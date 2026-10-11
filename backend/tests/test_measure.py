from shapely.geometry import GeometryCollection, LineString, Point, box

from app.services.crs import WGS84
from app.services.measure import process_features
from tests.fixtures import UTM, line_5000m, square_1000m, to_wgs


def test_projected_source_preserves_metre_measurements():
    features = [
        {"external_id": "sq", "geometry": square_1000m(), "properties": {}},
        {"external_id": "ln", "geometry": line_5000m(), "properties": {}},
        {"external_id": "pt", "geometry": Point(500000, 5_300_000), "properties": {}},
    ]
    results, meta = process_features(features, UTM)
    by_id = {item.external_id: item for item in results}
    assert abs(by_id["sq"].area_m2 - 1_000_000) < 1e-3
    assert abs(by_id["ln"].length_m - 5000) < 1e-3
    assert by_id["pt"].measurement_status == "not_applicable"
    assert "32633" in (meta["source_crs"] or "")


def test_geographic_source_is_not_measured_in_degrees():
    features = [{"external_id": "sq", "geometry": to_wgs(square_1000m()), "properties": {}}]
    results, _meta = process_features(features, WGS84)
    area = results[0].area_m2
    assert area is not None
    assert area > 1000  # degree-square area would be ~1e-5 to 1e-2
    assert abs(area - 1_000_000) / 1_000_000 < 0.02


def test_unsupported_and_empty_geometries():
    features = [
        {
            "external_id": "gc",
            "geometry": GeometryCollection([Point(0, 0), LineString([(0, 0), (1, 1)])]),
            "properties": {},
        },
        {"external_id": "none", "geometry": None, "properties": {}},
    ]
    results, _meta = process_features(features, WGS84)
    assert results[0].measurement_status == "unsupported"
    assert results[1].measurement_status == "skipped"


def test_missing_crs_skips_polygon_area():
    features = [{"external_id": "sq", "geometry": box(0, 0, 1, 1), "properties": {}}]
    results, meta = process_features(features, None)
    assert results[0].area_m2 is None
    assert results[0].measurement_status == "crs_missing"
    assert "Missing CRS" in (meta["warning"] or "")
