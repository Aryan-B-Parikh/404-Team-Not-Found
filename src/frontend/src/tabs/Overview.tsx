// Overview tab — live KPIs, zone heatmap matrix, anomalies, alerts, drill-down
import React, { useState } from "react";
import {
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  CartesianGrid,
  XAxis,
  YAxis,
} from "recharts";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Anchor, Ship, Clock, TrendingUp, Activity, Zap } from "lucide-react";
import { api } from "../lib/api";
import { SkeletonCard } from "../components/ui/Skeleton";
import { ErrorState } from "../components/ui/ErrorState";
import { Collapsible } from "../components/ui/Collapsible";

// ── colour helpers ─────────────────────────────────────────────────────────────
function indexBg(val: number): string {
  if (val >= 80) return "rgba(185, 74, 72, 0.85)";
  if (val >= 60) return "rgba(194, 110, 74, 0.80)";
  if (val >= 40) return "rgba(183, 121, 31, 0.75)";
  if (val >= 20) return "rgba(47, 111, 134, 0.60)";
  return "rgba(30, 60, 80, 0.35)";
}
function indexText(val: number): string {
  return val >= 40 ? "#ffffff" : "rgba(255,255,255,0.7)";
}

const LEVEL_COLORS: Record<string, string> = {
  CRIT: "var(--status-critical)",
  HIGH: "var(--status-warning)",
  ELEVATED: "#fbbf24",
  LOW: "var(--status-success)",
};
const ZONE_LABELS: Record<string, string> = {
  "Z-PORT": "Port (overall)",
  "Z-LBCT": "LBCT Pier E",
  "Z-ITS": "ITS Pier G",
  "Z-PCT": "PCT Pier J",
  "Z-TTI": "TTI Pier T",
};

// ── Heatmap matrix ─────────────────────────────────────────────────────────────
function HeatmapMatrix({ zones }: { zones: any[] }) {
  // Build 72-column × 5-row heatmap using forecast points baked into zone data
  // zone.recent_index is the sparkline (last 24h); we show it reversed + current
  const COLS = 24;
  const zoneRows = zones.filter((z: any) => z.zone_code !== "Z-PORT");

  return (
    <div className="overflow-x-auto">
      <div style={{ minWidth: 640 }}>
        {/* Header: hour buckets */}
        <div className="flex items-center gap-1 mb-1.5">
          <div className="font-mono text-[10px] text-[var(--text-muted)] shrink-0" style={{ width: 90 }}>Terminal</div>
          <div className="flex-1 grid text-[9px] text-[var(--text-muted)] font-mono text-center" style={{ gridTemplateColumns: `repeat(${COLS}, 1fr)` }}>
            {Array.from({ length: COLS }, (_, i) => (
              <span key={i} className={i % 6 === 0 ? "" : "opacity-0"}>{i === 0 ? "now" : `+${i}h`}</span>
            ))}
          </div>
        </div>
        {zoneRows.map((z: any) => {
          // recent_index = last N hours of history (most-recent last); truncate or pad to COLS
          const hist: number[] = (z.recent_index ?? []).slice(-COLS);
          const cells = Array.from({ length: COLS }, (_, i) => hist[i] ?? z.current_index ?? 0);

          return (
            <div key={z.zone_code} className="flex items-center gap-1 mb-0.5">
              <div className="font-mono text-[10px] text-[var(--text-secondary)] shrink-0 truncate" style={{ width: 90 }} title={ZONE_LABELS[z.zone_code]}>
                {z.zone_code.replace("Z-", "")}
              </div>
              <div className="flex-1 grid gap-px" style={{ gridTemplateColumns: `repeat(${COLS}, 1fr)`, height: 22 }}>
                {cells.map((val, ci) => (
                  <div
                    key={ci}
                    title={`${z.zone_code} +${ci}h: ${val.toFixed(1)}`}
                    style={{
                      background: indexBg(val),
                      borderRadius: 2,
                      height: "100%",
                    }}
                  />
                ))}
              </div>
            </div>
          );
        })}
        {/* Legend */}
        <div className="flex items-center gap-3 mt-2 text-[10px] text-[var(--text-muted)]">
          {[
            { label: "Low (0–20)", bg: "rgba(30, 60, 80, 0.35)" },
            { label: "Moderate (20–40)", bg: "rgba(47, 111, 134, 0.60)" },
            { label: "Elevated (40–60)", bg: "rgba(183, 121, 31, 0.75)" },
            { label: "High (60–80)", bg: "rgba(194, 110, 74, 0.80)" },
            { label: "Critical (80+)", bg: "rgba(185, 74, 72, 0.85)" },
          ].map((l) => (
            <span key={l.label} className="flex items-center gap-1">
              <span style={{ display: "inline-block", width: 10, height: 10, borderRadius: 2, background: l.bg }} />
              {l.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Sparkline using Recharts ───────────────────────────────────────────────────
let _spkSeq = 0;
function TrendSparkline({ data }: { data: number[] }) {
  // Generate a unique gradient id per instance so SVG id="spk" is not duplicated
  // across zone cards (browser would use only the first match for all fill references).
  const [gradId] = React.useState(() => `spk-${++_spkSeq}`);
  if (!data?.length) return null;
  const points = data.map((v, i) => ({ h: i, v }));
  return (
    <ResponsiveContainer width={140} height={34}>
      <AreaChart data={points} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.35} />
            <stop offset="95%" stopColor="var(--accent)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area type="monotone" dataKey="v" stroke="var(--accent)" fill={`url(#${gradId})`} strokeWidth={1.5} dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ── Zone drill-down card ───────────────────────────────────────────────────────
function ZoneCard({ z, hotspot, onClick, selected }: { z: any; hotspot: any; onClick: () => void; selected: boolean }) {
  const level = z.level ?? "LOW";
  const levelColor = LEVEL_COLORS[level] ?? "var(--text-muted)";

  return (
    <div
      onClick={onClick}
      className={`p-3 rounded-lg border cursor-pointer transition-all hover:border-[var(--brand)] ${selected ? "border-[var(--brand)] bg-[var(--brand-soft)]" : "border-[var(--border-default)] bg-[var(--bg-surface)]"}`}
    >
      <div className="flex items-center justify-between">
        <div className="font-medium text-sm">{ZONE_LABELS[z.zone_code] ?? z.zone_code}</div>
        <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded border" style={{ color: levelColor, borderColor: levelColor, background: `${levelColor}18` }}>
          {level}
        </span>
      </div>
      <div className="mt-1.5 flex items-end justify-between gap-2">
        <div>
          <div className="text-xl font-bold font-mono" style={{ color: "var(--accent)" }}>{z.peak_index}</div>
          <div className="text-[10px] text-[var(--text-muted)]">peak +{z.peak_hour}h · now {z.current_index}</div>
          <div className="text-[10px] text-[var(--text-muted)]">q {z.queue_now} · wait {z.wait_now}h · yard {z.yard_util_pct}%</div>
        </div>
        <TrendSparkline data={z.recent_index ?? []} />
      </div>
      {hotspot && (
        <div className="text-[10px] text-[var(--text-muted)] mt-2 pt-2 border-t border-[var(--border-subtle)] flex items-center gap-1.5 flex-wrap">
          <Zap className="w-3 h-3 text-[var(--accent)] shrink-0" />
          risk <b style={{ color: "var(--accent)" }}>{hotspot.risk_score}/100</b>
          · binding <b style={{ color: "var(--accent)" }}>{hotspot.binding_constraint}</b>
          · conf {hotspot.confidence}
        </div>
      )}
    </div>
  );
}

// ── KPI card ──────────────────────────────────────────────────────────────────
function KpiCard({ icon, label, value, sub, tone }: { icon: React.ReactNode; label: string; value: React.ReactNode; sub?: string; tone?: string }) {
  return (
    <div className="p-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
      <div className="flex items-center gap-1.5 mb-1.5">
        <span className="text-[var(--brand)]">{icon}</span>
        <div className="text-[10px] uppercase font-bold text-[var(--text-muted)] tracking-wider truncate">{label}</div>
      </div>
      <div className="text-xl font-bold font-mono" style={{ color: tone ?? "var(--text-primary)" }}>{value}</div>
      {sub && <div className="text-[10px] text-[var(--text-muted)] mt-0.5">{sub}</div>}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function Overview() {
  const [selectedZone, setSelectedZone] = useState<string | null>(null);
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["overview"],
    queryFn: () => api.overview(),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
          {[0,1,2,3,4].map((i) => <SkeletonCard key={i} />)}
        </div>
        <SkeletonCard />
        <div className="grid md:grid-cols-2 gap-4"><SkeletonCard /><SkeletonCard /></div>
      </div>
    );
  }

  if (error || !data) {
    return <ErrorState title="Overview unavailable" message={error instanceof Error ? error.message : "Could not reach /api/overview"} onRetry={() => refetch()} />;
  }

  const k = data.kpis;
  const selectedZoneData = selectedZone ? data.zones.find((z: any) => z.zone_code === selectedZone) : null;
  const selectedHotspot = selectedZone ? data.hotspots?.ranked?.find((r: any) => r.zone_code === selectedZone) : null;

  return (
    <div className="space-y-4">
      {/* KPI strip */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 xl:grid-cols-9 gap-3">
        <KpiCard icon={<Activity className="w-3.5 h-3.5" />} label="Port index" value={k.port_index_now} tone="var(--accent)" />
        <KpiCard icon={<TrendingUp className="w-3.5 h-3.5" />} label="72h peak" value={k.peak_forecast_index} sub={`at +${k.peak_forecast_hour}h`} tone="var(--status-warning)" />
        <KpiCard icon={<Anchor className="w-3.5 h-3.5" />} label="At anchor" value={k.vessels_at_anchor} sub={`${k.vessels_inbound} inbound`} />
        <KpiCard icon={<Clock className="w-3.5 h-3.5" />} label="Avg wait" value={`${k.avg_anchorage_wait}h`} sub={`max ${k.max_anchored_hours}h`} />
        <KpiCard icon={<Ship className="w-3.5 h-3.5" />} label="Berth util" value={`${k.berth_util_pct}%`} />
        <KpiCard icon={<Zap className="w-3.5 h-3.5" />} label="Crane util" value={`${k.crane_util_pct}%`} />
        <KpiCard icon={<Activity className="w-3.5 h-3.5" />} label="Moves pending" value={Number(k.moves_pending).toLocaleString()} />
        <KpiCard icon={<AlertTriangle className="w-3.5 h-3.5" />} label="Fleet burn/day" value={`$${Number(k.daily_fleet_burn_usd).toLocaleString()}`} tone="var(--status-critical)" />
        <KpiCard icon={<Ship className="w-3.5 h-3.5" />} label="Arrivals 24h" value={k.arrivals_next24} />
      </div>

      {/* Heatmap matrix */}
      <div className="p-4 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
        <div className="flex items-center justify-between gap-2 mb-3">
          <h3 className="font-semibold text-sm">Zone congestion heatmap — 24h history</h3>
          <span className="text-[10px] font-mono text-[var(--text-muted)]">{data.dataset?.source}</span>
        </div>
        <HeatmapMatrix zones={data.zones} />
      </div>

      {/* Zone cards grid with drill-down */}
      <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3">
        {data.zones.filter((z: any) => z.zone_code !== "Z-PORT").map((z: any) => {
          const h = data.hotspots?.ranked?.find((r: any) => r.zone_code === z.zone_code);
          return (
            <ZoneCard
              key={z.zone_code}
              z={z}
              hotspot={h}
              onClick={() => setSelectedZone(z.zone_code === selectedZone ? null : z.zone_code)}
              selected={selectedZone === z.zone_code}
            />
          );
        })}
      </div>

      {/* Drill-down panel */}
      {selectedZoneData && (
        <div className="p-4 rounded-lg border border-[var(--brand)] bg-[var(--brand-soft)] space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-sm">{ZONE_LABELS[selectedZoneData.zone_code] ?? selectedZoneData.zone_code} — detail</h3>
            <button onClick={() => setSelectedZone(null)} className="text-[10px] text-[var(--text-muted)] hover:text-[var(--text-primary)] cursor-pointer">✕ Close</button>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: "Current index", value: selectedZoneData.current_index },
              { label: "Peak index", value: `${selectedZoneData.peak_index} @ +${selectedZoneData.peak_hour}h` },
              { label: "Queue", value: `${selectedZoneData.queue_now} vessels` },
              { label: "Avg wait", value: `${selectedZoneData.wait_now}h` },
              { label: "Yard utilisation", value: `${selectedZoneData.yard_util_pct}%` },
              ...(selectedHotspot ? [
                { label: "Risk score", value: `${selectedHotspot.risk_score}/100` },
                { label: "Binding resource", value: selectedHotspot.binding_constraint },
                { label: "Confidence", value: selectedHotspot.confidence },
              ] : []),
            ].map((item) => (
              <div key={item.label} className="p-2.5 rounded bg-[var(--bg-surface)] border border-[var(--border-subtle)]">
                <div className="text-[10px] uppercase text-[var(--text-muted)] font-bold tracking-wider">{item.label}</div>
                <div className="font-mono font-semibold text-sm mt-0.5">{item.value}</div>
              </div>
            ))}
          </div>
          {selectedHotspot?.explanation && (
            <p className="text-xs text-[var(--text-secondary)]">{selectedHotspot.explanation}</p>
          )}
        </div>
      )}

      {/* Alerts + Anomalies */}
      <div className="grid lg:grid-cols-2 gap-4">
        <div className="p-4 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
          <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-[var(--status-warning)]" />
            Active Alerts
          </h3>
          {data.alerts?.length ? (
            <ul className="space-y-2">
              {data.alerts.map((a: any, i: number) => (
                <li key={i} className="p-2.5 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-elevated)]">
                  <div className="flex items-center gap-2">
                    <span
                      className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded border font-mono"
                      style={{
                        color: a.severity === "crit" ? "var(--status-critical)" : a.severity === "warn" ? "var(--status-warning)" : "var(--text-muted)",
                        borderColor: a.severity === "crit" ? "var(--status-critical-border)" : a.severity === "warn" ? "var(--status-warning-border)" : "var(--border-default)",
                        background: a.severity === "crit" ? "var(--status-critical-bg)" : a.severity === "warn" ? "var(--status-warning-bg)" : "transparent",
                      }}
                    >
                      {a.severity}
                    </span>
                    <span className="text-sm font-medium">{a.title}</span>
                  </div>
                  <div className="text-xs text-[var(--text-muted)] mt-1">{a.detail}</div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-xs text-[var(--text-muted)] py-4 text-center">No active alerts.</div>
          )}
        </div>

        {/* Tier 3 — the per-zone anomaly table is engine detail; flagged zones already
            surface as WARN alerts above, so the full table is one click away. */}
        <Collapsible
          summary={
            <span className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-[var(--brand)]" />
              Isolation Forest anomalies
            </span>
          }
          badge={
            <span className="text-[10px] font-mono text-[var(--text-muted)]">
              {data.anomalies?.filter((a: any) => a.is_anomaly).length ?? 0} flagged of {data.anomalies?.length ?? 0}
            </span>
          }
        >
          <div className="overflow-x-auto">
            <table className="w-full min-w-[360px] text-xs">
              <thead>
                <tr className="text-[10px] text-[var(--text-muted)] uppercase">
                  <th className="text-left py-1 pr-2">Zone</th>
                  <th className="text-left pr-2">Kind</th>
                  <th className="text-right pr-2">Score</th>
                  <th className="text-center pr-2">Flagged</th>
                  <th className="text-right">n</th>
                </tr>
              </thead>
              <tbody>
                {data.anomalies?.length ? data.anomalies.map((a: any) => (
                  <tr key={a.zone_code} className="border-t border-[var(--border-subtle)]">
                    <td className="py-1 pr-2 font-mono">{a.zone_code}</td>
                    <td className="pr-2 text-[var(--text-secondary)]">{a.kind}</td>
                    <td className="text-right pr-2 font-mono">{a.score}</td>
                    <td className="text-center pr-2">
                      {a.is_anomaly
                        ? <span className="text-[var(--status-critical)] font-bold">✓</span>
                        : <span className="text-[var(--text-muted)]">–</span>}
                    </td>
                    <td className="text-right text-[var(--text-muted)]">{a.sample_size}</td>
                  </tr>
                )) : (
                  <tr><td colSpan={5} className="text-center py-4 text-[var(--text-muted)]">No anomalies flagged.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Collapsible>
      </div>
    </div>
  );
}
