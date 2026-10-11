from __future__ import annotations

import csv
import io
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.exceptions import AppError
from app.models import Dataset, Feature
from app.schemas import (
    DatasetDetail,
    DatasetList,
    DatasetSummary,
    FeatureMeasurement,
    GeoJSONResponse,
    MeasurementPage,
    StatsResponse,
)
from app.services.processor import process_dataset
from app.services.storage import content_sha256, persist_upload, validate_upload_meta

logger = logging.getLogger(__name__)
router = APIRouter()

CRS_NOTES = (
    "Polygon area is reported in square metres and LineString length in metres. "
    "Values are computed after transforming geometries into a projected CRS selected "
    "from the dataset extent (UTM for local files, Lambert Azimuthal Equal Area for "
    "broader coverage). Measurements are never taken from longitude/latitude degrees."
)


def _format_from_ext(ext: str) -> str:
    return "kml" if ext == ".kml" else "shapefile"


def _to_measurement(row: Feature, include_geometry: bool = False) -> FeatureMeasurement:
    geometry = json.loads(row.geometry_geojson) if include_geometry and row.geometry_geojson else None
    return FeatureMeasurement(
        id=row.id,
        feature_index=row.feature_index,
        feature_id=row.external_id,
        geometry_type=row.geometry_type,
        properties=json.loads(row.properties_json or "{}"),
        source_crs=row.source_crs,
        measurement_crs=row.measurement_crs,
        area_m2=row.area_m2,
        length_m=row.length_m,
        measurement_status=row.measurement_status,
        measurement_note=row.measurement_note,
        geometry=geometry,
    )


@router.post("/files/", status_code=201, response_model=DatasetDetail)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    filename = file.filename or "upload"
    data = await file.read()
    ext = validate_upload_meta(filename, len(data))
    digest = content_sha256(data)

    existing = db.scalar(
        select(Dataset)
        .where(Dataset.content_hash == digest, Dataset.status != "failed")
        .order_by(Dataset.created_at.desc())
    )
    if existing and existing.status in {"completed", "completed_with_errors"}:

        existing.duplicate_of = existing.duplicate_of or existing.id
        logger.info("Duplicate upload of dataset %s", existing.id)
        return existing

    dataset_id, stored_path = persist_upload(data, filename)
    dataset = Dataset(
        id=dataset_id,
        original_filename=filename,
        stored_filename=stored_path.name,
        content_hash=digest,
        format=_format_from_ext(ext),
        size_bytes=len(data),
        status="queued",
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    try:
        process_dataset(db, dataset, stored_path)
    except AppError:
        db.refresh(dataset)
        if dataset.status == "failed":
            raise
        raise
    db.refresh(dataset)
    return dataset


@router.get("/files/", response_model=DatasetList)
def list_files(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
):
    total = db.scalar(select(func.count()).select_from(Dataset)) or 0
    rows = db.scalars(select(Dataset).order_by(Dataset.created_at.desc()).limit(limit)).all()
    return DatasetList(total=total, items=[DatasetSummary.model_validate(row) for row in rows])


@router.get("/files/stats", response_model=StatsResponse)
def stats(db: Session = Depends(get_db)):
    files = db.scalar(select(func.count()).select_from(Dataset)) or 0
    completed = db.scalar(
        select(func.count()).select_from(Dataset).where(Dataset.status.in_(("completed", "completed_with_errors")))
    ) or 0
    features = db.scalar(select(func.count()).select_from(Feature)) or 0
    polygons = db.scalar(
        select(func.count()).select_from(Feature).where(Feature.geometry_type.in_(("Polygon", "MultiPolygon")))
    ) or 0
    lines = db.scalar(
        select(func.count()).select_from(Feature).where(
            Feature.geometry_type.in_(("LineString", "MultiLineString", "LinearRing"))
        )
    ) or 0
    points = db.scalar(
        select(func.count()).select_from(Feature).where(Feature.geometry_type.in_(("Point", "MultiPoint")))
    ) or 0
    total_area = db.scalar(select(func.coalesce(func.sum(Feature.area_m2), 0.0))) or 0.0
    total_length = db.scalar(select(func.coalesce(func.sum(Feature.length_m), 0.0))) or 0.0
    return StatsResponse(
        files=files,
        completed_files=completed,
        features=features,
        polygons=polygons,
        lines=lines,
        points=points,
        total_area_m2=float(total_area),
        total_length_m=float(total_length),
    )


@router.get("/files/{dataset_id}/", response_model=DatasetDetail)
def get_file(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise AppError(404, "File not found.", code="not_found")
    return dataset


@router.get("/files/{dataset_id}/measurements/", response_model=MeasurementPage)
def get_measurements(
    dataset_id: str,
    db: Session = Depends(get_db),
    q: str | None = None,
    geometry_type: str | None = None,
    status: str | None = None,
    sort: str = Query("feature_index", pattern="^(feature_index|geometry_type|area_m2|length_m|measurement_status)$"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    include_geometry: bool = False,
):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise AppError(404, "File not found.", code="not_found")

    stmt = select(Feature).where(Feature.dataset_id == dataset_id)
    if geometry_type:
        stmt = stmt.where(Feature.geometry_type == geometry_type)
    if status:
        stmt = stmt.where(Feature.measurement_status == status)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (Feature.external_id.ilike(like))
            | (Feature.geometry_type.ilike(like))
            | (Feature.properties_json.ilike(like))
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = getattr(Feature, sort)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = db.scalars(stmt).all()
    return MeasurementPage(
        dataset_id=dataset_id,
        total=total,
        page=page,
        page_size=page_size,
        units={"area": "square metres (m²)", "length": "metres (m)"},
        crs_notes=CRS_NOTES,
        items=[_to_measurement(row, include_geometry=include_geometry) for row in rows],
    )


@router.get("/files/{dataset_id}/geojson")
def get_geojson(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise AppError(404, "File not found.", code="not_found")
    rows = db.scalars(
        select(Feature).where(Feature.dataset_id == dataset_id).order_by(Feature.feature_index)
    ).all()
    features: list[dict[str, Any]] = []
    for row in rows:
        if not row.geometry_geojson:
            continue
        features.append(
            {
                "type": "Feature",
                "id": row.id,
                "geometry": json.loads(row.geometry_geojson),
                "properties": {
                    "feature_index": row.feature_index,
                    "feature_id": row.external_id,
                    "geometry_type": row.geometry_type,
                    "area_m2": row.area_m2,
                    "length_m": row.length_m,
                    "measurement_status": row.measurement_status,
                    **json.loads(row.properties_json or "{}"),
                },
            }
        )
    bbox = None
    if dataset.bbox_west is not None:
        bbox = [dataset.bbox_west, dataset.bbox_south, dataset.bbox_east, dataset.bbox_north]
    return GeoJSONResponse(
        features=features,
        bbox=bbox,
        legend=[
            {"type": "Polygon", "label": "Polygon", "color": "#C8F542"},
            {"type": "LineString", "label": "Line", "color": "#2DD4BF"},
            {"type": "Point", "label": "Point", "color": "#F8FAFC"},
        ],
    )


@router.get("/files/{dataset_id}/measurements.csv")
def export_csv(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise AppError(404, "File not found.", code="not_found")
    rows = db.scalars(
        select(Feature).where(Feature.dataset_id == dataset_id).order_by(Feature.feature_index)
    ).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "feature_index",
            "feature_id",
            "geometry_type",
            "source_crs",
            "measurement_crs",
            "area_m2",
            "length_m",
            "measurement_status",
            "measurement_note",
            "properties_json",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.feature_index,
                row.external_id or "",
                row.geometry_type,
                row.source_crs or "",
                row.measurement_crs or "",
                "" if row.area_m2 is None else f"{row.area_m2:.6f}",
                "" if row.length_m is None else f"{row.length_m:.6f}",
                row.measurement_status,
                row.measurement_note or "",
                row.properties_json,
            ]
        )
    buffer.seek(0)
    filename = f"{dataset.original_filename}-measurements.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/health")
def health():
    return {"status": "ok", "service": get_settings().app_name}
