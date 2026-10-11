from __future__ import annotations

import hashlib
import logging
import re
import uuid
from pathlib import Path

from app.config import get_settings
from app.exceptions import AppError

logger = logging.getLogger(__name__)

SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")
ALLOWED_EXTENSIONS = {".kml", ".zip"}


def ensure_storage() -> Path:
    path = get_settings().upload_path
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_filename(name: str) -> str:
    base = Path(name or "upload").name
    cleaned = SAFE_FILENAME.sub("_", base).strip("._") or "upload"
    return cleaned[:180]


def detect_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def validate_upload_meta(filename: str, size: int) -> str:
    ext = detect_extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise AppError(
            400,
            "Only .kml files and .zip archives containing shapefiles are accepted.",
            code="unsupported_format",
        )
    limit = get_settings().max_upload_bytes
    if size > limit:
        raise AppError(
            413,
            f"File exceeds the {limit // (1024 * 1024)} MB upload limit.",
            code="file_too_large",
        )
    if size <= 0:
        raise AppError(400, "Uploaded file is empty.", code="empty_file")
    return ext


def content_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def persist_upload(data: bytes, original_filename: str) -> tuple[str, Path]:
    ensure_storage()
    dataset_id = str(uuid.uuid4())
    ext = detect_extension(original_filename)
    stored_name = f"{dataset_id}_{sanitize_filename(original_filename)}"
    if not stored_name.lower().endswith(ext):
        stored_name += ext
    dest = get_settings().upload_path / stored_name
    dest.write_bytes(data)
    logger.info("Stored upload %s (%s bytes)", stored_name, len(data))
    return dataset_id, dest
