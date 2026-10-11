from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from shapely.geometry import GeometryCollection, LineString, MultiLineString, MultiPoint, MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry

from app.exceptions import AppError


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _text(el: ET.Element | None) -> str | None:
    if el is None or el.text is None:
        return None
    value = el.text.strip()
    return value or None


def _coords(text: str | None) -> list[tuple[float, float]]:
    if not text:
        return []
    points: list[tuple[float, float]] = []
    for token in text.replace("\n", " ").replace("\t", " ").split():
        parts = token.split(",")
        if len(parts) < 2:
            continue
        try:
            lon = float(parts[0])
            lat = float(parts[1])
        except ValueError:
            continue
        points.append((lon, lat))
    return points


def _child(el: ET.Element, name: str) -> ET.Element | None:
    for child in list(el):
        if _local(child.tag) == name:
            return child
    return None


def _children(el: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(el) if _local(child.tag) == name]


def _geometry_from_element(el: ET.Element) -> BaseGeometry | None:
    kind = _local(el.tag)
    if kind == "Point":
        coords = _coords(_text(_child(el, "coordinates")))
        return Point(coords[0]) if coords else None
    if kind == "LineString":
        coords = _coords(_text(_child(el, "coordinates")))
        return LineString(coords) if len(coords) >= 2 else None
    if kind == "LinearRing":
        coords = _coords(_text(_child(el, "coordinates")))
        return LineString(coords) if len(coords) >= 2 else None
    if kind == "Polygon":
        outer_el = _child(el, "outerBoundaryIs")
        ring_el = _child(outer_el, "LinearRing") if outer_el is not None else None
        exterior = _coords(_text(_child(ring_el, "coordinates"))) if ring_el is not None else []
        if len(exterior) < 4:
            return None
        holes: list[list[tuple[float, float]]] = []
        for inner in _children(el, "innerBoundaryIs"):
            inner_ring = _child(inner, "LinearRing")
            hole = _coords(_text(_child(inner_ring, "coordinates"))) if inner_ring is not None else []
            if len(hole) >= 4:
                holes.append(hole)
        return Polygon(exterior, holes)
    if kind == "MultiGeometry":
        parts = []
        for child in list(el):
            geom = _geometry_from_element(child)
            if geom is not None:
                parts.append(geom)
        if not parts:
            return None
        if all(isinstance(p, Polygon) for p in parts):
            return MultiPolygon(parts)
        if all(isinstance(p, LineString) for p in parts):
            return MultiLineString(parts)
        if all(isinstance(p, Point) for p in parts):
            return MultiPoint(parts)
        return GeometryCollection(parts)
    return None


def _extended_data(placemark: ET.Element) -> dict[str, Any]:
    props: dict[str, Any] = {}
    extended = _child(placemark, "ExtendedData")
    if extended is None:
        return props
    for data in _children(extended, "Data"):
        name = data.attrib.get("name")
        value = _text(_child(data, "value"))
        if name:
            props[name] = value
    schema = _child(extended, "SchemaData")
    if schema is not None:
        for sd in _children(schema, "SimpleData"):
            name = sd.attrib.get("name")
            if name:
                props[name] = (sd.text or "").strip()
    return props


def parse_kml(path: Path) -> list[dict[str, Any]]:
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError as exc:
        raise AppError(400, "KML file is not valid XML.", code="invalid_kml") from exc

    if _local(root.tag) not in {"kml", "Document", "Folder", "Placemark"}:
        raise AppError(400, "File is not a recognizable KML document.", code="invalid_kml")

    features: list[dict[str, Any]] = []
    for el in root.iter():
        if _local(el.tag) != "Placemark":
            continue
        geom = None
        for child in list(el):
            geom = _geometry_from_element(child)
            if geom is not None:
                break
        name = _text(_child(el, "name"))
        description = _text(_child(el, "description"))
        props = _extended_data(el)
        if name:
            props.setdefault("name", name)
        if description:
            props.setdefault("description", description)
        features.append(
            {
                "external_id": name or props.get("id") or props.get("ID"),
                "geometry": geom,
                "properties": json.loads(json.dumps(props, default=str)),
            }
        )
    return features
