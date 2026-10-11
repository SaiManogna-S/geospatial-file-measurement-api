from __future__ import annotations

from pathlib import Path

from tests.fixtures import (
    malformed_zip,
    traversal_zip,
    write_kml,
    write_shapefile_dir,
    zip_directory,
    zip_without_shapefile,
)

AREA_TOLERANCE = 0.02  # 2% — projection round-trip from UTM to WGS84 and back
LENGTH_TOLERANCE = 0.02


def _upload(client, path: Path, name: str | None = None):
    data = path.read_bytes()
    files = {"file": (name or path.name, data, "application/octet-stream")}
    return client.post("/api/files/", files=files)


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_kml_upload_and_measurements(client, tmp_path):
    kml = write_kml(tmp_path / "survey.kml")
    response = _upload(client, kml)
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["format"] == "kml"
    assert payload["status"] in {"completed", "completed_with_errors"}
    assert payload["feature_count"] >= 3
    assert payload["source_crs"] == "EPSG:4326"
    assert payload["measurement_crs_name"]

    detail = client.get(f"/api/files/{payload['id']}/")
    assert detail.status_code == 200
    assert detail.json()["id"] == payload["id"]

    measured = client.get(f"/api/files/{payload['id']}/measurements/", params={"page_size": 50})
    assert measured.status_code == 200
    body = measured.json()
    assert body["units"]["area"].startswith("square metres")
    items = {item["feature_id"]: item for item in body["items"]}

    plot = items["plot-a"]
    assert plot["geometry_type"] == "Polygon"
    assert plot["measurement_status"] == "measured"
    assert plot["area_m2"] is not None
    assert abs(plot["area_m2"] - 1_000_000) / 1_000_000 < AREA_TOLERANCE

    line = items["transect-1"]
    assert line["geometry_type"] == "LineString"
    assert abs(line["length_m"] - 5000) / 5000 < LENGTH_TOLERANCE

    point = items["control-point"]
    assert point["geometry_type"] == "Point"
    assert point["area_m2"] is None
    assert point["length_m"] is None
    assert point["measurement_status"] == "not_applicable"

    mixed = items["mixed-collection"]
    assert mixed["measurement_status"] == "unsupported"
    assert mixed["area_m2"] is None

    empty = items["empty-line"]
    assert empty["measurement_status"] == "skipped"


def test_shapefile_zip_upload(client, tmp_path):
    shp_dir = write_shapefile_dir(tmp_path / "shp")
    archive = zip_directory(shp_dir.parent, tmp_path / "survey.zip")
    response = _upload(client, archive)
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["format"] == "shapefile"
    assert payload["status"] == "completed"
    assert payload["feature_count"] == 3
    assert payload["source_crs"] and "32633" in payload["source_crs"]

    measured = client.get(f"/api/files/{payload['id']}/measurements/")
    items = {item["feature_id"]: item for item in measured.json()["items"]}
    assert abs(items["plot-a"]["area_m2"] - 1_000_000) < 1.0
    assert abs(items["transect-1"]["length_m"] - 5000) < 1.0


def test_missing_crs_does_not_invent_measurements(client, tmp_path):
    shp_dir = write_shapefile_dir(tmp_path / "shp", with_prj=False)
    archive = zip_directory(shp_dir.parent, tmp_path / "no_crs.zip")
    response = _upload(client, archive)
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["source_crs"] is None
    items = client.get(f"/api/files/{payload['id']}/measurements/").json()["items"]
    plot = next(item for item in items if item["feature_id"] == "plot-a")
    assert plot["area_m2"] is None
    assert plot["measurement_status"] == "crs_missing"


def test_invalid_kml(client, tmp_path):
    path = tmp_path / "bad.kml"
    path.write_text("this is not kml", encoding="utf-8")
    response = _upload(client, path)
    assert response.status_code == 400
    assert "KML" in response.json()["detail"] or "XML" in response.json()["detail"]


def test_malformed_zip(client, tmp_path):
    path = malformed_zip(tmp_path / "broken.zip")
    response = _upload(client, path)
    assert response.status_code == 400


def test_zip_without_shapefile(client, tmp_path):
    path = zip_without_shapefile(tmp_path / "emptyish.zip")
    response = _upload(client, path)
    assert response.status_code == 400


def test_path_traversal_zip(client, tmp_path):
    path = traversal_zip(tmp_path / "evil.zip")
    response = _upload(client, path)
    assert response.status_code == 400


def test_rejected_extension(client, tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("hello")
    response = _upload(client, path)
    assert response.status_code == 400


def test_duplicate_upload_returns_existing(client, tmp_path):
    kml = write_kml(tmp_path / "survey.kml", include_unsupported=False)
    first = _upload(client, kml)
    second = _upload(client, kml)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


def test_list_and_stats_and_geojson(client, tmp_path):
    kml = write_kml(tmp_path / "survey.kml", include_unsupported=False)
    uploaded = _upload(client, kml).json()
    listing = client.get("/api/files/").json()
    assert listing["total"] >= 1
    stats = client.get("/api/files/stats").json()
    assert stats["files"] >= 1
    assert stats["features"] >= 1
    geojson = client.get(f"/api/files/{uploaded['id']}/geojson").json()
    assert geojson["type"] == "FeatureCollection"
    assert geojson["features"]
    csv_resp = client.get(f"/api/files/{uploaded['id']}/measurements.csv")
    assert csv_resp.status_code == 200
    assert "area_m2" in csv_resp.text


def test_missing_file_404(client):
    response = client.get("/api/files/not-a-real-id/")
    assert response.status_code == 404
    measured = client.get("/api/files/not-a-real-id/measurements/")
    assert measured.status_code == 404


def test_measurement_search_and_filter(client, tmp_path):
    kml = write_kml(tmp_path / "survey.kml")
    dataset_id = _upload(client, kml).json()["id"]
    filtered = client.get(
        f"/api/files/{dataset_id}/measurements/",
        params={"geometry_type": "Polygon", "q": "plot"},
    )
    assert filtered.status_code == 200
    items = filtered.json()["items"]
    assert items
    assert all(item["geometry_type"] == "Polygon" for item in items)
