import Link from "next/link";
import { statusLabel } from "@/lib/format";

export function PageHeader({
  kicker,
  title,
  description,
  actions,
}: {
  kicker: string;
  title: string;
  description: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p className="font-mono mb-2 text-[11px] uppercase tracking-[0.22em] text-[var(--teal)]">
          {kicker}
        </p>
        <h1 className="font-display text-3xl tracking-tight md:text-4xl">{title}</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">{description}</p>
      </div>
      {actions}
    </div>
  );
}

export function StatusChip({ status }: { status: string }) {
  const tone =
    status === "completed"
      ? "text-[var(--lime)] bg-[var(--lime-dim)]"
      : status === "failed"
        ? "text-[var(--danger)] bg-[rgba(251,113,133,0.12)]"
        : status.includes("error")
          ? "text-[var(--warn)] bg-[rgba(251,191,36,0.12)]"
          : "text-[var(--teal)] bg-[var(--teal-dim)]";
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] capitalize ${tone}`}>
      {statusLabel(status)}
    </span>
  );
}

export function EmptyState({
  title,
  body,
  href,
  action,
}: {
  title: string;
  body: string;
  href?: string;
  action?: string;
}) {
  return (
    <div className="panel rounded-xl px-6 py-14 text-center">
      <div className="mx-auto mb-4 h-16 w-16 rounded-full border border-dashed border-[var(--line-strong)]" />
      <h2 className="font-display text-xl">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-[var(--muted)]">{body}</p>
      {href && action ? (
        <Link
          href={href}
          className="mt-5 inline-flex rounded-md bg-[var(--lime)] px-4 py-2 text-sm font-medium text-[#111827]"
        >
          {action}
        </Link>
      ) : null}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-white/5 ${className}`} />;
}
