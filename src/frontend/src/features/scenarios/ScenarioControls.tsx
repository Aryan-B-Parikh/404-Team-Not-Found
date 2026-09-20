import React from "react";
import { Sliders, Play, RotateCcw, AlertCircle, Sparkles, CheckCircle2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import type { ScenarioParams, ScenarioPreset } from "./types";

export interface ScenarioControlsProps {
  params: ScenarioParams;
  onChangeParams: (params: ScenarioParams) => void;
  activePresetId: string;
  onApplyPreset: (preset: ScenarioPreset) => void;
  onRunScenario: () => void;
  isLoading: boolean;
  presets: ScenarioPreset[];
}

export function ScenarioControls({
  params,
  onChangeParams,
  activePresetId,
  onApplyPreset,
  onRunScenario,
  isLoading,
  presets,
}: ScenarioControlsProps) {
  return (
    <div className="space-y-4">
      {/* Disruption & Optimization Presets */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-[var(--brand)]" />
            <span>Operational Scenario Presets</span>
          </label>
          <span className="text-[11px] text-[var(--text-muted)]">
            OR-Tools CP-SAT discrete solver
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {presets.map((preset) => {
            const isSelected = activePresetId === preset.id;
            return (
              <button
                key={preset.id}
                type="button"
                onClick={() => onApplyPreset(preset)}
                className={`p-3 rounded-lg border text-left transition-all cursor-pointer flex flex-col justify-between ${
                  isSelected
                    ? "bg-[var(--bg-surface-elevated)] border-[var(--accent)] shadow-xs ring-1 ring-[var(--accent)]/30"
                    : "bg-[var(--bg-surface)] border-[var(--border-default)] hover:border-[var(--border-elevated)] hover:bg-[var(--bg-surface-hover)]"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-[var(--text-primary)]">
                      {preset.name}
                    </span>
                    {isSelected && (
                      <CheckCircle2 className="w-3.5 h-3.5 text-[var(--brand)] shrink-0" />
                    )}
                  </div>
                  <p className="text-[11px] text-[var(--text-secondary)] mt-1 line-clamp-2">
                    {preset.description}
                  </p>
                </div>
                <div className="mt-2.5 pt-2 border-t border-[var(--border-subtle)] flex items-center justify-between text-[10px] font-mono text-[var(--text-muted)]">
                  <span>Cranes: {(preset.crane_factor * 100).toFixed(0)}%</span>
                  <span>Rate: {preset.move_rate} m/h</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Parametric Adjustment Card */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-[var(--brand)]" />
              <CardTitle className="text-sm">Custom Parametric Stress Tuning</CardTitle>
            </div>
            <div className="text-[11px] font-mono text-[var(--text-muted)]">
              Boundary: 50–100% capacity · 20–35 moves/h
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Slider 1: Crane Availability Factor */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-[var(--text-primary)]">
                  Quay Crane Availability Factor
                </label>
                <span className="text-xs font-mono font-bold text-[var(--brand)] bg-[var(--bg-surface-elevated)] px-2 py-0.5 rounded border border-[var(--border-subtle)]">
                  {(params.crane_factor * 100).toFixed(0)}%
                </span>
              </div>
              <input
                type="range"
                min="0.5"
                max="1.0"
                step="0.05"
                value={params.crane_factor}
                onChange={(e) =>
                  onChangeParams({
                    ...params,
                    crane_factor: parseFloat(e.target.value),
                  })
                }
                className="w-full accent-[var(--accent)] cursor-pointer h-1.5 rounded-lg bg-[var(--bg-surface-elevated)]"
              />
              <div className="flex justify-between text-[10px] font-mono text-[var(--text-muted)]">
                <span>50% (Severe Outage)</span>
                <span>85% (Typical Breakdown)</span>
                <span>100% (Nominal)</span>
              </div>
            </div>

            {/* Slider 2: Move Rate per Crane-Hour */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-[var(--text-primary)]">
                  Throughput Move Rate per Crane-Hour
                </label>
                <span className="text-xs font-mono font-bold text-[var(--brand)] bg-[var(--bg-surface-elevated)] px-2 py-0.5 rounded border border-[var(--border-subtle)]">
                  {params.move_rate_per_crane_hour.toFixed(1)} moves/h
                </span>
              </div>
              <input
                type="range"
                min="20.0"
                max="35.0"
                step="1.0"
                value={params.move_rate_per_crane_hour}
                onChange={(e) =>
                  onChangeParams({
                    ...params,
                    move_rate_per_crane_hour: parseFloat(e.target.value),
                  })
                }
                className="w-full accent-[var(--accent)] cursor-pointer h-1.5 rounded-lg bg-[var(--bg-surface-elevated)]"
              />
              <div className="flex justify-between text-[10px] font-mono text-[var(--text-muted)]">
                <span>20 m/h (Congested Yard)</span>
                <span>28 m/h (Design Baseline)</span>
                <span>35 m/h (Automated Dual)</span>
              </div>
            </div>
          </div>

          {/* Action Row */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-[var(--border-subtle)]">
            <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
              <span className="font-semibold text-[var(--text-primary)]">Baseline:</span>
              <span className="font-mono">100% cranes @ 28.0 m/h</span>
              <span className="text-[var(--text-muted)]">vs</span>
              <span className="font-semibold text-[var(--text-accent)]">Scenario:</span>
              <span className="font-mono">
                {(params.crane_factor * 100).toFixed(0)}% cranes @{" "}
                {params.move_rate_per_crane_hour.toFixed(0)} m/h
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="primary"
                onClick={onRunScenario}
                loading={isLoading}
                icon={<Play className="w-3.5 h-3.5 fill-current" />}
              >
                <span>{isLoading ? "Solving CP-SAT..." : "Execute Simulation"}</span>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Honest Boundary Notice for Extended Scenarios */}
      <div className="p-2.5 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-elevated)]/50 text-[11px] text-[var(--text-muted)] flex items-start gap-2">
        <AlertCircle className="w-3.5 h-3.5 text-[var(--status-info)] shrink-0 mt-0.5" />
        <div>
          <strong className="text-[var(--text-secondary)] font-medium">Solver Contract:</strong>{" "}
          Quay crane availability factor and container move rate parameters execute live discrete optimization on OR-Tools CP-SAT via{" "}
          <code className="font-mono text-[var(--text-accent)]">POST /api/scenarios</code>. Extended multi-terminal berth modifications are routed through W3's pipeline contract.
        </div>
      </div>
    </div>
  );
}
