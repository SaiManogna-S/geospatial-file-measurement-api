from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TerraMetric"
    app_env: str = "development"
    database_url: str = f"sqlite:///{(BACKEND_ROOT / 'data' / 'terrametric.db').as_posix()}"
    upload_dir: str = str(BACKEND_ROOT / "data" / "uploads")
    max_upload_bytes: int = 25 * 1024 * 1024
    max_zip_files: int = 200
    max_zip_uncompressed_bytes: int = 120 * 1024 * 1024
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
