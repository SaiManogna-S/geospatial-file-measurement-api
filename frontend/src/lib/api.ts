import type {
  DatasetDetail,
  DatasetList,
  GeoJSONResponse,
  MeasurementPage,
  StatsResponse,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

async function parseError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    /* ignore */
  }
  return `Request failed (${response.status})`;
}

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { Accept: "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return response.json() as Promise<T>;
}

export function listFiles() {
  return getJson<DatasetList>("/api/files/");
}

export function getStats() {
  return getJson<StatsResponse>("/api/files/stats");
}

export function getFile(id: string) {
  return getJson<DatasetDetail>(`/api/files/${id}/`);
}

export function getMeasurements(
  id: string,
  params: Record<string, string | number | undefined>
) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  return getJson<MeasurementPage>(`/api/files/${id}/measurements/?${search.toString()}`);
}

export function getGeoJson(id: string) {
  return getJson<GeoJSONResponse>(`/api/files/${id}/geojson`);
}

export function csvUrl(id: string) {
  return `${API_BASE}/api/files/${id}/measurements.csv`;
}

export function uploadFile(
  file: File,
  onProgress: (pct: number) => void
): Promise<DatasetDetail> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/api/files/`);
    xhr.responseType = "json";
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr.response as DatasetDetail);
        return;
      }
      const detail =
        (xhr.response && xhr.response.detail) ||
        `Upload failed (${xhr.status})`;
      reject(new Error(detail));
    };
    xhr.onerror = () => reject(new Error("Network error while uploading the file."));
    const data = new FormData();
    data.append("file", file);
    xhr.send(data);
  });
}
