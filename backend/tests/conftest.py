from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "terrametric.db"
    uploads = tmp_path / "uploads"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")
    monkeypatch.setenv("UPLOAD_DIR", str(uploads))
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")

    from app.config import get_settings
    from app.db import configure_engine, init_db

    get_settings.cache_clear()
    configure_engine(get_settings().database_url)
    init_db()

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
