export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(value);
}

export function formatArea(m2: number | null | undefined): string {
  if (m2 === null || m2 === undefined) return "—";
  if (Math.abs(m2) >= 1_000_000) {
    return `${formatNumber(m2 / 1_000_000, 3)} km²`;
  }
  return `${formatNumber(m2, 2)} m²`;
}

export function formatLength(m: number | null | undefined): string {
  if (m === null || m === undefined) return "—";
  if (Math.abs(m) >= 1000) {
    return `${formatNumber(m / 1000, 3)} km`;
  }
  return `${formatNumber(m, 2)} m`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function statusLabel(status: string): string {
  return status.replaceAll("_", " ");
}
