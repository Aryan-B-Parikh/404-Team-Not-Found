// Forecast tab — LightGBM 72h forecast with per-target bands + weather indicator
import { useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";
import { useQuery } from "@tanstack/react-query";
import { CloudSun, CloudLightning, Activity, TrendingUp } from "lucide-react";
import { api } from "../lib/api";
import { SkeletonCard } from "../components/ui/Skeleton";
import { ErrorState } from "../components/ui/ErrorState";
import { Collapsible } from "../components/ui/Collapsible";

const ZONES = ["Z-PORT", "Z-LBCT", "Z-ITS", "Z-PCT", "Z-TTI"];
const ZONE_LABELS: Record<string, string> = {
  "Z-PORT": "Port (all terminals)",
  "Z-LBCT": "LBCT — Pier E",
  "Z-ITS": "ITS — Pier G",
  "Z-PCT": "PCT — Pier J",
  "Z-TTI": "TTI — Pier T",
};

type TargetKey = "index" | "queue" | "wait" | "yard";
interface TargetConfig {
  key: TargetKey;
  label: string;
  loKey: string;
  hiKey: string;
  color: string;
  unit: string;
  domain: [number | string, number | string];
}

const TARGETS: TargetConfig[] = [
  { key: "index", label: "Congestion index", loKey: "lo", hiKey: "hi", color: "var(--status-warning)", unit: "/100", domain: [0, 100] },
  { key: "queue", label: "Queue (vessels)", loKey: "queue_lo", hiKey: "queue_hi", color: "var(--accent)", unit: " vessels", domain: [0, "auto"] },
  { key: "wait", label: "Avg wait (hours)", loKey: "wait_lo", hiKey: "wait_hi", color: "#60a5fa", unit: "h", domain: [0, "auto"] },
  { key: "yard", label: "Yard utilisation (%)", loKey: "yard_lo", hiKey: "yard_hi", color: "#a78bfa", unit: "%", domain: [0, 100] },
];

function confidenceColor(conf: number): string {
  if (conf >= 0.8) return "var(--status-success)";
  if (conf >= 0.6) return "var(--status-warning)";
  return "var(--status-critical)";
}

function TargetChart({ data, cfg }: { data: any[]; cfg: TargetConfig }) {
  const chart = data.map((p: any) => ({
    label: `+${p.hour}h`,
    [cfg.key]: p[cfg.key],
    band: [p[cfg.loKey] ?? 0, p[cfg.hiKey] ?? 0],
  }));

  return (
    <div className="h-[220px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chart} margin={{ top: 4, right: 12, bottom: 4, left: -8 }}>
          <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" />
          <XAxis dataKey="label" interval={11} tick={{ fill: "var(--text-muted)", fontSize: 10 }} />
          <YAxis domain={cfg.domain} tick={{ fill: "var(--text-muted)", fontSize: 10 }} />
          <Tooltip
            contentStyle={{
              background: "var(--bg-surface-elevated)",
              border: "1px solid var(--border-default)",
              color: "var(--text-primary)",
              borderRadius: 8,
              fontSize: 11,
            }}
            formatter={(v: any) => [`${Number(v).toFixed(1)}${cfg.unit}`, cfg.label]}
          />
          <Area dataKey="band" stroke="none" fill={cfg.color} fillOpacity={0.14} />
          <Line dataKey={cfg.key} stroke={cfg.color} dot={false} strokeWidth={2} name={cfg.label} />
          <ReferenceLine x="+1h" stroke="var(--text-muted)" strokeDasharray="4 4" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function Forecast() {
  const [zone, setZone] = useState("Z-PORT");
  const [activeTarget, setActiveTarget] = useState<TargetKey>("index");

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["forecast", zone],
    queryFn: () => api.forecast(zone),
    staleTime: 120_000,
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <SkeletonCard />
        <div className="grid lg:grid-cols-2 gap-4">
          <SkeletonCard />
          <SkeletonCard />
        </div>
        <SkeletonCard />
      </div>
    );
  }

  if (error || !data) {
    return <ErrorState title="Forecast unavailable" message={error instanceof Error ? error.message : "Failed to reach /api/forecast"} onRetry={() => refetch()} />;
  }

  const s = data.selected;
  const conf = s.model?.confidence ?? data.confidence ?? 0;
  const confByHorizon = s.validation?.confidence_by_horizon ?? s.confidence_by_horizon ?? {};

  return (
    <div className="space-y-4">
      {/* Zone selector + meta */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={zone}
          onChange={(e) => setZone(e.target.value)}
          aria-label="Select Forecast Zone"
          className="bg-[var(--bg-surface-elevated)] border border-[var(--border-default)] rounded-md px-3 py-1.5 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--brand)] cursor-pointer"
        >
          {ZONES.map((z) => (
            <option key={z} value={z}>{ZONE_LABELS[z] ?? z}</option>
          ))}
        </select>

        {/* Weather indicator */}
        <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border text-xs font-mono"
          style={{
            borderColor: data.weather_used ? "var(--status-success-border, var(--border-default))" : "var(--border-subtle)",
            background: data.weather_used ? "var(--status-success-bg, transparent)" : "transparent",
            color: data.weather_used ? "var(--status-success)" : "var(--text-muted)",
          }}>
          {data.weather_used ? <CloudLightning className="w-3.5 h-3.5 shrink-0" /> : <CloudSun className="w-3.5 h-3.5 shrink-0" />}
          weather_used: {String(data.weather_used)}
        </div>

        {/* Confidence */}
        <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border text-xs font-mono"
          style={{ borderColor: "var(--border-subtle)", color: confidenceColor(conf) }}>
          <Activity className="w-3.5 h-3.5 shrink-0" />
          confidence: {conf}
        </div>

        <span className="text-[10px] text-[var(--text-muted)] font-mono">LightGBM · 80% quantile bands</span>
      </div>

      {/* Summary row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Now", value: s.current?.index, unit: "/100", color: "var(--accent)" },
          { label: "72h peak", value: s.peak?.index, unit: ` @ +${s.peak?.hour}h`, color: "var(--status-warning)" },
          { label: "72h avg", value: s.avg_index, unit: "/100", color: "var(--text-secondary)" },
          { label: "Queue now", value: s.current?.queue, unit: " vessels", color: "var(--text-primary)" },
        ].map((m) => (
          <div key={m.label} className="p-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
            <div className="text-[10px] uppercase font-bold text-[var(--text-muted)] tracking-wider">{m.label}</div>
            <div className="font-mono font-bold text-lg mt-0.5" style={{ color: m.color }}>{m.value}<span className="text-xs font-normal text-[var(--text-muted)]">{m.unit}</span></div>
          </div>
        ))}
      </div>

      {/* Horizon confidence */}
      {Object.keys(confByHorizon).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(confByHorizon).map(([bucket, val]) => (
            <div key={bucket} className="px-2.5 py-1 rounded-md border text-xs font-mono flex items-center gap-1.5"
              style={{ borderColor: "var(--border-subtle)", color: confidenceColor(val as number) }}>
              <TrendingUp className="w-3 h-3" />
              {bucket}: {String(val)}
            </div>
          ))}
        </div>
      )}

      {/* Target selector tabs */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {TARGETS.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTarget(t.key)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer border ${
              activeTarget === t.key
                ? "text-white font-bold shadow-xs"
                : "border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
            style={activeTarget === t.key ? { background: t.color, borderColor: t.color } : {}}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Main chart */}
      <div className="p-4 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
        <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1 mb-3">
          <h3 className="font-semibold text-sm">{s.zone_name} — 72h {TARGETS.find((t) => t.key === activeTarget)?.label}</h3>
          <div className="text-xs text-[var(--text-muted)] font-mono">
            shaded area = 80% prediction interval
          </div>
        </div>
        <TargetChart data={s.points} cfg={TARGETS.find((t) => t.key === activeTarget)!} />
      </div>

      {/* Drivers */}
      {s.drivers?.length > 0 && (
        <div className="p-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface-elevated)]">
          <div className="text-xs font-semibold text-[var(--text-secondary)] mb-2">Congestion drivers</div>
          <div className="flex flex-wrap gap-2">
            {s.drivers.map((d: any) => (
              <div key={d.label} className="px-2.5 py-1.5 rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] text-xs" title={d.detail}>
                <span className="font-semibold">{d.label}</span>
                {d.detail && <span className="text-[var(--text-muted)] ml-1 hidden sm:inline">— {d.detail}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tier 3 — model internals deferred: MAE/R²/coverage stay real and one click away,
          but they don't compete with the forecast itself for attention. */}
      <Collapsible
        summary="Model details & accuracy"
        badge={
          <span className="text-[10px] font-mono text-[var(--text-muted)]">
            MAE ≤72h {s.model?.mae72 ?? "—"} · R² {s.model?.r2 ?? "—"}
          </span>
        }
      >
        <div className="grid lg:grid-cols-2 gap-4">
          <div className="p-4 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
            <h3 className="font-semibold text-sm mb-3">Model card</h3>
            <table className="w-full text-xs"><tbody>
              {[
                ["Algorithm", s.model?.algorithm],
                ["Model version", <code className="font-mono text-[10px]">{s.model?.model_version}</code>],
                ["Training rows", s.model?.training_rows],
                ["Holdout", `${s.model?.holdout_hours}h`],
                ["MAE ≤24h / ≤72h", `${s.model?.mae24} / ${s.model?.mae72}`],
                ["R² / skill vs persistence", `${s.model?.r2} / ${s.model?.skill_pct}%`],
                ["Band coverage (80% target)", s.model?.calibration?.coverage_80 != null
                  ? `${Math.round(s.model.calibration.coverage_80 * 100)}% over ${s.model.calibration.origins} origins` : "—"],
              ].map(([k, v]) => (
                <tr key={k as string} className="border-t border-[var(--border-subtle)]">
                  <td className="py-1 pr-3 text-[var(--text-muted)]">{k}</td>
                  <td className="font-mono">{v}</td>
                </tr>
              ))}
            </tbody></table>
            <div className="text-[10px] text-[var(--text-muted)] mt-2">
              Top features: {s.model?.top_features?.map((f: any) => `${f.feature} (${f.gain})`).join(", ")}
            </div>
          </div>

          <div className="p-4 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
            <h3 className="font-semibold text-sm mb-3">Per-horizon validation (multi-origin residuals)</h3>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[320px] text-xs">
                <thead>
                  <tr className="text-[10px] text-[var(--text-muted)] uppercase">
                    <th className="text-left py-1 pr-3">Horizon</th>
                    <th className="text-right pr-3">MAE</th>
                    <th className="text-right pr-3">σ</th>
                    <th className="text-right pr-3">Bias</th>
                    <th className="text-right">n</th>
                  </tr>
                </thead>
                <tbody>
                  {s.validation?.buckets?.map((b: any) => (
                    <tr key={b.label} className="border-t border-[var(--border-subtle)]">
                      <td className="py-1 pr-3 font-semibold">{b.label}</td>
                      <td className="text-right pr-3 font-mono">{b.mae}</td>
                      <td className="text-right pr-3 font-mono">{b.sigma}</td>
                      <td className="text-right pr-3 font-mono">{b.bias}</td>
                      <td className="text-right text-[var(--text-muted)]">{b.n}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </Collapsible>

      {/* Bottleneck attribution stays visible — it is decision-relevant, not model internals. */}
      <div className="p-4 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
        <h3 className="font-semibold text-sm mb-3">Bottleneck attribution</h3>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[360px] text-xs">
            <thead>
              <tr className="text-[10px] text-[var(--text-muted)] uppercase">
                <th className="text-left py-1 pr-2">Zone</th>
                <th className="text-right pr-2">Risk</th>
                <th className="text-left pr-2">Binding</th>
                <th className="text-right pr-2">Conf</th>
              </tr>
            </thead>
            <tbody>
              {data.hotspots?.ranked?.map((r: any) => (
                <tr key={r.zone_code} className="border-t border-[var(--border-subtle)]">
                  <td className="py-1 pr-2 font-mono">{r.zone_code}</td>
                  <td className="text-right pr-2 font-mono" style={{ color: confidenceColor(r.risk_score / 100) }}>{r.risk_score}</td>
                  <td className="pr-2 font-semibold" style={{ color: "var(--accent)" }}>{r.binding_constraint}</td>
                  <td className="text-right text-[var(--text-muted)]">{r.confidence}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
