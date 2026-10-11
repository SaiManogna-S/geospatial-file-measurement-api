export type DatasetStatus =
  | "queued"
  | "processing"
  | "completed"
  | "completed_with_errors"
  | "failed";

export type DatasetSummary = {
  id: string;
  original_filename: string;
  format: string;
  size_bytes: number;
  status: DatasetStatus;
  source_crs: string | null;
  measurement_crs_name: string | null;
  projection_strategy: string | null;
  feature_count: number;
  measured_count: number;
  error_count: number;
  warning: string | null;
  error_summary: string | null;
  duplicate_of: string | null;
  created_at: string;
  processed_at: string | null;
};

export type DatasetDetail = DatasetSummary & {
  content_hash: string;
  measurement_crs: string | null;
  bbox_west: number | null;
  bbox_south: number | null;
  bbox_east: number | null;
  bbox_north: number | null;
};

export type FeatureMeasurement = {
  id: number;
  feature_index: number;
  feature_id: string | null;
  geometry_type: string;
  properties: Record<string, unknown>;
  source_crs: string | null;
  measurement_crs: string | null;
  area_m2: number | null;
  length_m: number | null;
  measurement_status: string;
  measurement_note: string | null;
  geometry?: Record<string, unknown> | null;
};

export type MeasurementPage = {
  dataset_id: string;
  total: number;
  page: number;
  page_size: number;
  units: { area: string; length: string };
  crs_notes: string;
  items: FeatureMeasurement[];
};

export type DatasetList = {
  total: number;
  items: DatasetSummary[];
};

export type StatsResponse = {
  files: number;
  completed_files: number;
  features: number;
  polygons: number;
  lines: number;
  points: number;
  total_area_m2: number;
  total_length_m: number;
};

export type GeoJSONFeature = {
  type: "Feature";
  id?: number;
  geometry: { type: string; coordinates: unknown };
  properties: Record<string, unknown>;
};

export type GeoJSONResponse = {
  type: "FeatureCollection";
  crs_display: string;
  features: GeoJSONFeature[];
  bbox: number[] | null;
  legend: { type: string; label: string; color: string }[];
};
