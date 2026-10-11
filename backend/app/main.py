from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings
from app.db import init_db
from app.exceptions import register_exception_handlers
from app.routers.files import router as files_router
from app.services.storage import ensure_storage

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("terrametric")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_storage()
    init_db()
    logger.info("TerraMetric API ready")
    yield


app = FastAPI(
    title="TerraMetric API",
    description="Geospatial file measurement service for KML and Shapefile uploads.",
    version=__version__,
    lifespan=lifespan,
)
register_exception_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(files_router, prefix="/api")


@app.get("/")
def root():
    return {
        "name": "TerraMetric",
        "tagline": "Precision in every coordinate.",
        "docs": "/docs",
        "health": "/api/health",
    }
