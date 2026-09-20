import React from "react";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  CheckCircle2,
  AlertTriangle,
  Cpu,
  DollarSign,
  Ship,
  Clock,
  Boxes,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/Card";
import { StatusBadge } from "../../components/ui/StatusBadge";
import type { ScenarioResponse } from "./types";

export interface ScenarioComparisonProps {
  data: ScenarioResponse;
}

export function ScenarioComparison({ data }: { data: ScenarioResponse }) {
  const { baseline, scenario, impact, solver } = data;

  // Real API metrics
  const baseServiced = baseline?.serviced ?? 0;
  const scenServiced = scenario?.serviced ?? 0;
  const deltaServiced = impact?.serviced ?? (scenServiced - baseServiced);

  const baseMoves = baseline?.total_moves ?? 0;
  const scenMoves = scenario?.total_moves ?? 0;
  const deltaMoves = impact?.moves ?? (scenMoves - baseMoves);

  const baseWait = baseline?.avg_wait_hours ?? 0;
  const scenWait = scenario?.avg_wait_hours ?? 0;
  const deltaWait = impact?.avg_wait ?? (scenWait - baseWait);

  // Economic impact calculation based on documented maritime operating cost ($32,000/day = $1,333/hour/vessel)
  const hourlyCostPerVessel = 32000 / 24;
  const costImpactUsd = Math.round(deltaWait * baseServiced * hourlyCostPerVessel);

  return (
    <div className="space-y-4">
      {/* Top Solvers & Lineage Status Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-default)] text-xs">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-[var(--brand)]" />
          <span className="font-semibold text-[var(--text-primary)]">
            CP-SAT Discrete Solver Result
          </span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] text-[var(--text-secondary)]">
            Scenario #{data.scenario_id} ({data.params?.kind || "DISRUPTION"})
          </span>
        </div>

        <div className="flex items-center gap-3 font-mono text-[11px] text-[var(--text-muted)]">
          <div className="flex items-center gap-1.5">
            <span>Baseline:</span>
            <span className="text-[var(--text-primary)] font-semibold">
              {solver?.baseline?.status || "OPTIMAL"}
            </span>
            {solver?.baseline?.wall_time_s !== undefined && (
              <span>({solver.baseline.wall_time_s.toFixed(2)}s)</span>
            )}
          </div>
          <span>·</span>
          <div className="flex items-center gap-1.5">
            <span>Scenario:</span>
            <span
              className={
                solver?.scenario?.status === "OPTIMAL"
                  ? "text-[var(--status-success)] font-semibold"
                  : "text-[var(--status-warning)] font-semibold"
              }
            >
              {solver?.scenario?.status || "FEASIBLE"}
            </span>
            {solver?.scenario?.wall_time_s !== undefined && (
              <span>({solver.scenario.wall_time_s.toFixed(2)}s)</span>
            )}
          </div>
        </div>
      </div>

      {/* Primary KPI Comparison Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Card 1: Serviced Vessels */}
        <div className="p-4 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-default)] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-[11px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
              <span className="flex items-center gap-1.5">
                <Ship className="w-3.5 h-3.5 text-[var(--brand)]" />
                Vessels Serviced
              </span>
              <span className="text-[10px] font-mono">Horizon (72h)</span>
            </div>

            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-xl font-bold font-mono text-[var(--text-primary)]">
                {scenServiced}
              </span>
              <span className="text-xs font-mono text-[var(--text-muted)]">
                from {baseServiced}
              </span>
            </div>
          </div>

          <div className="mt-3 pt-2 border-t border-[var(--border-subtle)] flex items-center justify-between">
            <span className="text-[11px] text-[var(--text-secondary)]">Throughput Delta</span>
            <DeltaPill
              value={deltaServiced}
              format={(v) => `${v > 0 ? "+" : ""}${v} vessels`}
              favorable="HIGHER"
            />
          </div>
        </div>

        {/* Card 2: Total Container Moves */}
        <div className="p-4 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-default)] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-[11px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
              <span className="flex items-center gap-1.5">
                <Boxes className="w-3.5 h-3.5 text-[var(--brand)]" />
                Container Moves
              </span>
              <span className="text-[10px] font-mono">TEU Lifts</span>
            </div>

            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-xl font-bold font-mono text-[var(--text-primary)]">
                {scenMoves.toLocaleString()}
              </span>
              <span className="text-xs font-mono text-[var(--text-muted)]">
                from {baseMoves.toLocaleString()}
              </span>
            </div>
          </div>

          <div className="mt-3 pt-2 border-t border-[var(--border-subtle)] flex items-center justify-between">
            <span className="text-[11px] text-[var(--text-secondary)]">Lift Capacity</span>
            <DeltaPill
              value={deltaMoves}
              format={(v) => `${v > 0 ? "+" : ""}${v.toLocaleString()}`}
              favorable="HIGHER"
            />
          </div>
        </div>

        {/* Card 3: Average Dwell / Wait Time */}
        <div className="p-4 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-default)] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-[11px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-[var(--brand)]" />
                Avg Wait Time
              </span>
              <span className="text-[10px] font-mono">Dwell Hours</span>
            </div>

            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-xl font-bold font-mono text-[var(--text-primary)]">
                {scenWait.toFixed(1)}h
              </span>
              <span className="text-xs font-mono text-[var(--text-muted)]">
                from {baseWait.toFixed(1)}h
              </span>
            </div>
          </div>

          <div className="mt-3 pt-2 border-t border-[var(--border-subtle)] flex items-center justify-between">
            <span className="text-[11px] text-[var(--text-secondary)]">Congestion Impact</span>
            <DeltaPill
              value={deltaWait}
              format={(v) => `${v > 0 ? "+" : ""}${v.toFixed(1)}h`}
              favorable="LOWER"
            />
          </div>
        </div>

        {/* Card 4: Estimated Fleet Cost Delta */}
        <div className="p-4 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-default)] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-[11px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
              <span className="flex items-center gap-1.5">
                <DollarSign className="w-3.5 h-3.5 text-[var(--brand)]" />
                Fleet Economic Impact
              </span>
              <span className="text-[10px] font-mono">$32k/day model</span>
            </div>

            <div className="mt-2 flex items-baseline gap-2">
              <span
                className={`text-xl font-bold font-mono ${
                  costImpactUsd > 0
                    ? "text-[var(--status-critical)]"
                    : costImpactUsd < 0
                    ? "text-[var(--status-success)]"
                    : "text-[var(--text-primary)]"
                }`}
              >
                {costImpactUsd > 0 ? `+$${costImpactUsd.toLocaleString()}` : `-$${Math.abs(costImpactUsd).toLocaleString()}`}
              </span>
            </div>
          </div>

          <div className="mt-3 pt-2 border-t border-[var(--border-subtle)] flex items-center justify-between text-[10px] text-[var(--text-muted)]">
            <span>Demurrage &amp; Idle Burn</span>
            <span className="font-mono">
              {costImpactUsd > 0 ? "Cost Increase" : costImpactUsd < 0 ? "Cost Savings" : "Cost Neutral"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function DeltaPill({
  value,
  format,
  favorable,
}: {
  value: number;
  format: (v: number) => string;
  favorable: "HIGHER" | "LOWER";
}) {
  const isZero = Math.abs(value) < 0.01;
  const isGood = favorable === "HIGHER" ? value > 0 : value < 0;

  if (isZero) {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-[var(--bg-surface-elevated)] text-[var(--text-muted)] border border-[var(--border-subtle)]">
        <Minus className="w-3 h-3" />
        <span>Unchanged</span>
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold border ${
        isGood
          ? "bg-[var(--status-success-bg)] text-[var(--status-success)] border-[var(--status-success-border)]"
          : "bg-[var(--status-critical-bg)] text-[var(--status-critical)] border-[var(--status-critical-border)]"
      }`}
    >
      {isGood ? (
        <TrendingDown className="w-3 h-3" />
      ) : (
        <TrendingUp className="w-3 h-3" />
      )}
      <span>{format(value)}</span>
    </span>
  );
}
