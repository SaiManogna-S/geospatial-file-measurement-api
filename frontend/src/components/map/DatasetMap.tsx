"use client";

import { useEffect, useMemo } from "react";
import { GeoJSON, MapContainer, ScaleControl, TileLayer, useMap } from "react-leaflet";
import type { Feature, FeatureCollection, GeoJsonObject } from "geojson";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { formatArea, formatLength } from "@/lib/format";
import type { GeoJSONResponse } from "@/lib/types";

function FitBounds({ data }: { data: GeoJSONResponse }) {
  const map = useMap();
  useEffect(() => {
    const bounds = L.geoJSON(data as unknown as FeatureCollection).getBounds();
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [28, 28], maxZoom: 16 });
      return;
    }

    if (data.bbox && data.bbox.length === 4 && data.bbox.every(Number.isFinite)) {
      const [west, south, east, north] = data.bbox;
      if (west <= east && south <= north) {
        map.fitBounds(
          [
            [south, west],
            [north, east],
          ],
          { padding: [28, 28], maxZoom: 16 }
        );
      }
    }
  }, [data, map]);
  return null;
}

function geomStyle(feature?: Feature) {
  const type = feature?.geometry?.type || "";
  if (type.includes("Polygon")) {
    return { color: "#C8F542", weight: 1.4, fillColor: "#C8F542", fillOpacity: 0.22 };
  }
  if (type.includes("Line")) {
    return { color: "#2DD4BF", weight: 2.4, opacity: 0.95 };
  }
  return { color: "#F8FAFC", weight: 1 };
}

export function DatasetMap({ data = null }: { data?: GeoJSONResponse | null }) {
  const pointToLayer = useMemo(
    () => (feature: Feature, latlng: L.LatLng) =>
      L.circleMarker(latlng, {
        radius: 6,
        color: "#F8FAFC",
        weight: 1.5,
        fillColor: "#2DD4BF",
        fillOpacity: 0.9,
      }),
    []
  );

  function onEachFeature(feature: Feature, layer: L.Layer) {
    const props = feature.properties || {};
    const title = String(props.feature_id || `Feature ${props.feature_index ?? ""}`);
    const area = formatArea(typeof props.area_m2 === "number" ? props.area_m2 : null);
    const length = formatLength(typeof props.length_m === "number" ? props.length_m : null);
    const popup = document.createElement("div");
    popup.style.minWidth = "180px";

    const geometryType = document.createElement("div");
    geometryType.style.cssText = "font-size:11px;letter-spacing:.16em;text-transform:uppercase;opacity:.7";
    geometryType.textContent = String(props.geometry_type || "");

    const heading = document.createElement("strong");
    heading.textContent = title;

    const measurements = document.createElement("div");
    measurements.style.cssText = "margin-top:8px;font-family:IBM Plex Mono,monospace;font-size:12px";
    measurements.append(`Area ${area}`, document.createElement("br"), `Length ${length}`);

    popup.append(geometryType, heading, measurements);
    layer.bindPopup(popup);
  }

  if (!data) {
    return (
      <div className="grid h-[540px] place-items-center rounded-xl border border-[var(--line)] bg-[var(--bg-panel)] px-6">
        <div className="max-w-sm text-center">
          <h2 className="font-display text-lg text-[var(--text)]">No dataset selected</h2>
          <p className="mt-2 text-sm text-[var(--muted)]">
            Choose an uploaded dataset to explore its polygon, line, and point geometries on the map.
          </p>
        </div>
      </div>
    );
  }

  if (!data.features.length) {
    return (
      <div className="grid h-[540px] place-items-center rounded-xl border border-[var(--line)] bg-[var(--bg-panel)] px-6">
        <div className="max-w-sm text-center">
          <h2 className="font-display text-lg text-[var(--text)]">No map geometries available</h2>
          <p className="mt-2 text-sm text-[var(--muted)]">
            This dataset has no displayable WGS84 geometry. Measurements may still exist in the table if the source CRS was projected.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden rounded-xl border border-[var(--line)]">
      <MapContainer
        center={[20, 0]}
        zoom={2}
        className="h-[540px] w-full"
        scrollWheelZoom
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
          className="terrametric-dark-basemap"
          maxZoom={19}
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <GeoJSON
          data={data as unknown as GeoJsonObject}
          style={geomStyle}
          pointToLayer={pointToLayer}
          onEachFeature={onEachFeature}
        />
        <FitBounds data={data} />
        <ScaleControl imperial={false} />
      </MapContainer>
      <div className="pointer-events-none absolute bottom-4 left-4 rounded-md border border-[var(--line)] bg-[rgba(11,16,22,0.88)] px-3 py-2 text-xs">
        <div className="mb-1 font-mono uppercase tracking-[0.16em] text-[var(--muted)]">Legend</div>
        {data.legend.map((item) => (
          <div key={item.type} className="flex items-center gap-2 py-0.5">
            <span className="h-2 w-4 rounded-sm" style={{ background: item.color }} />
            {item.label}
          </div>
        ))}
      </div>
    </div>
  );
}
