from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import shapefile
from pyproj import CRS
from shapely.geometry import shape as shapely_shape
from shapely.geometry.base import BaseGeometry

from app.exceptions import AppError


def read_prj(shp_path: Path) -> CRS | None:
    prj = shp_path.with_suffix(".prj")
    if not prj.exists():
        return None
    text = prj.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return None
    try:
        return CRS.from_user_input(text)
    except Exception:
        try:
            return CRS.from_wkt(text)
        except Exception as exc:
            raise AppError(
                400,
                "Shapefile .prj file could not be interpreted as a valid CRS.",
                code="invalid_crs",
            ) from exc


def read_shapefile(shp_path: Path) -> tuple[list[dict[str, Any]], CRS | None]:
    shx = shp_path.with_suffix(".shx")
    dbf = shp_path.with_suffix(".dbf")
    if not shx.exists() or not dbf.exists():
        raise AppError(
            400,
            "Shapefile is incomplete. A .shp file requires matching .shx and .dbf companions.",
            code="incomplete_shapefile",
        )
    try:
        reader = shapefile.Reader(str(shp_path))
    except Exception as exc:
        raise AppError(400, "Shapefile could not be read.", code="invalid_shapefile") from exc

    crs = read_prj(shp_path)
    fields = [field[0] for field in reader.fields[1:]]
    features: list[dict[str, Any]] = []
    try:
        for index, sr in enumerate(reader.shapeRecords()):
            geom: BaseGeometry | None = None
            try:
                if sr.shape.shapeType != shapefile.NULL:
                    geom = shapely_shape(sr.shape.__geo_interface__)
            except Exception:
                geom = None
            props = {}
            for name, value in zip(fields, sr.record, strict=False):
                if hasattr(value, "isoformat"):
                    props[name] = value.isoformat()
                else:
                    props[name] = value
            external = None
            for key in ("id", "ID", "fid", "FID", "name", "NAME", "Name"):
                if key in props and props[key] not in (None, ""):
                    external = str(props[key])
                    break
            features.append(
                {
                    "external_id": external,
                    "geometry": geom,
                    "properties": json.loads(json.dumps(props, default=str)),
                }
            )
    finally:
        reader.close()
    return features, crs
