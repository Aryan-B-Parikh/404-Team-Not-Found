import React from "react";
import { PageHeader } from "../components/layout/PageHeader";
import { PageContainer } from "../components/layout/PageContainer";
import { StatusBadge } from "../components/ui/StatusBadge";
import { Card } from "../components/ui/Card";
import { ErrorState } from "../components/ui/ErrorState";
import { CongestionMap, MapControls, TerminalDetailDrawer, useCongestionMap } from "../features/heatmap";
import { formatHours } from "../lib/formatters";

export default function CongestionPage() {
  const { terminals, filteredTerminals, selectedTerminal, terminalVessels, anchorages, filterState, datasetSource,
    setSelectedTerminalCode, setHorizon, setSeverityFilter, setMode, toggleLayer, isLoading, error } = useCongestionMap();

  if (error) return <PageContainer><PageHeader title="Congestion Intelligence & Heatmap" description="Spatial density, terminal congestion indices, and anchorage queues across San Pedro Bay." breadcrumbs={["Command", "Congestion"]} /><ErrorState title="Unable to load congestion telemetry" message={error instanceof Error ? error.message : String(error)} onRetry={() => window.location.reload()} /></PageContainer>;

  const isForecast = filterState.mode === "FORECAST";
  // Playtest fix: on first visit these KPIs rendered 0 / UNKNOWN while queries loaded,
  // reading as "no data" instead of "loading".
  const d = (v: string | number) => (isLoading ? "…" : v);
  const totalAnchoredVessels = anchorages.reduce((sum, a) => sum + a.vessels_count, 0);
  const avgWaitHours = terminals.length ? terminals.reduce((sum, t) => sum + t.wait_now, 0) / terminals.length : 0;
  const criticalCount = terminals.filter((t) => (isForecast ? t.peak_index : t.current_index) >= 80).length;
  const criticalCodes = terminals.filter((t) => (isForecast ? t.peak_index : t.current_index) >= 80).map((t) => t.code).join(", ");
  const sourceLabel = isLoading ? "…" : datasetSource === "AIS" ? "NOAA AIS" : datasetSource === "DEMO_AIS" ? "DEMO_AIS" : datasetSource;

  return (
    <PageContainer>
      <PageHeader title="Congestion Intelligence & Map" description="Spatial density, terminal congestion indices, anchorage queues, and physical bottleneck analysis across San Pedro Bay." breadcrumbs={["Command", "Congestion"]}
        status={<div className="flex items-center gap-1.5"><StatusBadge status="OPERATIONAL" size="xs" /><span className="text-[10px] font-mono text-[var(--text-muted)] bg-[var(--bg-surface-elevated)] px-1.5 py-0.5 rounded border border-[var(--border-subtle)]">MapLibre v6</span></div>} />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]"><div className="text-[10px] uppercase font-bold text-[var(--text-muted)] tracking-wider">Active Terminals</div><div className="text-lg font-bold text-[var(--text-primary)] font-mono mt-1">{d(terminals.length)}</div><div className="text-[10px] text-[var(--text-secondary)] mt-0.5">Port of Long Beach reference set</div></div>
        <div className="p-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]"><div className="text-[10px] uppercase font-bold text-[var(--text-muted)] tracking-wider">Anchorage Queue</div><div className="text-lg font-bold text-[var(--text-primary)] font-mono mt-1">{d(totalAnchoredVessels)} <span className="text-xs text-[var(--text-secondary)] font-normal font-sans">vessels</span></div><div className="text-[10px] text-[var(--text-secondary)] mt-0.5">Avg wait: <span className="font-semibold text-[var(--text-primary)]">{isLoading ? "…" : formatHours(avgWaitHours)}</span></div></div>
        <div className="p-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]"><div className="text-[10px] uppercase font-bold text-[var(--text-muted)] tracking-wider">{isForecast ? "Forecast Peak Hotspots" : "Current Hotspots"}</div><div className={`text-lg font-bold font-mono mt-1 ${!isLoading && criticalCount > 0 ? "text-[var(--status-critical)]" : "text-[var(--status-success)]"}`}>{d(criticalCount)} <span className="text-xs font-normal font-sans text-[var(--text-secondary)]">terminals &gt; 80</span></div><div className="text-[10px] text-[var(--text-secondary)] mt-0.5 truncate">{isLoading ? "loading…" : criticalCodes ? `Bottlenecks: ${criticalCodes}` : (isForecast ? "No peak alerts" : "Normal operations")}</div></div>
        <div className="p-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]"><div className="text-[10px] uppercase font-bold text-[var(--text-muted)] tracking-wider">Operational History</div><div className="text-lg font-bold text-[var(--text-accent)] font-mono mt-1">{sourceLabel}</div><div className="text-[10px] text-[var(--text-secondary)] mt-0.5">{isLoading ? "loading dataset…" : datasetSource === "AIS" ? "Measured NOAA AccessAIS history" : datasetSource === "DEMO_AIS" ? "Synthetic SimPy demo history" : "No dataset loaded"}</div></div>
      </div>

      <MapControls filterState={filterState} terminals={terminals} onSelectTerminal={(code) => setSelectedTerminalCode(code)} onSetHorizon={setHorizon} onSetSeverity={setSeverityFilter} onSetMode={setMode} onToggleLayer={toggleLayer} onResetView={() => setSelectedTerminalCode(null)} />
      {isLoading ? <div className="h-[400px] sm:h-[480px] lg:h-[580px] w-full rounded-lg bg-[var(--bg-surface-elevated)] animate-pulse border border-[var(--border-default)]" /> : <CongestionMap terminals={filteredTerminals} anchorages={anchorages} filterState={filterState} selectedTerminal={selectedTerminal} onSelectTerminal={(code) => setSelectedTerminalCode(code)} />}

      <div className="space-y-3"><div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1"><h2 className="text-sm font-semibold text-[var(--text-primary)] tracking-tight">Terminal Capacity &amp; Live Hotspot Ranking</h2><span className="text-xs text-[var(--text-muted)]">Click any terminal card or map marker to inspect berths and vessel queue</span></div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">{terminals.map((term) => { const isSelected = selectedTerminal?.code === term.code; const val = filterState.mode === "FORECAST" ? term.peak_index : term.current_index; return <Card key={term.code} variant={isSelected ? "elevated" : "interactive"} onClick={() => setSelectedTerminalCode(term.code)} className={`transition-all ${isSelected ? "ring-2 ring-[var(--accent)] border-[var(--accent)]" : ""}`}><div className="flex items-start justify-between"><div><div className="flex items-center gap-1.5"><span className="font-bold text-sm text-[var(--text-primary)]">{term.code}</span><span className="text-xs font-mono text-[var(--text-muted)]">({term.pier})</span></div><p className="text-[11px] text-[var(--text-secondary)] truncate max-w-[180px]">{term.name}</p></div><StatusBadge status={term.level} size="xs" /></div><div className="mt-3 flex items-baseline justify-between border-t border-[var(--border-subtle)] pt-2.5"><div><div className="text-[10px] text-[var(--text-muted)] uppercase">{filterState.mode === "FORECAST" ? "Peak 72h" : "Index Now"}</div><div className="text-xl font-bold font-mono text-[var(--brand)]">{val.toFixed(1)}</div></div><div className="text-right text-xs"><div className="text-[11px] text-[var(--text-primary)] font-medium">q: <strong className="font-mono">{term.queue_now}</strong> · wait: <strong className="font-mono">{term.wait_now.toFixed(0)}h</strong></div><div className="text-[10px] text-[var(--text-muted)]">{term.deepsea_berths} berths · {term.gantry_cranes} cranes</div></div></div>{term.binding_constraint && <div className="mt-2 text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] text-[var(--text-secondary)] flex items-center justify-between"><span>Binding:</span><strong className="text-[var(--text-accent)]">{term.binding_constraint}</strong></div>}</Card>; })}</div>
      </div>
      <TerminalDetailDrawer terminal={selectedTerminal} open={Boolean(selectedTerminal)} onClose={() => setSelectedTerminalCode(null)} vessels={terminalVessels} />
    </PageContainer>
  );
}
