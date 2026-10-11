from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(255))
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    format: Mapped[str] = mapped_column(String(32))
    size_bytes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(40), index=True)
    source_crs: Mapped[str | None] = mapped_column(String(256), nullable=True)
    measurement_crs: Mapped[str | None] = mapped_column(Text, nullable=True)
    measurement_crs_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    projection_strategy: Mapped[str | None] = mapped_column(Text, nullable=True)
    feature_count: Mapped[int] = mapped_column(Integer, default=0)
    measured_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    bbox_west: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_south: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_east: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_north: Mapped[float | None] = mapped_column(Float, nullable=True)
    duplicate_of: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    features: Mapped[list["Feature"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )


class Feature(Base):
    __tablename__ = "features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    feature_index: Mapped[int] = mapped_column(Integer)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    geometry_type: Mapped[str] = mapped_column(String(64))
    geometry_geojson: Mapped[str | None] = mapped_column(Text, nullable=True)
    properties_json: Mapped[str] = mapped_column(Text, default="{}")
    source_crs: Mapped[str | None] = mapped_column(String(256), nullable=True)
    measurement_crs: Mapped[str | None] = mapped_column(Text, nullable=True)
    area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    length_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    measurement_status: Mapped[str] = mapped_column(String(40))
    measurement_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    dataset: Mapped[Dataset] = relationship(back_populates="features")
