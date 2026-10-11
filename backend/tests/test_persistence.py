from tests.fixtures import write_kml


def test_failed_upload_is_persisted(client, tmp_path):
    path = tmp_path / "broken.kml"
    path.write_text("not xml", encoding="utf-8")
    response = client.post("/api/files/", files={"file": ("broken.kml", path.read_bytes(), "text/xml")})
    assert response.status_code == 400
    listing = client.get("/api/files/").json()
    assert listing["total"] >= 1
    failed = listing["items"][0]
    assert failed["status"] == "failed"
    detail = client.get(f"/api/files/{failed['id']}/")
    assert detail.status_code == 200
    assert detail.json()["error_summary"]


def test_successful_upload_survives_refetch(client, tmp_path):
    kml = write_kml(tmp_path / "survey.kml", include_unsupported=False)
    created = client.post(
        "/api/files/",
        files={"file": ("survey.kml", kml.read_bytes(), "application/vnd.google-earth.kml+xml")},
    ).json()
    again = client.get(f"/api/files/{created['id']}/").json()
    assert again["id"] == created["id"]
    assert again["feature_count"] == created["feature_count"]
    measures = client.get(f"/api/files/{created['id']}/measurements/").json()
    assert measures["total"] == again["feature_count"]
