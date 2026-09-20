// Berth & Cranes tab — CP-SAT BAP/QCAP with tidal windows, incremental re-solve,
// scenario-compare table (CP-SAT vs FIFO side-by-side), and binding constraint column.
//
// Visual-density pass: tier 1 = headline delta + solver honesty chips, tier 2 = four
// compact KPIs + the Gantt (the deliverable), tier 3 = full comparison table,
// per-vessel assignments, deferred list and terminal capacity — one tab click away.
import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Waves, Zap, RotateCcw, Play, BarChart2 } from "lucide-react";
import { api } from "../lib/api";
import { SkeletonCard } from "../components/ui/Skeleton";
import { ErrorState } from "../components/ui/ErrorState";
import { Tabs, TabsList, TabTrigger, TabContent } from "../components/ui/Tabs";

function fmtDelta(val: number | undefined | null, unit = ""): React.ReactNode {
  if (val == null) return <span className="text-[var(--text-muted)]">—</span>;
  const sign = val > 0 ? "+" : "";
  const color = val < 0 ? "var(--status-success)" : val > 0 ? "var(--status-critical)" : "var(--text-muted)";
  return <span className="font-mono font-semibold" style={{ color }}>{sign}{val}{unit}</span>;
}

// Backend deltas use base−optimised (positive = CP-SAT improved over FIFO),
// unlike the ScenarioCompare table below which computes cpsat−fifo itself.
// audit-fix: colors were inverted, painting a 63.8h WAIT INCREASE green.
function DeltaTag({ val }: { val: number | undefined }) {
  if (val == null) return null;
  const color = val > 0 ? "var(--status-success)" : val < 0 ? "var(--status-critical)" : "var(--text-muted)";
  const sign = val > 0 ? "+" : "";
  return <span className="font-mono text-[10px]" style={{ color }}>{sign}{val}</span>;
}

function KpiCard({ label, value, sub }: { label: string; value: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <div className="p-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
      <div className="text-[10px] uppercase font-bold text-[var(--text-muted)] tracking-wider">{label}</div>
      <div className="font-mono font-bold text-lg text-[var(--text-primary)] mt-0.5">{value}</div>
      {sub && <div className="text-[10px] text-[var(--text-muted)] mt-0.5">{sub}</div>}
    </div>
  );
}

// ── Scenario compare table ────────────────────────────────────────────────────
function ScenarioCompare({ opt }: { opt: any }) {
  if (!opt?.metrics || !opt?.baseline) return null;
  const m = opt.metrics;
  const b = opt.baseline;

  const rows = [
    { label: "Vessels serviced",    cpsat: m.serviced,           fifo: b.serviced,           unit: "",    lowerBetter: false },
    { label: "Deferred",            cpsat: m.deferred,           fifo: b.deferred,           unit: "",    lowerBetter: true  },
    { label: "Total wait (h)",      cpsat: m.total_wait_hours,   fifo: b.total_wait_hours,   unit: "h",   lowerBetter: true  },
    { label: "Avg wait (h)",        cpsat: m.avg_wait_hours,     fifo: b.avg_wait_hours,     unit: "h",   lowerBetter: true  },
    { label: "Max wait (h)",        cpsat: m.max_wait_hours,     fifo: b.max_wait_hours,     unit: "h",   lowerBetter: true  },
    { label: "Weighted wait (h)",   cpsat: m.weighted_wait_hours,fifo: b.weighted_wait_hours,unit: "h",   lowerBetter: true  },
    { label: "Makespan (h)",        cpsat: m.makespan_hours,     fifo: b.makespan_hours,     unit: "h",   lowerBetter: true  },
    { label: "Berth util (%)",      cpsat: m.berth_util_pct,     fifo: b.berth_util_pct,     unit: "%",   lowerBetter: false },
    { label: "Crane util (%)",      cpsat: m.crane_util_pct,     fifo: b.crane_util_pct,     unit: "%",   lowerBetter: false },
    { label: "Moves served",        cpsat: m.total_moves,        fifo: b.total_moves,        unit: "",    lowerBetter: false },
    { label: "Avg cranes/vessel",   cpsat: m.avg_cranes_per_vessel, fifo: b.avg_cranes_per_vessel, unit: "", lowerBetter: false },
  ];

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[480px] text-xs">
          <thead>
            <tr className="text-[10px] text-[var(--text-muted)] uppercase border-b border-[var(--border-default)]">
              <th className="text-left py-1.5 pr-4 font-bold">Metric</th>
              <th className="text-right pr-4 font-bold">CP-SAT</th>
              <th className="text-right pr-4 font-bold">FIFO</th>
              <th className="text-right font-bold">Δ</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ label, cpsat, fifo, unit, lowerBetter }) => {
              const delta = cpsat != null && fifo != null
                ? Math.round((cpsat - fifo) * 10) / 10
                : null;
              const improved = delta != null && (lowerBetter ? delta < 0 : delta > 0);
              const worse    = delta != null && (lowerBetter ? delta > 0 : delta < 0);
              return (
                <tr key={label} className="border-t border-[var(--border-subtle)]">
                  <td className="py-1 pr-4 text-[var(--text-secondary)]">{label}</td>
                  <td className="text-right pr-4 font-mono font-semibold"
                    style={{ color: improved ? "var(--status-success)" : worse ? "var(--status-critical)" : "var(--text-primary)" }}>
                    {cpsat != null ? `${cpsat}${unit}` : "—"}
                  </td>
                  <td className="text-right pr-4 font-mono text-[var(--text-muted)]">
                    {fifo != null ? `${fifo}${unit}` : "—"}
                  </td>
                  <td className="text-right font-mono">
                    {fmtDelta(delta, unit)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-[10px] text-[var(--text-muted)] mt-2">
        Green Δ = CP-SAT improvement over FIFO. Objective weights: {Object.entries(opt.weights || {}).map(([k, v]) => `${k}=${v}`).join(" · ")}
      </p>
    </div>
  );
}

const MAX_HOUR = 96;

export default function BerthCranes() {
  const qc = useQueryClient();
  const [crane, setCrane] = useState(1.0);
  const [rate, setRate] = useState(28);
  const [useTidal, setUseTidal] = useState(true);
  const [useIncremental, setUseIncremental] = useState(false);
  const [scenarioRun, setScenarioRun] = useState<any>(null);
  const [detailTab, setDetailTab] = useState("compare");

  const { data: terms } = useQuery({ queryKey: ["terminals"], queryFn: () => api.terminals(), staleTime: 300_000 });
  const { data: latest, isLoading } = useQuery({ queryKey: ["optimise-latest"], queryFn: () => api.optimiseLatest(), staleTime: 120_000 });
  const { data: tides } = useQuery({ queryKey: ["tides"], queryFn: () => api.tides(), staleTime: 3_600_000 });

  const opt = scenarioRun ?? latest;

  const solveMutation = useMutation({
    mutationFn: () => api.optimise({
      crane_factor: crane,
      move_rate_per_crane_hour: rate,
      incremental: useIncremental,
      tidal: useTidal,
    }),
    onSuccess: (data) => {
      setScenarioRun(data);
      qc.invalidateQueries({ queryKey: ["optimise-latest"] });
    },
  });

  // Headline (tier 1): total-wait delta vs FIFO. Backend deltas = base − optimised,
  // so positive means CP-SAT saved wait. Falls back to metrics when deltas absent.
  const waitSaved = opt?.deltas?.wait_total
    ?? (opt?.metrics && opt?.baseline ? Math.round((opt.baseline.total_wait_hours - opt.metrics.total_wait_hours) * 10) / 10 : null);
  const saved = waitSaved != null;

  return (
    <div className="space-y-4">
      {/* Controls panel */}
      <div className="p-4 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
        <div className="flex flex-wrap items-end gap-5">
          {/* Crane slider */}
          <div className="w-full xs:w-auto">
            <div className="text-xs text-[var(--text-muted)] mb-1">
              Crane availability: <b className="text-[var(--accent)] font-mono">{Math.round(crane * 100)}%</b>
            </div>
            <input type="range" min={0.5} max={1} step={0.05} value={crane}
              onChange={(e) => setCrane(+e.target.value)}
              className="w-full xs:w-52 cursor-pointer accent-[var(--brand)]" />
          </div>

          {/* Rate slider */}
          <div className="w-full xs:w-auto">
            <div className="text-xs text-[var(--text-muted)] mb-1">
              STS productivity: <b className="text-[var(--accent)] font-mono">{rate} moves/crane·h</b>
            </div>
            <input type="range" min={20} max={35} step={1} value={rate}
              onChange={(e) => setRate(+e.target.value)}
              className="w-full xs:w-52 cursor-pointer accent-[var(--brand)]" />
          </div>

          {/* Toggles */}
          <div className="flex items-center gap-3 flex-wrap">
            <label className="flex items-center gap-1.5 cursor-pointer text-xs select-none">
              <input type="checkbox" checked={useTidal} onChange={(e) => setUseTidal(e.target.checked)}
                className="accent-[var(--brand)] cursor-pointer" />
              <Waves className="w-3.5 h-3.5 text-[var(--brand)]" />
              Tidal windows
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer text-xs select-none">
              <input type="checkbox" checked={useIncremental} onChange={(e) => setUseIncremental(e.target.checked)}
                className="accent-[var(--brand)] cursor-pointer" />
              <Zap className="w-3.5 h-3.5 text-[var(--accent)]" />
              Incremental (warm-start)
            </label>
          </div>

          {/* Buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => solveMutation.mutate()}
              disabled={solveMutation.isPending}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-xs font-semibold bg-[var(--brand)] hover:bg-[var(--brand-hover)] text-white shadow-xs transition-colors cursor-pointer disabled:opacity-50"
            >
              <Play className="w-3 h-3" />
              {solveMutation.isPending ? "Solving CP-SAT…" : "Run scenario"}
            </button>
            {scenarioRun && (
              <button
                onClick={() => setScenarioRun(null)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium border border-[var(--border-default)] hover:border-[var(--border-elevated)] cursor-pointer transition-colors"
              >
                <RotateCcw className="w-3 h-3" />
                Reset
              </button>
            )}
          </div>

          {opt && (
            <div className="text-[10px] font-mono text-[var(--text-muted)] w-full sm:w-auto">
              <span className="text-[var(--accent)] font-semibold">{opt.solver}</span> · {opt.status} · {opt.solve_ms}ms
              {opt.gap_pct != null && <> · gap: <span className={`font-semibold ${opt.status === "OPTIMAL" || opt.gap_pct <= 10 ? "text-[var(--status-success)]" : "text-[var(--status-warning)]"}`}>{opt.gap_pct}%</span>{opt.status !== "OPTIMAL" && <span className="text-[var(--text-muted)]"> (time-limited)</span>}</>}
              {opt.tidal_feasible != null && <> · tidal_feasible: <span className={opt.tidal_feasible ? "text-[var(--status-success)]" : "text-[var(--status-critical)]"}>{String(opt.tidal_feasible)}</span></>}
              {opt.incremental && <> · <span className="text-[var(--accent)]">incremental</span></>}
            </div>
          )}
        </div>
      </div>

      {isLoading && <SkeletonCard />}

      {solveMutation.isError && (
        <div className="p-3 rounded-lg border border-[var(--status-critical)] bg-[var(--status-critical-bg)] text-xs text-[var(--status-critical)]">
          CP-SAT solve failed: {String((solveMutation.error as Error)?.message ?? solveMutation.error)}
        </div>
      )}

      {opt && (
        <>
          {/* Tier 1 — headline metric: wait delta vs FIFO, same snapshot */}
          <div className="p-4 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] flex flex-wrap items-center gap-x-8 gap-y-3">
            <div>
              <div className="text-[10px] uppercase font-bold text-[var(--text-muted)] tracking-wider">Total wait vs FIFO baseline</div>
              <div className="font-mono font-bold text-3xl mt-0.5"
                style={{ color: !saved ? "var(--text-muted)" : waitSaved > 0 ? "var(--status-success)" : waitSaved < 0 ? "var(--status-critical)" : "var(--text-primary)" }}>
                {saved ? (waitSaved > 0 ? `−${waitSaved}h` : `+${Math.abs(waitSaved)}h`) : "—"}
                {!saved && <span className="text-sm font-normal">no delta reported</span>}
              </div>
              <div className="text-xs text-[var(--text-secondary)] mt-0.5">
                {saved
                  ? waitSaved > 0 ? "less total anchorage wait than the FIFO plan" : waitSaved < 0 ? "more total anchorage wait than the FIFO plan" : "no wait change vs FIFO"
                  : "run a solve to compare against FIFO"}
              </div>
            </div>
            <div className="text-xs text-[var(--text-secondary)] space-y-0.5">
              <div><b className="font-mono">{opt.metrics?.serviced}</b> vessels serviced <span className="text-[var(--text-muted)]">(FIFO {opt.baseline?.serviced})</span></div>
              <div><b className="font-mono" style={{ color: "var(--status-warning)" }}>{opt.metrics?.deferred}</b> deferred <span className="text-[var(--text-muted)]">— reasons in Assignments tab</span></div>
            </div>
          </div>

          {/* Tier 2 — four compact KPIs */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <KpiCard label="Berth util" value={`${opt.metrics?.berth_util_pct}%`} sub={`FIFO ${opt.baseline?.berth_util_pct}%`} />
            <KpiCard label="Crane util" value={`${opt.metrics?.crane_util_pct}%`} sub={`FIFO ${opt.baseline?.crane_util_pct}%`} />
            <KpiCard label="Makespan" value={`${opt.metrics?.makespan_hours}h`} sub={`FIFO ${opt.baseline?.makespan_hours}h`} />
            <KpiCard label="Avg cranes/vessel" value={opt.metrics?.avg_cranes_per_vessel} sub={`FIFO ${opt.baseline?.avg_cranes_per_vessel}`} />
          </div>

          {/* Tier 1 supporting chart — the assignment Gantt stays always visible */}
          <div className="p-4 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
            <div className="flex items-start justify-between flex-wrap gap-2 mb-3">
              <h3 className="font-semibold text-sm">72h Berth Gantt — CP-SAT assignments</h3>
              <div className="text-[10px] font-mono text-[var(--text-muted)]">
                objective weights: {Object.entries(opt.weights || {}).map(([k, v]) => `${k}=${v}`).join(" · ")}
              </div>
            </div>
            <div className="overflow-x-auto">
              <div style={{ minWidth: 900 }}>
                {/* Hour ticks */}
                <div className="flex items-center mb-1" style={{ marginLeft: 116 }}>
                  {[0, 12, 24, 36, 48, 60, 72].map((h) => (
                    <div key={h} className="text-[9px] font-mono text-[var(--text-muted)]"
                      style={{ position: "relative", left: `${(h / MAX_HOUR) * 100}%`, width: 0 }}>
                      {h > 0 ? `+${h}h` : "now"}
                    </div>
                  ))}
                </div>

                {Object.entries(
                  (opt.assignments || []).reduce((acc: any, a: any) => {
                    const key = `${a.terminal_code ?? ""} ${a.berth_name}`.trim();
                    (acc[key] ||= []).push(a);
                    return acc;
                  }, {})
                ).sort().map(([berth, list]: any) => {
                  const tideCurve = tides?.berths?.find((b: any) => b.berth_name === list[0]?.berth_name)?.curve ?? [];

                  return (
                    <div key={berth} className="flex items-center gap-2 py-0.5">
                      <div className="font-mono text-[10px] text-[var(--text-secondary)] shrink-0 truncate" style={{ width: 110 }}>{berth}</div>
                      <div className="relative flex-1" style={{ height: 26, background: "var(--bg-surface-elevated)", border: "1px solid var(--border-subtle)", borderRadius: 6 }}>
                        {tideCurve.slice(0, MAX_HOUR).map((pt: any, hi: number) => {
                          if (pt.depth_ft >= (list[0]?.design_depth_ft ?? 52)) return null;
                          return (
                            <div key={hi}
                              className="absolute top-0 h-full pointer-events-none"
                              style={{
                                left: `${(hi / MAX_HOUR) * 100}%`,
                                width: `${(1 / MAX_HOUR) * 100}%`,
                                background: "rgba(96, 165, 250, 0.08)",
                                borderLeft: "1px solid rgba(96, 165, 250, 0.12)",
                              }}
                              title={`Depth ${pt.depth_ft.toFixed(1)} ft at +${hi}h`}
                            />
                          );
                        })}
                        {list.map((a: any, i: number) => (
                          <div key={`${a.vessel_id ?? a.vessel_name}-${a.start_hour}-${a.end_hour}-${i}`}
                            title={`${a.vessel_name} · +${a.start_hour}→${a.end_hour}h · ${a.cranes} cranes · wait ${a.wait_hours}h · priority ${a.priority_score}`}
                            className="absolute top-0 h-full text-[9px] flex items-center justify-center font-semibold overflow-hidden select-none"
                            style={{
                              left: `${(a.start_hour / MAX_HOUR) * 100}%`,
                              width: `${Math.max(1.2, ((a.end_hour - a.start_hour) / MAX_HOUR) * 100)}%`,
                              background: "var(--brand-soft)",
                              border: "1px solid var(--brand-border)",
                              borderRadius: 4,
                              color: "var(--text-primary)",
                            }}>
                            {a.vessel_name?.replace("M/V ", "")} ×{a.cranes}
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}

                {tides && (
                  <div className="flex items-center gap-2 mt-2 text-[9px] text-[var(--text-muted)]">
                    <span style={{ display: "inline-block", width: 12, height: 10, background: "rgba(96, 165, 250, 0.15)", border: "1px solid rgba(96, 165, 250, 0.3)", borderRadius: 2 }} />
                    Low-water (depth below design) · amplitude ±{tides.amplitude_ft} ft · period {tides.period_hours}h
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Tier 3 — full detail, one tab away: comparison table, assignments +
              deferred reasons, terminal capacity. Same data, deferred rendering. */}
          <Tabs value={detailTab} onValueChange={setDetailTab}>
            <TabsList>
              <TabTrigger value="compare" badge={<BarChart2 className="w-3 h-3" />}>CP-SAT vs FIFO</TabTrigger>
              <TabTrigger value="assignments">Assignments ({opt.assignments?.length ?? 0})</TabTrigger>
              <TabTrigger value="terminals">Terminals</TabTrigger>
            </TabsList>

            <TabContent value="compare">
              <div className="p-4 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
                <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
                  <BarChart2 className="w-4 h-4 text-[var(--brand)]" />
                  Scenario comparison — CP-SAT vs FIFO baseline
                </h3>
                <ScenarioCompare opt={opt} />
              </div>
            </TabContent>

            <TabContent value="assignments">
              <div className="p-4 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
                <h3 className="font-semibold text-sm mb-3">
                  Assignments ({opt.assignments?.length}) · deferred ({opt.deferred?.length})
                </h3>
                <div className="overflow-x-auto max-h-80">
                  <table className="w-full min-w-[640px] text-xs">
                    <thead>
                      <tr className="text-[10px] text-[var(--text-muted)] uppercase">
                        <th className="text-left py-1 pr-2">Vessel</th>
                        <th className="text-left pr-2">Berth</th>
                        <th className="text-left pr-2">Terminal</th>
                        <th className="text-right pr-2">Start</th>
                        <th className="text-right pr-2">End</th>
                        <th className="text-right pr-2">Cranes</th>
                        <th className="text-right pr-2">Wait</th>
                        <th className="text-right">Priority</th>
                      </tr>
                    </thead>
                    <tbody>
                      {opt.assignments?.map((a: any, i: number) => (
                        <tr key={`${a.vessel_id ?? a.vessel_name}-${a.start_hour}-${a.end_hour}-${a.berth_name}-${i}`} className="border-t border-[var(--border-subtle)]">
                          <td className="py-1 pr-2 font-medium">{a.vessel_name}</td>
                          <td className="pr-2 font-mono">{a.berth_name}</td>
                          <td className="pr-2 text-[var(--text-secondary)]">{a.terminal_code}</td>
                          <td className="text-right pr-2 font-mono">+{a.start_hour}h</td>
                          <td className="text-right pr-2 font-mono">+{a.end_hour}h</td>
                          <td className="text-right pr-2 font-mono">{a.cranes}</td>
                          <td className="text-right pr-2 font-mono text-[var(--text-muted)]">{a.wait_hours}h</td>
                          <td className="text-right font-mono text-[var(--text-muted)]">{a.priority_score != null ? Number(a.priority_score).toFixed(1) : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {!!opt.deferred?.length && (
                  <div className="mt-2 space-y-0.5">
                    <div className="text-xs font-semibold text-[var(--status-warning)]">Deferred vessels:</div>
                    {opt.deferred.map((d: any, i: number) => (
                      <div key={`${d.vessel_id ?? d.vessel_name}-${i}`} className="text-[10px] font-mono text-[var(--text-muted)]">
                        {d.vessel_name} — {d.reason ?? "beyond 72h horizon"}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </TabContent>

            <TabContent value="terminals">
              {terms ? (
                <div className="p-4 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
                  <h3 className="font-semibold text-sm mb-3">Terminals — real POLB capacity + live yard &amp; crane state</h3>
                  <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3">
                    {terms.terminals?.map((t: any) => (
                      <div key={t.code} className="p-3 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-elevated)]">
                        <div className="font-semibold text-sm">{t.code} <span className="text-[var(--text-muted)] font-normal text-xs">· {t.pier}</span></div>
                        <div className="text-[10px] text-[var(--text-muted)] mb-2 truncate">{t.name}</div>
                        <div className="text-xs">{t.deepsea_berths} berths · {t.gantry_cranes} STS · {Number(t.berth_length_ft).toLocaleString()} ft{t.capacity_teu_m ? ` · ${t.capacity_teu_m}M TEU` : ""}</div>
                        <div className="text-xs mt-1">
                          cranes: <span className="font-semibold" style={{ color: "var(--accent)" }}>
                            {t.cranes?.filter((c: any) => c.status === "AVAILABLE").length} avail
                          </span>
                          {t.cranes?.some((c: any) => c.status !== "AVAILABLE") && (
                            <span className="text-[var(--text-muted)]"> · {t.cranes?.filter((c: any) => c.status !== "AVAILABLE").length} maint.</span>
                          )}
                        </div>
                        <div className="text-[10px] text-[var(--text-muted)] mt-0.5">
                          yard: {t.yard_zones?.map((y: any) => `${y.code}:${y.util_pct}%`).join(" ")}
                        </div>
                        <div className="text-[10px] text-[var(--text-muted)]">gate {t.gate?.lanes} lanes · q {t.gate?.queue_len}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <SkeletonCard />
              )}
            </TabContent>
          </Tabs>
        </>
      )}
    </div>
  );
}
