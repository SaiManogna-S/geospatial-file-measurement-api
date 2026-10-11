from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import geopandas as gpd
from pyproj import CRS
from shapely import force_2d, make_valid
from shapely.geometry.base import BaseGeometry

from app.services.crs import (
    WGS84,
    MeasurementCRS,
    choose_measurement_crs,
    crs_label,
    is_geographic,
    reproject,
)

POLYGON_TYPES = {"Polygon", "MultiPolygon"}
LINE_TYPES = {"LineString", "MultiLineString", "LinearRing"}
POINT_TYPES = {"Point", "MultiPoint"}


@dataclass
class FeatureResult:
    feature_index: int
    external_id: str | None
    geometry_type: str
    geometry_wgs84: BaseGeometry | None
    properties: dict[str, Any]
    source_crs: str | None
    measurement_crs: str | None
    area_m2: float | None
    length_m: float | None
    measurement_status: str
    measurement_note: str | None


def _prepare_geom(geom: BaseGeometry | None) -> tuple[BaseGeometry | None, str | None]:
    if geom is None:
        return None, "Feature has no geometry."
    geom = force_2d(geom)
    if geom.is_empty:
        return None, "Geometry is empty."
    if not geom.is_valid:
        geom = force_2d(make_valid(geom))
        if geom.is_empty:
            return None, "Geometry is invalid and could not be repaired."
        if not geom.is_valid:
            return None, "Geometry is invalid."
    return geom, None


def _measure(geom: BaseGeometry) -> tuple[float | None, float | None, str, str]:
    gtype = geom.geom_type
    if gtype in POLYGON_TYPES:
        return (
            float(geom.area),
            None,
            "measured",
            "Polygon area computed in the projected measurement CRS (square metres).",
        )
    if gtype in LINE_TYPES:
        return (
            None,
            float(geom.length),
            "measured",
            "Line length computed in the projected measurement CRS (metres).",
        )
    if gtype in POINT_TYPES:
        return None, None, "not_applicable", "Point features do not receive area or length measurements."
    return (
        None,
        None,
        "unsupported",
        f"{gtype} is not measured. Only Polygon and LineString geometries are measured.",
    )


def process_features(
    raw_features: list[dict[str, Any]],
    source_crs: CRS | None,
    assumed_crs_note: str | None = None,
) -> tuple[list[FeatureResult], dict[str, Any]]:
    source_label = crs_label(source_crs) if source_crs else None
    prepared: list[tuple[int, dict[str, Any], BaseGeometry | None, str | None]] = []
    wgs_geoms: list[BaseGeometry] = []

    for index, feature in enumerate(raw_features):
        geom, note = _prepare_geom(feature.get("geometry"))
        prepared.append((index, feature, geom, note))

    meta: dict[str, Any] = {
        "source_crs": source_label,
        "measurement_crs": None,
        "measurement_crs_name": None,
        "projection_strategy": None,
        "warning": assumed_crs_note,
        "bbox": None,
    }

    if source_crs is None:
        results = []
        measurable = POLYGON_TYPES | LINE_TYPES
        for index, feature, geom, note in prepared:
            gtype = geom.geom_type if geom is not None else "Unknown"
            if geom is None:
                status, message = "skipped", note or "Feature could not be measured."
            elif gtype in measurable:
                status, message = (
                    "crs_missing",
                    "Source CRS is missing, so ground measurements were not calculated.",
                )
            elif gtype in POINT_TYPES:
                status, message = "not_applicable", "Point features do not receive area or length measurements."
            else:
                status, message = "unsupported", f"{gtype} is not measured."
            results.append(
                FeatureResult(
                    feature_index=index,
                    external_id=feature.get("external_id"),
                    geometry_type=gtype,
                    geometry_wgs84=None,
                    properties=feature.get("properties") or {},
                    source_crs=None,
                    measurement_crs=None,
                    area_m2=None,
                    length_m=None,
                    measurement_status=status,
                    measurement_note=message,
                )
            )
        meta["projection_strategy"] = (
            "No source CRS was provided. Features were stored without ground measurements "
            "to avoid returning values in geographic degrees."
        )
        meta["warning"] = "Missing CRS: area and length were not calculated."
        return results, meta

    valid_geoms = [geom for _i, _f, geom, _n in prepared if geom is not None]
    if valid_geoms:
        try:
            gdf = gpd.GeoDataFrame({"geometry": valid_geoms}, geometry="geometry", crs=source_crs)
            wgs_gdf = gdf.to_crs(WGS84) if not source_crs.equals(WGS84) else gdf
            wgs_geoms = [geom for geom in wgs_gdf.geometry if geom is not None and not geom.is_empty]
        except Exception:
            for geom in valid_geoms:
                try:
                    wgs = reproject(geom, source_crs, WGS84) if not source_crs.equals(WGS84) else geom
                    if not wgs.is_empty:
                        wgs_geoms.append(wgs)
                except Exception:
                    continue

    measurement: MeasurementCRS | None = None
    if wgs_geoms:
        if is_geographic(source_crs):
            measurement = choose_measurement_crs(wgs_geoms)
        else:
            axis_unit = None
            try:
                axis_unit = (source_crs.axis_info[0].unit_name or "").lower() if source_crs.axis_info else None
            except Exception:
                axis_unit = None
            if axis_unit in {"metre", "meter", "metres", "meters", "m"}:
                measurement = MeasurementCRS(
                    source_crs,
                    "Source CRS is projected with metre units; measurements use the source CRS.",
                    source_label or "source projected CRS",
                )
            else:
                measurement = choose_measurement_crs(wgs_geoms)

    if measurement:
        meta["measurement_crs"] = measurement.crs.to_wkt()
        meta["measurement_crs_name"] = measurement.name
        meta["projection_strategy"] = measurement.strategy

    results = []
    xs: list[float] = []
    ys: list[float] = []
    for index, feature, geom, note in prepared:
        gtype = geom.geom_type if geom is not None else "Unknown"
        if geom is None:
            results.append(
                FeatureResult(
                    feature_index=index,
                    external_id=feature.get("external_id"),
                    geometry_type=gtype,
                    geometry_wgs84=None,
                    properties=feature.get("properties") or {},
                    source_crs=source_label,
                    measurement_crs=measurement.name if measurement else None,
                    area_m2=None,
                    length_m=None,
                    measurement_status="skipped",
                    measurement_note=note or "Feature has no usable geometry.",
                )
            )
            continue

        wgs = None
        area = length = None
        status = "skipped"
        message = note
        try:
            wgs = reproject(geom, source_crs, WGS84) if not source_crs.equals(WGS84) else geom
            if not wgs.is_empty:
                minx, miny, maxx, maxy = wgs.bounds
                xs.extend([minx, maxx])
                ys.extend([miny, maxy])
        except Exception:
            wgs = None
            status = "error"
            message = "Geometry could not be transformed for map display."

        if measurement is None:
            status = "error"
            message = "No suitable projected CRS could be selected."
        else:
            try:
                projected = reproject(geom, source_crs, measurement.crs)
                projected, repair_note = _prepare_geom(projected)
                if projected is None:
                    status = "error"
                    message = repair_note or "Projected geometry is unusable."
                else:
                    area, length, status, message = _measure(projected)
            except Exception:
                status = "error"
                message = "Geometry could not be transformed into the measurement CRS."

        results.append(
            FeatureResult(
                feature_index=index,
                external_id=feature.get("external_id"),
                geometry_type=gtype,
                geometry_wgs84=wgs,
                properties=feature.get("properties") or {},
                source_crs=source_label,
                measurement_crs=measurement.name if measurement else None,
                area_m2=area,
                length_m=length,
                measurement_status=status,
                measurement_note=message,
            )
        )

    if xs and ys:
        meta["bbox"] = (min(xs), min(ys), max(xs), max(ys))
    if assumed_crs_note:
        meta["warning"] = assumed_crs_note
    return results, meta
