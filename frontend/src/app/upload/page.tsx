"use client";

import { useRouter } from "next/navigation";
import { useMemo, useRef, useState } from "react";
import { FileUp, ShieldAlert } from "lucide-react";
import { PageHeader } from "@/components/ui";
import { uploadFile } from "@/lib/api";
import { formatBytes } from "@/lib/format";

const MAX_BYTES = 25 * 1024 * 1024;
const ACCEPT = ".kml,.zip";

export default function UploadPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [drag, setDrag] = useState(false);
  const [progress, setProgress] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastHash = useRef<string>("");

  const detected = useMemo(() => {
    if (!file) return null;
    const name = file.name.toLowerCase();
    if (name.endsWith(".kml")) return "KML · EPSG:4326 by specification";
    if (name.endsWith(".zip")) return "ZIP archive · expected shapefile set";
    return "Unsupported extension";
  }, [file]);

  function choose(next: File | null) {
    setError(null);
    if (!next) {
      setFile(null);
      return;
    }
    const lower = next.name.toLowerCase();
    if (!lower.endsWith(".kml") && !lower.endsWith(".zip")) {
      setError("Only .kml files and .zip shapefile archives are accepted.");
      setFile(null);
      return;
    }
    if (next.size > MAX_BYTES) {
      setError("File exceeds the 25 MB upload limit.");
      setFile(null);
      return;
    }
    setFile(next);
  }

  async function submit() {
    if (!file || busy) return;
    const fingerprint = `${file.name}:${file.size}:${file.lastModified}`;
    if (fingerprint === lastHash.current) {
      setError("This file was just submitted. Open the previous result instead of uploading twice.");
      return;
    }
    setBusy(true);
    setProgress(0);
    setError(null);
    try {
      lastHash.current = fingerprint;
      const dataset = await uploadFile(file, setProgress);
      router.push(`/files/${dataset.id}`);
    } catch (err) {
      lastHash.current = "";
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        kicker="Ingest"
        title="Upload studio"
        description="Drop a KML document or a ZIP that contains a shapefile. TerraMetric validates the payload, extracts geometries, and measures polygon area and line length in a projected CRS."
      />

      <div className="grid gap-6 lg:grid-cols-[1.4fr_0.8fr]">
        <section className="panel rounded-xl p-6">
          <label
            onDragOver={(e) => {
              e.preventDefault();
              setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDrag(false);
              choose(e.dataTransfer.files[0] || null);
            }}
            className={`flex min-h-64 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed px-6 text-center transition ${
              drag ? "border-[var(--lime)] bg-[var(--lime-dim)]" : "border-[var(--line-strong)] bg-black/10"
            }`}
          >
            <FileUp className="mb-3 text-[var(--lime)]" />
            <span className="font-display text-xl">Drop a geospatial file</span>
            <span className="mt-2 max-w-sm text-sm text-[var(--muted)]">
              Accepted formats: .kml and .zip (shapefile). Maximum size 25 MB. ZIP archives are scanned for path traversal and decompression limits.
            </span>
            <input
              ref={inputRef}
              className="sr-only"
              type="file"
              accept={ACCEPT}
              onChange={(e) => choose(e.target.files?.[0] || null)}
            />
            <span className="mt-4 rounded-md border border-[var(--line)] px-3 py-1.5 text-sm">
              Browse files
            </span>
          </label>

          {file ? (
            <div className="mt-5 rounded-lg border border-[var(--line)] p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-medium">{file.name}</p>
                  <p className="font-mono text-xs text-[var(--muted)]">
                    {formatBytes(file.size)} · {detected}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => choose(null)}
                  className="text-xs text-[var(--muted)] hover:text-[var(--text)]"
                >
                  Remove
                </button>
              </div>
              {busy ? (
                <div className="mt-4">
                  <div className="mb-1 flex justify-between text-xs text-[var(--muted)]">
                    <span>{progress < 100 ? "Uploading" : "Processing geometries"}</span>
                    <span>{progress}%</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                    <div className="h-full bg-[var(--lime)]" style={{ width: `${Math.max(progress, 8)}%` }} />
                  </div>
                </div>
              ) : null}
              <button
                type="button"
                disabled={busy}
                onClick={submit}
                className="mt-4 rounded-md bg-[var(--lime)] px-4 py-2 text-sm font-medium text-[#111827] disabled:opacity-60"
              >
                {busy ? "Working…" : "Process dataset"}
              </button>
            </div>
          ) : null}

          {error ? (
            <p className="mt-4 flex items-start gap-2 text-sm text-[var(--danger)]" role="alert">
              <ShieldAlert size={16} className="mt-0.5" />
              {error}
            </p>
          ) : null}
        </section>

        <aside className="space-y-4">
          <div className="panel rounded-xl p-5">
            <h2 className="font-display text-lg">What happens next</h2>
            <ol className="mt-3 space-y-3 text-sm text-[var(--muted)]">
              <li>1. File metadata is stored with a content hash to avoid accidental duplicates.</li>
              <li>2. Features are extracted with geometry type, properties, and source CRS.</li>
              <li>3. Area and length are computed after projecting to UTM or centered LAEA.</li>
              <li>4. Results persist so you can reopen the map and measurement table later.</li>
            </ol>
          </div>
          <div className="panel rounded-xl p-5 text-sm text-[var(--muted)]">
            <h2 className="font-display text-lg text-[var(--text)]">Limitations</h2>
            <p className="mt-2 leading-6">
              Point features are catalogued but not measured. Mixed geometry collections are recorded as unsupported rather than silently approximated. Missing shapefile CRS blocks ground measurements on purpose.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
