from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorBody(BaseModel):
    detail: str
    code: str | None = None


class DatasetSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    format: str
    size_bytes: int
    status: str
    source_crs: str | None
    measurement_crs_name: str | None
    projection_strategy: str | None
    feature_count: int
    measured_count: int
    error_count: int
    warning: str | None
    error_summary: str | None
    duplicate_of: str | None
    created_at: datetime
    processed_at: datetime | None


class DatasetDetail(DatasetSummary):
    content_hash: str
    measurement_crs: str | None
    bbox_west: float | None
    bbox_south: float | None
    bbox_east: float | None
    bbox_north: float | None


class FeatureMeasurement(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    feature_index: int
    feature_id: str | None = Field(default=None, validation_alias="external_id")
    geometry_type: str
    properties: dict[str, Any]
    source_crs: str | None
    measurement_crs: str | None
    area_m2: float | None
    length_m: float | None
    measurement_status: str
    measurement_note: str | None
    geometry: dict[str, Any] | None = None


class MeasurementPage(BaseModel):
    dataset_id: str
    total: int
    page: int
    page_size: int
    units: dict[str, str]
    crs_notes: str
    items: list[FeatureMeasurement]


class DatasetList(BaseModel):
    total: int
    items: list[DatasetSummary]


class StatsResponse(BaseModel):
    files: int
    completed_files: int
    features: int
    polygons: int
    lines: int
    points: int
    total_area_m2: float
    total_length_m: float


class GeoJSONResponse(BaseModel):
    type: str = "FeatureCollection"
    crs_display: str = "EPSG:4326"
    features: list[dict[str, Any]]
    bbox: list[float] | None = None
    legend: list[dict[str, str]]
