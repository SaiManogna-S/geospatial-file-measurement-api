"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Download, Map as MapIcon } from "lucide-react";
import { DatasetMapLoader } from "@/components/map/DatasetMapLoader";
import { EmptyState, PageHeader, Skeleton, StatusChip } from "@/components/ui";
import { csvUrl, getFile, getGeoJson, getMeasurements } from "@/lib/api";
import { formatArea, formatBytes, formatDate, formatLength, formatNumber } from "@/lib/format";
import type { DatasetDetail, FeatureMeasurement, GeoJSONResponse, MeasurementPage } from "@/lib/types";

const TYPES = ["", "Polygon", "MultiPolygon", "LineString", "MultiLineString", "Point", "GeometryCollection"];

export default function FileDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [tab, setTab] = useState<"map" | "table" | "meta">("map");
  const [dataset, setDataset] = useState<DatasetDetail | null>(null);
  const [geojson, setGeojson] = useState<GeoJSONResponse | null>(null);
  const [page, setPage] = useState<MeasurementPage | null>(null);
  const [selected, setSelected] = useState<FeatureMeasurement | null>(null);
  const [q, setQ] = useState("");
  const [geometryType, setGeometryType] = useState("");
  const [sort, setSort] = useState("feature_index");
  const [order, setOrder] = useState<"asc" | "desc">("asc");
  const [pageNo, setPageNo] = useState(1);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [file, measures, gj] = await Promise.all([
        getFile(id),
        getMeasurements(id, { q, geometry_type: geometryType, sort, order, page: pageNo, page_size: 12 }),
        getGeoJson(id),
      ]);
      setDataset(file);
      setPage(measures);
      setGeojson(gj);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load dataset");
    }
  }, [id, q, geometryType, sort, order, pageNo]);

  useEffect(() => {
    load();
  }, [load]);

  if (error) {
    return <EmptyState title="Dataset unavailable" body={error} href="/" action="Back to overview" />;
  }
  if (!dataset) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-16" />
        <Skeleton className="h-[540px]" />
      </div>
    );
  }

  const totalPages = page ? Math.max(1, Math.ceil(page.total / page.page_size)) : 1;

  return (
    <div>
      <PageHeader
        kicker="Dataset"
        title={dataset.original_filename}
        description={`${dataset.format.toUpperCase()} · ${formatBytes(dataset.size_bytes)} · source ${dataset.source_crs || "CRS not detected"}`}
        actions={
          <div className="flex flex-wrap gap-2">
            <a
              href={csvUrl(dataset.id)}
              className="inline-flex items-center gap-2 rounded-md border border-[var(--line-strong)] px-3 py-2 text-sm"
            >
              <Download size={14} />
              Export CSV
            </a>
            <Link href="/upload" className="inline-flex items-center gap-2 rounded-md bg-[var(--lime)] px-3 py-2 text-sm font-medium text-[#111827]">
              Upload another
            </Link>
          </div>
        }
      />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <StatusChip status={dataset.status} />
        <span className="text-xs text-[var(--muted)]">{dataset.feature_count} features</span>
        <span className="text-xs text-[var(--muted)]">{dataset.measured_count} measured</span>
        {dataset.warning ? <span className="text-xs text-[var(--warn)]">{dataset.warning}</span> : null}
        {dataset.error_summary ? <span className="text-xs text-[var(--danger)]">{dataset.error_summary}</span> : null}
      </div>

      <div className="mb-4 flex gap-2" role="tablist">
        {(
          [
            ["map", "Map workspace"],
            ["table", "Measurements"],
            ["meta", "File details"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={`rounded-md px-3 py-1.5 text-sm ${
              tab === key ? "bg-[var(--lime-dim)] text-[var(--lime)]" : "text-[var(--muted)] hover:bg-white/5"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "map" ? (
        geojson ? (
          geojson.features.length ? (
            <DatasetMapLoader data={geojson} />
          ) : (
            <EmptyState
              title="No map geometries yet"
              body="Nothing was transformed into WGS84 for display. This is not sample map data — the table may still contain measurement notes."
            />
          )
        ) : (
          <Skeleton className="h-[540px]" />
        )
      ) : null}

      {tab === "table" && page ? (
        <section className="grid gap-5 lg:grid-cols-[1.5fr_0.7fr]">
          <div className="panel overflow-hidden rounded-xl">
            <div className="flex flex-wrap gap-3 border-b border-[var(--line)] p-4">
              <input
                aria-label="Search features"
                placeholder="Search id, type, or properties"
                value={q}
                onChange={(e) => {
                  setPageNo(1);
                  setQ(e.target.value);
                }}
                className="min-w-48 flex-1 rounded-md border border-[var(--line)] bg-transparent px-3 py-2 text-sm"
              />
              <select
                aria-label="Filter geometry type"
                value={geometryType}
                onChange={(e) => {
                  setPageNo(1);
                  setGeometryType(e.target.value);
                }}
                className="rounded-md border border-[var(--line)] bg-[var(--bg-panel)] px-3 py-2 text-sm"
              >
                <option value="">All types</option>
                {TYPES.filter(Boolean).map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
              <select
                aria-label="Sort measurements"
                value={`${sort}:${order}`}
                onChange={(e) => {
                  const [s, o] = e.target.value.split(":");
                  setSort(s);
                  setOrder(o as "asc" | "desc");
                }}
                className="rounded-md border border-[var(--line)] bg-[var(--bg-panel)] px-3 py-2 text-sm"
              >
                <option value="feature_index:asc">Index</option>
                <option value="area_m2:desc">Area</option>
                <option value="length_m:desc">Length</option>
                <option value="geometry_type:asc">Type</option>
              </select>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
                  <tr>
                    <th className="px-4 py-3">ID</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Area</th>
                    <th className="px-4 py-3">Length</th>
                    <th className="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {page.items.map((item) => (
                    <tr
                      key={item.id}
                      onClick={() => setSelected(item)}
                      className="cursor-pointer border-t border-[var(--line)] hover:bg-white/[0.03]"
                    >
                      <td className="px-4 py-3 font-mono text-xs">{item.feature_id || item.feature_index}</td>
                      <td className="px-4 py-3">{item.geometry_type}</td>
                      <td className="px-4 py-3 font-mono">{formatArea(item.area_m2)}</td>
                      <td className="px-4 py-3 font-mono">{formatLength(item.length_m)}</td>
                      <td className="px-4 py-3">
                        <StatusChip status={item.measurement_status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between border-t border-[var(--line)] px-4 py-3 text-xs text-[var(--muted)]">
              <span>
                {page.total} features · units {page.units.area} / {page.units.length}
              </span>
              <div className="flex gap-2">
                <button disabled={pageNo <= 1} onClick={() => setPageNo((n) => n - 1)}>
                  Prev
                </button>
                <span>
                  {pageNo} / {totalPages}
                </span>
                <button disabled={pageNo >= totalPages} onClick={() => setPageNo((n) => n + 1)}>
                  Next
                </button>
              </div>
            </div>
          </div>
          <aside className="panel rounded-xl p-5">
            <h2 className="font-display text-lg">Feature detail</h2>
            {!selected ? (
              <p className="mt-3 text-sm text-[var(--muted)]">Select a row to inspect properties, CRS, and measurement notes.</p>
            ) : (
              <dl className="mt-4 space-y-3 text-sm">
                <Row label="Feature ID" value={selected.feature_id || String(selected.feature_index)} />
                <Row label="Geometry" value={selected.geometry_type} />
                <Row label="Source CRS" value={selected.source_crs || "—"} />
                <Row label="Measurement CRS" value={selected.measurement_crs || "—"} />
                <Row label="Area" value={selected.area_m2 == null ? "—" : `${formatNumber(selected.area_m2, 3)} m²`} />
                <Row label="Length" value={selected.length_m == null ? "—" : `${formatNumber(selected.length_m, 3)} m`} />
                <Row label="Note" value={selected.measurement_note || "—"} />
                <div>
                  <dt className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">Properties</dt>
                  <dd className="font-mono mt-1 whitespace-pre-wrap break-all text-xs text-[var(--text)]">
                    {JSON.stringify(selected.properties, null, 2)}
                  </dd>
                </div>
              </dl>
            )}
            <p className="mt-6 text-xs leading-5 text-[var(--muted)]">{page.crs_notes}</p>
          </aside>
        </section>
      ) : null}

      {tab === "meta" ? (
        <section className="panel rounded-xl p-6">
          <div className="mb-4 flex items-center gap-2 text-[var(--teal)]">
            <MapIcon size={16} />
            <h2 className="font-display text-lg text-[var(--text)]">Processing history</h2>
          </div>
          <dl className="grid gap-4 sm:grid-cols-2">
            <Row label="Dataset ID" value={dataset.id} />
            <Row label="Received" value={formatDate(dataset.created_at)} />
            <Row label="Processed" value={formatDate(dataset.processed_at)} />
            <Row label="Content hash" value={dataset.content_hash} />
            <Row label="Source CRS" value={dataset.source_crs || "Missing"} />
            <Row label="Measurement CRS" value={dataset.measurement_crs_name || "—"} />
            <Row label="Errors" value={String(dataset.error_count)} />
            <Row label="Extent (WGS84)" value={
              dataset.bbox_west == null
                ? "—"
                : `${dataset.bbox_west.toFixed(5)}, ${dataset.bbox_south?.toFixed(5)} → ${dataset.bbox_east?.toFixed(5)}, ${dataset.bbox_north?.toFixed(5)}`
            } />
          </dl>
          <p className="mt-6 max-w-3xl text-sm leading-6 text-[var(--muted)]">
            {dataset.projection_strategy || "Projection strategy is recorded after geometries are read."}
          </p>
        </section>
      ) : null}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">{label}</dt>
      <dd className="mt-1 break-all">{value}</dd>
    </div>
  );
}
