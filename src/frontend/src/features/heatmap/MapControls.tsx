import React from "react";
import { SlidersHorizontal, RotateCcw, Layers, Clock, TrendingUp, Flame } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import type { MapFilterState, EnrichedTerminal } from "./types";

export interface MapControlsProps {
  filterState: MapFilterState;
  terminals: EnrichedTerminal[];
  onSelectTerminal: (code: string | null) => void;
  onSetHorizon: (horizon: 24 | 48 | 72) => void;
  onSetSeverity: (severity: MapFilterState["severityFilter"]) => void;
  onSetMode: (mode: "CURRENT" | "FORECAST") => void;
  onToggleLayer: (layer: keyof MapFilterState["layers"]) => void;
  onResetView: () => void;
}

export function MapControls({
  filterState,
  terminals,
  onSelectTerminal,
  onSetHorizon,
  onSetSeverity,
  onSetMode,
  onToggleLayer,
  onResetView,
}: MapControlsProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] text-xs select-none">
      {/* Left controls: Horizon & Mode */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Mode Segmented Control */}
        <div className="flex flex-col gap-1">
          <div className="flex items-center rounded-lg bg-[var(--bg-surface-elevated)] p-1 border border-[var(--border-default)] shadow-xs">
            <button
              type="button"
              onClick={() => onSetMode("CURRENT")}
              aria-pressed={filterState.mode === "CURRENT"}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                filterState.mode === "CURRENT"
                  ? "bg-[var(--bg-surface)] text-[var(--brand)] shadow-xs border border-[var(--border-accent)]"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-transparent"
              }`}
            >
              <Clock className="w-3.5 h-3.5" />
              <span>CURRENT</span>
            </button>
            <button
              type="button"
              onClick={() => onSetMode("FORECAST")}
              aria-pressed={filterState.mode === "FORECAST"}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                filterState.mode === "FORECAST"
                  ? "bg-[var(--bg-surface)] text-[var(--status-warning)] shadow-xs border border-[var(--status-warning)]/40"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-transparent"
              }`}
            >
              <TrendingUp className="w-3.5 h-3.5" />
              <span>FORECAST PEAK</span>
            </button>
          </div>
          <div className="text-[10px] px-1 font-medium select-none">
            {filterState.mode === "CURRENT" ? (
              <span className="text-[var(--text-muted)] flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
                Current operational state
              </span>
            ) : (
              <span className="text-[var(--status-warning)] flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--status-warning)] animate-pulse" />
                Predicted congestion peak
              </span>
            )}
          </div>
        </div>

        {/* Horizon Pills */}
        <div className="flex items-center gap-1 bg-[var(--bg-surface-elevated)] p-0.5 rounded-md border border-[var(--border-subtle)]">
          {[24, 48, 72].map((h) => (
            <button
              key={h}
              type="button"
              onClick={() => onSetHorizon(h as 24 | 48 | 72)}
              aria-label={`Forecast horizon +${h} hours`}
              className={`px-2 py-0.5 rounded text-[11px] font-mono font-medium transition-colors cursor-pointer ${
                filterState.horizon === h
                  ? "bg-[var(--brand)] text-white font-semibold shadow-2xs"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              }`}
            >
              +{h}h
            </button>
          ))}
        </div>

        {/* Terminal Selector */}
        <div className="w-full xs:w-44">
          <Select
            value={filterState.selectedTerminalCode || "ALL"}
            onChange={(e) => onSelectTerminal(e.target.value === "ALL" ? null : e.target.value)}
            sizeVariant="xs"
            aria-label="Filter by terminal"
          >
            <option value="ALL">All 4 Terminals</option>
            {terminals.map((t) => (
              <option key={t.code} value={t.code}>
                {t.code} — {t.pier} ({t.current_index.toFixed(1)})
              </option>
            ))}
          </Select>
        </div>

        {/* Severity Filter */}
        <div className="w-full xs:w-32">
          <Select
            value={filterState.severityFilter}
            onChange={(e) => onSetSeverity(e.target.value as any)}
            sizeVariant="xs"
            aria-label="Filter by congestion severity"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical (80+)</option>
            <option value="HIGH">High (60–80)</option>
            <option value="ELEVATED">Elevated (40–60)</option>
            <option value="LOW">Low (0–40)</option>
          </Select>
        </div>
      </div>

      {/* Right controls: Layer toggles and Reset */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Layer: Heatmap */}
        <Button
          size="xs"
          variant={filterState.layers.heatmap ? "accent" : "outline"}
          onClick={() => onToggleLayer("heatmap")}
          icon={<Flame className="w-3 h-3" />}
          title="Toggle congestion density heatmap"
          aria-label="Toggle congestion density heatmap layer"
        >
          Heatmap
        </Button>

        {/* Layer: Markers */}
        <Button
          size="xs"
          variant={filterState.layers.markers ? "accent" : "outline"}
          onClick={() => onToggleLayer("markers")}
          icon={<Layers className="w-3 h-3" />}
          title="Toggle terminal markers"
          aria-label="Toggle terminal markers layer"
        >
          Terminals
        </Button>

        {/* Reset View */}
        <Button
          size="xs"
          variant="outline"
          onClick={onResetView}
          icon={<RotateCcw className="w-3 h-3" />}
          title="Reset map camera to San Pedro Bay"
          aria-label="Reset map camera to San Pedro Bay"
        >
          Reset
        </Button>
      </div>
    </div>
  );
}
