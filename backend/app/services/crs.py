from __future__ import annotations

from dataclasses import dataclass

from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform

WGS84 = CRS.from_epsg(4326)


@dataclass(frozen=True)
class MeasurementCRS:
    crs: CRS
    strategy: str
    name: str


def crs_label(crs: CRS | None) -> str | None:
    if crs is None:
        return None
    try:
        epsg = crs.to_epsg()
        if epsg:
            return f"EPSG:{epsg}"
    except Exception:
        pass
    try:
        name = crs.name
        if name:
            return str(name)
    except Exception:
        pass
    return crs.to_wkt()[:240]


def is_geographic(crs: CRS) -> bool:
    try:
        return bool(crs.is_geographic)
    except Exception:
        return True


def transformer(source: CRS, dest: CRS) -> Transformer:
    return Transformer.from_crs(source, dest, always_xy=True)


def reproject(geom: BaseGeometry, source: CRS, dest: CRS) -> BaseGeometry:
    if source == dest or source.equals(dest):
        return geom
    project = transformer(source, dest).transform
    return shapely_transform(project, geom)


def _centroid_lonlat(geoms: list[BaseGeometry]) -> tuple[float, float]:
    lons: list[float] = []
    lats: list[float] = []
    for geom in geoms:
        if geom is None or geom.is_empty:
            continue
        c = geom.centroid
        lons.append(c.x)
        lats.append(c.y)
    if not lons:
        raise ValueError("No geometries available for CRS selection")
    return sum(lons) / len(lons), sum(lats) / len(lats)


def _bounds(geoms: list[BaseGeometry]) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []
    for geom in geoms:
        if geom is None or geom.is_empty:
            continue
        minx, miny, maxx, maxy = geom.bounds
        xs.extend([minx, maxx])
        ys.extend([miny, maxy])
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def utm_crs(lon: float, lat: float) -> CRS:
    zone = int((lon + 180) / 6) + 1
    zone = min(max(zone, 1), 60)
    epsg = (32600 if lat >= 0 else 32700) + zone
    return CRS.from_epsg(epsg)


def choose_measurement_crs(geoms_wgs84: list[BaseGeometry]) -> MeasurementCRS:
    """Select a projected CRS from geographic extent.

    Strategy:
    1. Geometries are first represented in WGS84 lon/lat.
    2. If the dataset is local (≤ 6° longitude and ≤ 8° latitude, roughly
       one UTM zone), use the UTM zone of the centroid. UTM is conformal and
       suitable for both area and length at local survey scale.
    3. If the dataset is regional or spans multiple UTM zones, use a custom
       Lambert Azimuthal Equal Area projection centered on the centroid.
       LAEA preserves area; length distortion grows with distance from the
       center and is reported in the dataset notes.
    Measurements are never computed in geographic degrees.
    """
    bounds = _bounds(geoms_wgs84)
    lon, lat = _centroid_lonlat(geoms_wgs84)
    if bounds is None:
        crs = utm_crs(lon, lat)
        return MeasurementCRS(crs, "utm_centroid_fallback", crs_label(crs) or "UTM")

    minx, miny, maxx, maxy = bounds
    lon_span = maxx - minx
    lat_span = maxy - miny

    if lon_span <= 6.0 and lat_span <= 8.0:
        crs = utm_crs(lon, lat)
        return MeasurementCRS(
            crs,
            (
                "Local UTM zone of the WGS84 centroid. Suitable for compact datasets "
                f"(lon span {lon_span:.3f}°, lat span {lat_span:.3f}°)."
            ),
            crs_label(crs) or "UTM",
        )

    proj4 = (
        f"+proj=laea +lat_0={lat:.8f} +lon_0={lon:.8f} +x_0=0 +y_0=0 "
        "+datum=WGS84 +units=m +no_defs"
    )
    crs = CRS.from_proj4(proj4)
    return MeasurementCRS(
        crs,
        (
            "Lambert Azimuthal Equal Area centered on the dataset centroid. "
            "Chosen because the geographic extent exceeds a single UTM zone. "
            "Area is preserved; length accuracy decreases away from the center."
        ),
        f"LAEA lat_0={lat:.4f} lon_0={lon:.4f}",
    )
