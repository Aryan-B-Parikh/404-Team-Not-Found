// 72-Hour Plan tab — confidence by horizon bucket, colour-coded risk, export
import { useQuery } from "@tanstack/react-query";
import { Download, AlertTriangle, CheckCircle2, Clock } from "lucide-react";
import { api } from "../lib/api";
import { SkeletonCard } from "../components/ui/Skeleton";
import { ErrorState } from "../components/ui/ErrorState";
import { Collapsible } from "../components/ui/Collapsible";

function riskColor(level: string): string {
  if (level === "SEVERE") return "var(--status-critical)";
  if (level === "HIGH") return "var(--status-warning)";
  if (level === "ELEVATED") return "#fbbf24";
  return "var(--status-success)";
}

function confColor(val: number): string {
  if (val >= 0.8) return "var(--status-success)";
  if (val >= 0.6) return "var(--status-warning)";
  return "var(--status-critical)";
}

function ConfBadge({ bucket, val }: { bucket: string; val: number }) {
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded border font-mono text-[9px]"
      style={{ color: confColor(val), borderColor: confColor(val), background: `${confColor(val)}18` }}>
      {bucket}: {val}
    </span>
  );
}

export default function Plan() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["plan"],
    queryFn: () => api.plan(),
    staleTime: 120_000,
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">{[0,1,2,3,4,5].map((i) => <SkeletonCard key={i} />)}</div>
        <SkeletonCard />
        <div className="grid lg:grid-cols-2 gap-3">{[0,1,2,3].map((i) => <SkeletonCard key={i} />)}</div>
      </div>
    );
  }

  if (error || !data) {
    return <ErrorState title="72h plan unavailable" message={error instanceof Error ? error.message : "Could not reach /api/plan"} onRetry={() => refetch()} />;
  }

  const s = data.summary;
  const conf = s.confidence_by_bucket ?? {};

  return (
    <div className="space-y-4">
      {/* Spec §6 traceability: every number traces to the snapshot that produced it. */}
      <div className="text-[10px] font-mono text-[var(--text-muted)]">
        {data.plan_id != null
          ? `Plan #${data.plan_id} · generated ${data.created_at ?? "—"} · from forecast run ${data.forecast_run_id ?? "—"} + optimiser run ${data.optimiser_run_id ?? "—"}`
          : `Live build · from forecast run ${data.forecast_run_id ?? "—"} + optimiser run ${data.optimiser_run_id ?? "—"}`}
      </div>
      {/* KPI strip */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
        <div className="p-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
          <div className="text-[10px] uppercase font-bold text-[var(--text-muted)] tracking-wider flex items-center gap-1.5">
            <AlertTriangle className="w-3 h-3" /> Risk
          </div>
          <div className="font-mono font-bold text-lg mt-0.5" style={{ color: riskColor(s.risk_level) }}>{s.risk_level}</div>
        </div>
        {[
          { label: "Arrivals", value: s.total_arrivals },
          { label: "Berthings", value: s.total_berthings },
          { label: "Moves", value: Number(s.total_moves).toLocaleString() },
          { label: "Crane-hours", value: Number(s.crane_hours).toLocaleString() },
          { label: "Deferred", value: s.deferred_count, bad: s.deferred_count > 0 },
        ].map((m) => (
          <div key={m.label} className="p-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
            <div className="text-[10px] uppercase font-bold text-[var(--text-muted)] tracking-wider">{m.label}</div>
            <div className="font-mono font-bold text-lg mt-0.5" style={m.bad ? { color: "var(--status-warning)" } : {}}>{m.value}</div>
          </div>
        ))}
      </div>

      {/* Top actions + confidence badges */}
      <div className="p-4 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <h3 className="font-semibold text-sm">Top actions</h3>
          <div className="flex flex-wrap items-center gap-2">
            {Object.entries(conf).map(([bucket, val]) => (
              <ConfBadge key={bucket} bucket={bucket} val={val as number} />
            ))}
            <a
              href={api.exportUrl("assignments")}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border border-[var(--border-default)] hover:border-[var(--brand)] transition-colors"
            >
              <Download className="w-3 h-3" />
              Export CSV
            </a>
          </div>
        </div>
        <ol className="list-decimal ml-5 text-sm space-y-1.5">
          {s.top_actions?.map((a: string, i: number) => (
            <li key={i} className="text-[var(--text-secondary)]">{a}</li>
          ))}
        </ol>
      </div>

      {/* 12 shift cards — density pass: the immediate window (next two shifts) is
          visible; the remaining ten are one click away. Nothing is removed. */}
      <div className="grid lg:grid-cols-2 gap-3">
        {data.shifts?.slice(0, 2).map((sh: any) => (
          <div key={sh.seq} className="p-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
            <div className="flex items-center justify-between">
              <div className="font-semibold text-sm">{sh.label}</div>
              <span className="text-[10px] font-mono text-[var(--text-muted)]">{sh.window_label}</span>
            </div>

            {/* Arrivals */}
            <div className="text-xs mt-2 flex items-start gap-1.5">
              <Clock className="w-3 h-3 text-[var(--text-muted)] mt-0.5 shrink-0" />
              <span>
                <b className="text-[var(--text-secondary)]">Arrivals:</b>{" "}
                {sh.arrivals?.length
                  ? sh.arrivals.map((a: any) => `${a.vessel_name?.replace("M/V ", "")}@+${a.eta_hour}h`).join(", ")
                  : <span className="text-[var(--text-muted)]">none</span>}
              </span>
            </div>

            {/* Berthings */}
            {sh.berthings?.length > 0 && (
              <div className="text-xs mt-1 flex items-start gap-1.5">
                <CheckCircle2 className="w-3 h-3 text-[var(--status-success)] mt-0.5 shrink-0" />
                <span>
                  <b className="text-[var(--text-secondary)]">Berthings:</b>{" "}
                  {sh.berthings.map((b: any) => `${b.vessel_name?.replace("M/V ", "")}→${b.berth_name} (${b.cranes}c)`).join(", ")}
                </span>
              </div>
            )}

            {/* Congestion alerts */}
            {sh.congestion_alerts?.length > 0 && (
              <div className="text-xs mt-1 flex items-start gap-1.5">
                <AlertTriangle className="w-3 h-3 text-[var(--status-warning)] mt-0.5 shrink-0" />
                <span>
                  <b className="text-[var(--status-warning)]">Alerts:</b>{" "}
                  {sh.congestion_alerts.map((a: any) => `${a.level} ${a.zone_code} ${a.peak_index}@+${a.peak_hour}h`).join(" · ")}
                </span>
              </div>
            )}

            {/* Routing actions */}
            {sh.routing_actions?.length > 0 && (
              <div className="text-xs mt-1 text-[var(--brand)]">
                <b>Routing:</b> {sh.routing_actions.join(" ")}
              </div>
            )}

            {/* Checklist */}
            <ul className="mt-2 space-y-0.5">
              {sh.checklist?.map((c: string, i: number) => (
                <li key={i} className="text-[10px] text-[var(--text-muted)] flex items-center gap-1.5">
                  <span className="w-1 h-1 rounded-full bg-[var(--border-default)] shrink-0" />
                  {c}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {(data.shifts?.length ?? 0) > 2 && (
        <Collapsible
          summary={`Remaining shifts (${(data.shifts?.length ?? 0) - 2} of ${data.shifts?.length})`}
          badge={<span className="text-[10px] font-mono text-[var(--text-muted)]">+{data.shifts?.slice(2).reduce((n: number, sh: any) => n + (sh.arrivals?.length ?? 0) + (sh.berthings?.length ?? 0), 0)} planned movements</span>}
        >
          <div className="grid lg:grid-cols-2 gap-3">
            {data.shifts?.slice(2).map((sh: any) => (
              <div key={sh.seq} className="p-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-sm">{sh.label}</div>
                  <span className="text-[10px] font-mono text-[var(--text-muted)]">{sh.window_label}</span>
                </div>

                {/* Arrivals */}
                <div className="text-xs mt-2 flex items-start gap-1.5">
                  <Clock className="w-3 h-3 text-[var(--text-muted)] mt-0.5 shrink-0" />
                  <span>
                    <b className="text-[var(--text-secondary)]">Arrivals:</b>{" "}
                    {sh.arrivals?.length
                      ? sh.arrivals.map((a: any) => `${a.vessel_name?.replace("M/V ", "")}@+${a.eta_hour}h`).join(", ")
                      : <span className="text-[var(--text-muted)]">none</span>}
                  </span>
                </div>

                {/* Berthings */}
                {sh.berthings?.length > 0 && (
                  <div className="text-xs mt-1 flex items-start gap-1.5">
                    <CheckCircle2 className="w-3 h-3 text-[var(--status-success)] mt-0.5 shrink-0" />
                    <span>
                      <b className="text-[var(--text-secondary)]">Berthings:</b>{" "}
                      {sh.berthings.map((b: any) => `${b.vessel_name?.replace("M/V ", "")}→${b.berth_name} (${b.cranes}c)`).join(", ")}
                    </span>
                  </div>
                )}

                {/* Congestion alerts */}
                {sh.congestion_alerts?.length > 0 && (
                  <div className="text-xs mt-1 flex items-start gap-1.5">
                    <AlertTriangle className="w-3 h-3 text-[var(--status-warning)] mt-0.5 shrink-0" />
                    <span>
                      <b className="text-[var(--status-warning)]">Alerts:</b>{" "}
                      {sh.congestion_alerts.map((a: any) => `${a.level} ${a.zone_code} ${a.peak_index}@+${a.peak_hour}h`).join(" · ")}
                    </span>
                  </div>
                )}

                {/* Routing actions */}
                {sh.routing_actions?.length > 0 && (
                  <div className="text-xs mt-1 text-[var(--brand)]">
                    <b>Routing:</b> {sh.routing_actions.join(" ")}
                  </div>
                )}

                {/* Checklist */}
                <ul className="mt-2 space-y-0.5">
                  {sh.checklist?.map((c: string, i: number) => (
                    <li key={i} className="text-[10px] text-[var(--text-muted)] flex items-center gap-1.5">
                      <span className="w-1 h-1 rounded-full bg-[var(--border-default)] shrink-0" />
                      {c}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Collapsible>
      )}
    </div>
  );
}
