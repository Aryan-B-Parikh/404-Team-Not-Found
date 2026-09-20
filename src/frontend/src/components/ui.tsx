// Shared UI atoms — import from here in every tab. (Owner: W4)
import { useEffect, useState } from "react";

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`card p-4 ${className}`}>{children}</div>;
}

export function Kpi({ label, value, sub, tone }: { label: string; value: React.ReactNode; sub?: string; tone?: string }) {
  return (
    <div className="card-2 p-3">
      <div className="muted text-xs uppercase tracking-wide">{label}</div>
      <div className="text-2xl font-semibold" style={tone ? { color: tone } : undefined}>{value}</div>
      {sub && <div className="muted text-xs mt-1">{sub}</div>}
    </div>
  );
}

export function Level({ level }: { level: string }) {
  const map: Record<string, string> = { CRIT: "#fb7185", HIGH: "#fb923c", ELEVATED: "#fbbf24", LOW: "#2dd4bf" };
  return (
    <span className="chip" style={{ color: map[level] ?? "#93a4bf", borderColor: map[level] ?? "#23324e" }}>
      {level}
    </span>
  );
}

export function Sparkline({ data, color = "#2dd4bf" }: { data: number[]; color?: string }) {
  if (!data?.length) return null;
  const w = 160, h = 34, min = Math.min(...data), max = Math.max(...data), r = max - min || 1;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / r) * h}`).join(" ");
  return (
    <svg width={w} height={h} role="img" aria-label="recent index trend">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.6" />
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
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return { data, err, loading, setData };
}

export function Loading({ what }: { what: string }) {
  return <div className="muted">{what}… (first call trains LightGBM + solves CP-SAT, ~20s)</div>;
}

export function ErrorBox({ err }: { err: string }) {
  return <div style={{ color: "var(--bad)" }}>{err}</div>;
}
