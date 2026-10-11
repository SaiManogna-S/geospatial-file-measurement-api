from __future__ import annotations

import logging
import zipfile
from pathlib import Path

from app.config import get_settings
from app.exceptions import AppError

logger = logging.getLogger(__name__)


def _is_unsafe_name(name: str) -> bool:
    path = Path(name)
    if path.is_absolute() or name.startswith("/") or name.startswith("\\"):
        return True
    if ":" in path.parts[0] if path.parts else False:
        return True
    return any(part in ("..", "") for part in Path(name.replace("\\", "/")).parts if part == "..")


def extract_shapefile_zip(zip_path: Path, dest_dir: Path) -> list[Path]:
    settings = get_settings()
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path) as archive:
            infos = archive.infolist()
            if not infos:
                raise AppError(400, "ZIP archive is empty.", code="empty_zip")
            if len(infos) > settings.max_zip_files:
                raise AppError(400, "ZIP archive contains too many files.", code="zip_too_many_files")

            total_uncompressed = 0
            members: list[zipfile.ZipInfo] = []
            for info in infos:
                if info.is_dir():
                    continue
                name = info.filename
                if _is_unsafe_name(name):
                    raise AppError(400, "ZIP archive contains an unsafe path.", code="zip_path_traversal")
                if info.file_size < 0:
                    raise AppError(400, "ZIP archive is malformed.", code="malformed_zip")
                total_uncompressed += info.file_size
                if total_uncompressed > settings.max_zip_uncompressed_bytes:
                    raise AppError(400, "ZIP archive exceeds the decompression size limit.", code="zip_bomb")
                members.append(info)

            if not members:
                raise AppError(400, "ZIP archive does not contain any files.", code="empty_zip")

            for info in members:
                target = (dest_dir / info.filename).resolve()
                try:
                    target.relative_to(dest_dir.resolve())
                except ValueError:
                    raise AppError(400, "ZIP archive contains an unsafe path.", code="zip_path_traversal")
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src, target.open("wb") as out:
                    out.write(src.read())
    except AppError:
        raise
    except zipfile.BadZipFile as exc:
        raise AppError(400, "File is not a valid ZIP archive.", code="malformed_zip") from exc
    except Exception as exc:
        logger.warning("ZIP extraction failed: %s", type(exc).__name__)
        raise AppError(400, "Unable to extract the ZIP archive.", code="malformed_zip") from exc

    shapefiles = [
        path
        for path in dest_dir.rglob("*.shp")
        if path.is_file() and "__macosx" not in str(path).lower()
    ]
    if not shapefiles:
        raise AppError(
            400,
            "ZIP archive must contain a shapefile (.shp) with companion .shx and .dbf files.",
            code="missing_shapefile",
        )
    return shapefiles
