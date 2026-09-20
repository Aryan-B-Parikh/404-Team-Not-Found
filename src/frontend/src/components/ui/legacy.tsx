import React, { useEffect, useState } from "react";
import { cn } from "../../lib/utils";
import { StatusBadge } from "./StatusBadge";
import { SkeletonKpi, SkeletonCard } from "./Skeleton";
import { ErrorState } from "./ErrorState";

export interface KpiProps {
  label: string;
  value: React.ReactNode;
  sub?: string;
  tone?: string;
  className?: string;
}

export function Kpi({ label, value, sub, tone, className }: KpiProps) {
  return (
    <div className={cn("p-3 sm:p-4 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] space-y-1 shadow-xs transition-colors overflow-hidden", className)}>
      <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)] truncate">{label}</div>
      <div className="text-xl sm:text-2xl lg:text-[28px] font-bold tracking-tight text-[var(--text-primary)] tnum leading-tight truncate" style={tone ? { color: tone } : undefined}>
        {value}
      </div>
      {sub && <div className="text-[11px] text-[var(--text-secondary)] font-normal truncate">{sub}</div>}
    </div>
  );
}

export function Level({ level }: { level: string }) {
  return <StatusBadge status={level} size="xs" />;
}

export function Sparkline({ data, color = "var(--brand)" }: { data: number[]; color?: string }) {
  if (!data?.length) return null;
  const w = 140,
    h = 32,
    min = Math.min(...data),
    max = Math.max(...data),
    r = max - min || 1;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / r) * h}`).join(" ");
  return (
    <svg width={w} height={h} role="img" aria-label="recent index trend" className="overflow-visible">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let alive = true;
    setLoading(true);
    fn()
      .then((d) => alive && (setData(d), setErr(null)))
      .catch((e) => alive && setErr(String(e)))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return { data, err, loading, setData };
}

export function Loading({ what }: { what: string }) {
  return (
    <div className="space-y-4 animate-in fade-in duration-200">
      <div className="flex items-center gap-2 text-xs font-medium text-[var(--text-secondary)]">
        <span className="w-2 h-2 rounded-full bg-[var(--accent)] animate-ping" />
        <span>{what}… (retrieving operational telemetry and ML models)</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <SkeletonKpi />
        <SkeletonKpi />
        <SkeletonKpi />
        <SkeletonKpi />
      </div>
      <div className="grid md:grid-cols-2 gap-4">
        <SkeletonCard />
        <SkeletonCard />
      </div>
    </div>
  );
}

export function ErrorBox({ err, onRetry }: { err: string; onRetry?: () => void }) {
  const isNetwork =
    err?.toLowerCase().includes("failed to fetch") ||
    err?.toLowerCase().includes("network") ||
    err?.toLowerCase().includes("econnrefused") ||
    err?.toLowerCase().includes("500");

  const cleanMessage = isNetwork
    ? "The telemetry service on port 8000 is temporarily unavailable. Check backend processes or retry connection."
    : err.length > 140
    ? `${err.slice(0, 140)}...`
    : err;

  return (
    <ErrorState
      title="Unable to load operational telemetry"
      message={cleanMessage}
      onRetry={onRetry || (() => window.location.reload())}
    />
  );
}
