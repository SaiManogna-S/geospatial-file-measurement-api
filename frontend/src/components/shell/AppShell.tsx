"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Compass,
  FolderOpen,
  LayoutDashboard,
  MapPinned,
  Menu,
  Upload,
  X,
} from "lucide-react";
import { useState } from "react";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/upload", label: "Upload studio", icon: Upload },
];

function Mark() {
  return (
    <span className="relative grid h-9 w-9 place-items-center rounded-md border border-[var(--line-strong)] bg-[var(--bg-panel-2)]">
      <span className="absolute h-5 w-px bg-[var(--lime)]" />
      <span className="absolute w-5 h-px bg-[var(--lime)]" />
      <span className="h-2 w-2 rounded-full border border-[var(--teal)]" />
    </span>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[240px_1fr]">
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 border-r border-[var(--line)] bg-[var(--bg-elev)] p-5 transition lg:static lg:block lg:w-auto ${
          open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        <div className="mb-8 flex items-center justify-between gap-3">
          <Link href="/" className="flex items-center gap-3" onClick={() => setOpen(false)}>
            <Mark />
            <span>
              <span className="font-display block text-lg tracking-tight">TerraMetric</span>
              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-[var(--muted)]">
                AEREO workspace
              </span>
            </span>
          </Link>
          <button className="lg:hidden" onClick={() => setOpen(false)} aria-label="Close navigation">
            <X size={18} />
          </button>
        </div>
        <p className="mb-6 text-xs leading-5 text-[var(--muted)]">Precision in every coordinate.</p>
        <nav className="space-y-1" aria-label="Workspace">
          {NAV.map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm transition ${
                  active
                    ? "bg-[var(--lime-dim)] text-[var(--lime)]"
                    : "text-[var(--muted)] hover:bg-white/5 hover:text-[var(--text)]"
                }`}
              >
                <Icon size={16} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-10 rounded-lg border border-[var(--line)] p-4">
          <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
            <Compass size={14} />
            Units
          </div>
          <p className="text-sm text-[var(--text)]">Area in m² · Length in m</p>
          <p className="mt-2 text-xs leading-5 text-[var(--muted)]">
            Ground measurements use a projected CRS. Geographic degrees are never used as metres.
          </p>
        </div>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-30 flex items-center justify-between gap-4 border-b border-[var(--line)] bg-[rgba(11,16,22,0.88)] px-4 py-3 backdrop-blur-md lg:px-8">
          <button className="lg:hidden" onClick={() => setOpen(true)} aria-label="Open navigation">
            <Menu size={18} />
          </button>
          <div className="flex items-center gap-2 text-xs text-[var(--muted)]">
            <MapPinned size={14} className="text-[var(--teal)]" />
            <span className="font-mono uppercase tracking-[0.16em]">Survey workspace</span>
          </div>
          <Link
            href="/upload"
            className="inline-flex items-center gap-2 rounded-md bg-[var(--lime)] px-3 py-1.5 text-sm font-medium text-[#111827]"
          >
            <FolderOpen size={14} />
            New dataset
          </Link>
        </header>
        <main className="px-4 py-6 lg:px-8 lg:py-8">{children}</main>
      </div>
    </div>
  );
}
