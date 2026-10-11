"use client";

import dynamic from "next/dynamic";
import type { GeoJSONResponse } from "@/lib/types";

const Map = dynamic(() => import("./DatasetMap").then((mod) => mod.DatasetMap), {
  ssr: false,
  loading: () => (
    <div className="grid h-[540px] place-items-center rounded-xl border border-[var(--line)] bg-[var(--bg-panel)] text-sm text-[var(--muted)]">
      Loading map workspace…
    </div>
  ),
});

export function DatasetMapLoader({ data = null }: { data?: GeoJSONResponse | null }) {
  return <Map data={data} />;
}
