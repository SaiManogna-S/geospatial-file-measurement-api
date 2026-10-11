from __future__ import annotations

import io
import zipfile
from pathlib import Path

import shapefile
from pyproj import CRS, Transformer
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import transform as shapely_transform

UTM = CRS.from_epsg(32633)
WGS84 = CRS.from_epsg(4326)
TO_WGS = Transformer.from_crs(UTM, WGS84, always_xy=True)


def square_1000m() -> Polygon:
    return box(500000, 5_300_000, 501000, 5_301_000)


def line_5000m() -> LineString:
    return LineString([(500000, 5_300_000), (505000, 5_300_000)])


def survey_point() -> Point:
    return Point(500500, 5_300_500)


def to_wgs(geom):
    return shapely_transform(TO_WGS.transform, geom)


def _kml_coords(geom) -> str:
    if geom.geom_type == "Point":
        return f"{geom.x},{geom.y},0"
    coords = list(geom.coords) if geom.geom_type == "LineString" else list(geom.exterior.coords)
    return " ".join(f"{x},{y},0" for x, y in coords)


def write_kml(path: Path, include_unsupported: bool = True) -> Path:
    poly = to_wgs(square_1000m())
    line = to_wgs(line_5000m())
    point = to_wgs(survey_point())
    unsupported = """
    <Placemark>
      <name>mixed-collection</name>
      <MultiGeometry>
        <Point><coordinates>12.0,48.0,0</coordinates></Point>
        <LineString><coordinates>12.0,48.0,0 12.1,48.1,0</coordinates></LineString>
      </MultiGeometry>
    </Placemark>
    """ if include_unsupported else ""
    invalid = """
    <Placemark>
      <name>empty-line</name>
      <LineString><coordinates></coordinates></LineString>
    </Placemark>
    """
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>plot-a</name>
      <ExtendedData><Data name="site"><value>north-field</value></Data></ExtendedData>
      <Polygon>
        <outerBoundaryIs><LinearRing><coordinates>{_kml_coords(poly)}</coordinates></LinearRing></outerBoundaryIs>
      </Polygon>
    </Placemark>
    <Placemark>
      <name>transect-1</name>
      <LineString><coordinates>{_kml_coords(line)}</coordinates></LineString>
    </Placemark>
    <Placemark>
      <name>control-point</name>
      <Point><coordinates>{_kml_coords(point)}</coordinates></Point>
    </Placemark>
    {unsupported}
    {invalid}
  </Document>
</kml>
"""
    path.write_text(xml, encoding="utf-8")
    return path


def _write_prj(path: Path, enabled: bool) -> None:
    if enabled:
        path.write_text(UTM.to_wkt(), encoding="utf-8")


def write_shapefile_dir(directory: Path, with_prj: bool = True) -> Path:
    directory.mkdir(parents=True, exist_ok=True)

    poly_writer = shapefile.Writer(str(directory / "plots"), shapeType=shapefile.POLYGON)
    poly_writer.field("name", "C", size=40)
    poly_writer.field("code", "C", size=12)
    poly = square_1000m()
    poly_writer.poly([[list(coord) for coord in poly.exterior.coords]])
    poly_writer.record("plot-a", "P1")
    poly_writer.close()
    _write_prj(directory / "plots.prj", with_prj)

    line_writer = shapefile.Writer(str(directory / "lines"), shapeType=shapefile.POLYLINE)
    line_writer.field("name", "C", size=40)
    line_writer.field("code", "C", size=12)
    line = line_5000m()
    line_writer.line([[list(coord) for coord in line.coords]])
    line_writer.record("transect-1", "L1")
    line_writer.close()
    _write_prj(directory / "lines.prj", with_prj)

    point_writer = shapefile.Writer(str(directory / "points"), shapeType=shapefile.POINT)
    point_writer.field("name", "C", size=40)
    point_writer.field("code", "C", size=12)
    point = survey_point()
    point_writer.point(point.x, point.y)
    point_writer.record("control-point", "C1")
    point_writer.close()
    _write_prj(directory / "points.prj", with_prj)

    return directory / "plots.shp"


def zip_directory(directory: Path, dest: Path) -> Path:
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in directory.rglob("*"):
            if file.is_file():
                archive.write(file, file.relative_to(directory))
    return dest


def malformed_zip(path: Path) -> Path:
    path.write_bytes(b"this is not a zip file")
    return path


def zip_without_shapefile(path: Path) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("readme.txt", "no shapefile here")
    return path


def traversal_zip(path: Path) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        info = zipfile.ZipInfo("../evil.shp")
        archive.writestr(info, b"not-a-shape")
    return path
