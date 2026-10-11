from tests.fixtures import write_kml


def test_api_payload_matches_frontend_fields(client, tmp_path):
    kml = write_kml(tmp_path / "survey.kml", include_unsupported=False)
    uploaded = client.post(
        "/api/files/",
        files={"file": ("survey.kml", kml.read_bytes(), "application/vnd.google-earth.kml+xml")},
    ).json()

    for key in (
        "id",
        "original_filename",
        "format",
        "status",
        "feature_count",
        "measured_count",
        "source_crs",
        "measurement_crs_name",
        "created_at",
    ):
        assert key in uploaded

    listing = client.get("/api/files/").json()
    assert set(listing) >= {"total", "items"}

    stats = client.get("/api/files/stats").json()
    assert set(stats) >= {
        "files",
        "completed_files",
        "features",
        "polygons",
        "lines",
        "points",
        "total_area_m2",
        "total_length_m",
    }

    measures = client.get(f"/api/files/{uploaded['id']}/measurements/").json()
    assert set(measures) >= {"dataset_id", "total", "page", "page_size", "units", "crs_notes", "items"}
    item = measures["items"][0]
    assert set(item) >= {
        "id",
        "feature_index",
        "feature_id",
        "geometry_type",
        "properties",
        "source_crs",
        "measurement_crs",
        "area_m2",
        "length_m",
        "measurement_status",
        "measurement_note",
    }

    geojson = client.get(f"/api/files/{uploaded['id']}/geojson").json()
    assert geojson["type"] == "FeatureCollection"
    assert "legend" in geojson
    assert geojson["features"]
