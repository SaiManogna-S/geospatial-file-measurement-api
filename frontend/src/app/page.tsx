"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowUpRight, Layers3, Ruler, Shapes, Waypoints } from "lucide-react";
import { EmptyState, PageHeader, Skeleton, StatusChip } from "@/components/ui";
import { getStats, listFiles } from "@/lib/api";
import { formatArea, formatBytes, formatDate, formatLength, formatNumber } from "@/lib/format";
import type { DatasetSummary, StatsResponse } from "@/lib/types";

export default function OverviewPage() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [files, setFiles] = useState<DatasetSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getStats(), listFiles()])
      .then(([s, list]) => {
        setStats(s);
        setFiles(list.items);
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <div>
      <PageHeader
        kicker="Workspace"
        title="Overview"
        description="Live counts from processed KML and Shapefile datasets. Empty cards mean this workspace has not received files yet — nothing here is simulated."
        actions={
          <Link
            href="/upload"
            className="inline-flex items-center gap-2 rounded-md border border-[var(--line-strong)] px-4 py-2 text-sm text-[var(--text)]"
          >
            Open upload studio
            <ArrowUpRight size={16} />
          </Link>
        }
      />

      {error ? (
        <div className="panel mb-6 rounded-xl p-4 text-sm text-[var(--danger)]">
          Could not reach the TerraMetric API. Start the backend on port 8000. {error}
        </div>
      ) : null}

      <section className="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {!stats ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28" />)
        ) : (
          <>
            <StatCard icon={Layers3} label="Datasets" value={formatNumber(stats.files, 0)} hint={`${stats.completed_files} processed`} />
            <StatCard icon={Shapes} label="Features" value={formatNumber(stats.features, 0)} hint={`${stats.polygons} polygons`} />
            <StatCard icon={Ruler} label="Measured area" value={formatArea(stats.total_area_m2)} hint="Projected square metres" />
            <StatCard icon={Waypoints} label="Measured length" value={formatLength(stats.total_length_m)} hint={`${stats.lines} line features`} />
          </>
        )}
      </section>

      <section className="panel overflow-hidden rounded-xl">
        <div className="flex items-center justify-between border-b border-[var(--line)] px-5 py-4">
          <div>
            <h2 className="font-display text-lg">Recent processing</h2>
            <p className="text-xs text-[var(--muted)]">Persisted upload history from SQLite</p>
          </div>
        </div>
        {!files ? (
          <div className="p-5 space-y-3">
            <Skeleton className="h-10" />
            <Skeleton className="h-10" />
          </div>
        ) : files.length === 0 ? (
          <div className="p-5">
            <EmptyState
              title="No datasets yet"
              body="Upload a KML file or a ZIP archive that contains a shapefile. The dashboard will populate from the API as soon as processing finishes."
              href="/upload"
              action="Upload a geospatial file"
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="bg-white/[0.02] text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
                <tr>
                  <th className="px-5 py-3 font-medium">File</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Features</th>
                  <th className="px-5 py-3 font-medium">CRS</th>
                  <th className="px-5 py-3 font-medium">Received</th>
                </tr>
              </thead>
              <tbody>
                {files.map((file) => (
                  <tr key={file.id} className="border-t border-[var(--line)] hover:bg-white/[0.02]">
                    <td className="px-5 py-3">
                      <Link href={`/files/${file.id}`} className="text-[var(--text)] hover:text-[var(--lime)]">
                        {file.original_filename}
                      </Link>
                      <div className="font-mono text-[11px] text-[var(--muted)]">
                        {file.format} · {formatBytes(file.size_bytes)}
                      </div>
                    </td>
                    <td className="px-5 py-3">
                      <StatusChip status={file.status} />
                    </td>
                    <td className="px-5 py-3 font-mono">{file.feature_count}</td>
                    <td className="px-5 py-3 text-[var(--muted)]">{file.source_crs || "Not detected"}</td>
                    <td className="px-5 py-3 text-[var(--muted)]">{formatDate(file.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  hint,
}: {
  icon: typeof Layers3;
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <article className="panel rounded-xl p-5">
      <div className="mb-4 flex items-center justify-between text-[var(--muted)]">
        <span className="text-xs uppercase tracking-[0.16em]">{label}</span>
        <Icon size={16} className="text-[var(--teal)]" />
      </div>
      <p className="font-display text-2xl">{value}</p>
      <p className="mt-1 text-xs text-[var(--muted)]">{hint}</p>
    </article>
  );
}
