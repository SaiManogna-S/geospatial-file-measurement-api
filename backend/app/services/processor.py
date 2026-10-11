from __future__ import annotations

import json
import logging
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from shapely.geometry.base import BaseGeometry
from sqlalchemy.orm import Session

from app.models import Dataset, Feature
from app.services.crs import WGS84
from app.services.kml import parse_kml
from app.services.measure import FeatureResult, process_features
from app.services.shapefile_reader import read_shapefile
from app.services.zip_safe import extract_shapefile_zip

logger = logging.getLogger(__name__)


def _process_shapefiles(shapefiles: list[Path]) -> tuple[list[FeatureResult], dict]:
    combined: list[FeatureResult] = []
    source_labels: list[str] = []
    warnings: list[str] = []
    strategies: list[str] = []
    measure_names: list[str] = []
    measure_wkts: list[str] = []
    xs: list[float] = []
    ys: list[float] = []

    for shp in shapefiles:
        raw, source_crs = read_shapefile(shp)
        results, meta = process_features(raw, source_crs)
        offset = len(combined)
        for item in results:
            item.feature_index += offset
            combined.append(item)
        if meta.get("source_crs"):
            source_labels.append(meta["source_crs"])
        if meta.get("warning"):
            warnings.append(str(meta["warning"]))
        if meta.get("projection_strategy"):
            strategies.append(str(meta["projection_strategy"]))
        if meta.get("measurement_crs_name"):
            measure_names.append(str(meta["measurement_crs_name"]))
        if meta.get("measurement_crs"):
            measure_wkts.append(str(meta["measurement_crs"]))
        bbox = meta.get("bbox")
        if bbox:
            xs.extend([bbox[0], bbox[2]])
            ys.extend([bbox[1], bbox[3]])

    unique_source = sorted(set(source_labels))
    unique_names = sorted(set(measure_names))
    merged = {
        "source_crs": unique_source[0] if len(unique_source) == 1 else (", ".join(unique_source) if unique_source else None),
        "measurement_crs": measure_wkts[0] if len(set(measure_wkts)) == 1 else (measure_wkts[0] if measure_wkts else None),
        "measurement_crs_name": unique_names[0] if len(unique_names) == 1 else ("Multiple projected CRS" if unique_names else None),
        "projection_strategy": strategies[0] if strategies else None,
        "warning": " ".join(dict.fromkeys(warnings)) or None,
        "bbox": (min(xs), min(ys), max(xs), max(ys)) if xs and ys else None,
    }
    return combined, merged


def _geojson(geom: BaseGeometry | None) -> str | None:
    if geom is None or geom.is_empty:
        return None
    return json.dumps(geom.__geo_interface__)


def process_dataset(db: Session, dataset: Dataset, path: Path) -> Dataset:
    dataset.status = "processing"
    db.commit()
    try:
        if dataset.format == "kml":
            raw = parse_kml(path)
            results, meta = process_features(
                raw,
                WGS84,
                assumed_crs_note="KML coordinates are lon/lat WGS84 (EPSG:4326) by specification.",
            )
        elif dataset.format == "shapefile":
            tmp = Path(tempfile.mkdtemp(prefix="tm_shp_"))
            try:
                shapefiles = extract_shapefile_zip(path, tmp)
                results, meta = _process_shapefiles(shapefiles)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        else:
            raise ValueError("Unsupported dataset format")

        _persist_results(db, dataset, results, meta)
        logger.info("Processed dataset %s with %s features", dataset.id, dataset.feature_count)
        return dataset
    except Exception as exc:
        from app.exceptions import AppError

        dataset.processed_at = datetime.utcnow()
        dataset.status = "failed"
        if isinstance(exc, AppError):
            dataset.error_summary = exc.detail
        else:
            dataset.error_summary = "The file could not be processed."
            logger.exception("Processing failed for %s", dataset.id)
        db.commit()
        db.refresh(dataset)
        if isinstance(exc, AppError):
            raise
        raise


def _persist_results(
    db: Session, dataset: Dataset, results: list[FeatureResult], meta: dict
) -> None:
    db.query(Feature).filter(Feature.dataset_id == dataset.id).delete()
    error_count = 0
    measured = 0
    for item in results:
        if item.measurement_status in {"error", "skipped", "crs_missing"}:
            error_count += 1
        if item.measurement_status == "measured":
            measured += 1
        db.add(
            Feature(
                dataset_id=dataset.id,
                feature_index=item.feature_index,
                external_id=item.external_id,
                geometry_type=item.geometry_type,
                geometry_geojson=_geojson(item.geometry_wgs84),
                properties_json=json.dumps(item.properties, default=str),
                source_crs=item.source_crs,
                measurement_crs=item.measurement_crs,
                area_m2=item.area_m2,
                length_m=item.length_m,
                measurement_status=item.measurement_status,
                measurement_note=item.measurement_note,
            )
        )

    bbox = meta.get("bbox")
    dataset.source_crs = meta.get("source_crs")
    dataset.measurement_crs = meta.get("measurement_crs")
    dataset.measurement_crs_name = meta.get("measurement_crs_name")
    dataset.projection_strategy = meta.get("projection_strategy")
    dataset.warning = meta.get("warning")
    dataset.feature_count = len(results)
    dataset.measured_count = measured
    dataset.error_count = error_count
    dataset.processed_at = datetime.utcnow()
    if bbox:
        dataset.bbox_west, dataset.bbox_south, dataset.bbox_east, dataset.bbox_north = bbox
    if dataset.feature_count == 0:
        dataset.status = "completed"
        dataset.warning = (dataset.warning + " " if dataset.warning else "") + "No features were found in the file."
    elif error_count and measured:
        dataset.status = "completed_with_errors"
    elif error_count and not measured:
        dataset.status = "completed_with_errors"
    else:
        dataset.status = "completed"
    db.commit()
    db.refresh(dataset)
