import React from "react";
import {
  Ship,
  Route,
  Clock,
  DollarSign,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  Building2,
  Calendar,
  Sparkles,
  GitCompare,
  Bot,
} from "lucide-react";
import { Drawer } from "../../components/ui/Drawer";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import type { RoutingRecommendation, RoutingCostModel } from "./types";

export interface RoutingDetailDrawerProps {
  recommendation: RoutingRecommendation | null;
  costModel?: RoutingCostModel;
  open: boolean;
  onClose: () => void;
  onSimulateScenario?: () => void;
  onAskBob?: (prompt: string) => void;
}

export function RoutingDetailDrawer({
  recommendation,
  costModel,
  open,
  onClose,
  onSimulateScenario,
  onAskBob,
}: RoutingDetailDrawerProps) {
  if (!recommendation) return null;

  const r = recommendation;

  const optionColors: Record<string, { bg: string; text: string; border: string }> = {
    DIVERT: {
      bg: "var(--status-critical-bg)",
      text: "var(--status-critical)",
      border: "var(--status-critical-border)",
    },
    SLOW_STEAM: {
      bg: "var(--status-warning-bg)",
      text: "var(--status-warning)",
      border: "var(--status-warning-border)",
    },
    PRIORITY_WINDOW: {
      bg: "var(--brand-soft)",
      text: "var(--text-accent)",
      border: "var(--brand-border)",
    },
    HOLD: {
      bg: "var(--bg-surface-elevated)",
      text: "var(--text-secondary)",
      border: "var(--border-subtle)",
    },
  };

  const currentOptionStyle = optionColors[r.option] || optionColors.HOLD;

  return (
    <Drawer
      open={open}
      onOpenChange={(isOpen) => !isOpen && onClose()}
      width="lg"
      title={
        <div className="flex items-center gap-2">
          <Ship className="w-4 h-4 text-[var(--brand)] shrink-0" />
          <span>{r.vessel_name}</span>
          <span
            className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border"
            style={{
              backgroundColor: currentOptionStyle.bg,
              color: currentOptionStyle.text,
              borderColor: currentOptionStyle.border,
            }}
          >
            {r.option}
          </span>
        </div>
      }
      description={
        <div className="flex items-center gap-2 text-[11px] text-[var(--text-muted)] font-mono mt-0.5">
          <span>Carrier: {r.carrier}</span>
          <span>·</span>
          <span>Class: {r.vessel_class}</span>
          <span>·</span>
          <span>Status: {r.status}</span>
        </div>
      }
      footer={
        <div className="flex flex-wrap items-center justify-between gap-2 w-full">
          <div className="text-[11px] text-[var(--text-muted)] italic">
            Decision-support recommendation (Advisory)
          </div>
          <div className="flex items-center gap-2">
            {onSimulateScenario && (
              <Button
                size="sm"
                variant="outline"
                onClick={onSimulateScenario}
                icon={<GitCompare className="w-3.5 h-3.5" />}
                className="text-xs"
              >
                Simulate Scenario
              </Button>
            )}
            {onAskBob && (
              <Button
                size="sm"
                variant="primary"
                onClick={() =>
                  onAskBob(
                    `Explain routing recommendation for ${r.vessel_name}: recommended option is ${r.option}${
                      r.target_port ? ` to ${r.target_port}` : ""
                    } with predicted wait of ${r.predicted_wait_hours}h.`
                  )
                }
                icon={<Bot className="w-3.5 h-3.5" />}
                className="text-xs"
              >
                Explain with Bob AI
              </Button>
            )}
          </div>
        </div>
      }
    >
      <div className="space-y-4 text-xs">
        {/* Comparison: Current Status vs Recommended Action */}
        <div className="p-4 rounded-lg bg-[var(--bg-surface-elevated)] border border-[var(--border-default)]">
          <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-muted)] mb-3">
            Trajectory Comparison
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Left: Baseline Destination */}
            <div className="p-3 rounded-md bg-[var(--bg-surface)] border border-[var(--border-subtle)] space-y-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                Current Assigned Destination
              </span>
              <div className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                <Building2 className="w-4 h-4 text-[var(--text-secondary)]" />
                <span>{r.dest_zone_code}</span>
              </div>
              <div className="text-[11px] text-[var(--status-critical)] font-mono">
                Predicted Wait: {r.predicted_wait_hours.toFixed(1)} hours
              </div>
            </div>

            {/* Right: Recommended Action */}
            <div className="p-3 rounded-md bg-[var(--bg-surface)] border border-[var(--border-accent)] space-y-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-accent)]">
                Recommended Alternative
              </span>
              <div className="text-sm font-bold text-[var(--brand)] flex items-center gap-1.5">
                <Route className="w-4 h-4" />
                <span>{r.target_port ? `Divert to ${r.target_port}` : r.option}</span>
              </div>
              <div className="text-[11px] text-[var(--status-success)] font-mono">
                ETA Shift: {r.eta_shift_hours > 0 ? `+${r.eta_shift_hours}h` : `${r.eta_shift_hours}h`}
              </div>
            </div>
          </div>
        </div>

        {/* Operational Rationale */}
        <div className="p-3.5 rounded-lg bg-[var(--bg-surface-elevated)]/60 border border-[var(--border-subtle)] space-y-2">
          <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-[11px] text-[var(--text-primary)]">
            <Sparkles className="w-3.5 h-3.5 text-[var(--brand)]" />
            <span>Economic &amp; Operational Rationale</span>
          </div>
          <p className="text-xs text-[var(--text-secondary)] leading-relaxed italic">
            "{r.rationale}"
          </p>
        </div>

        {/* Economic Impact Breakdown Cards */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-default)]">
            <div className="text-[10px] uppercase font-bold text-[var(--text-muted)]">
              Estimated Net Savings
            </div>
            <div className="text-lg font-bold font-mono text-[var(--status-success)] mt-1">
              ${r.est_savings_usd.toLocaleString()}
            </div>
            <div className="text-[10px] text-[var(--text-muted)] mt-0.5">
              Fuel &amp; demurrage avoided
            </div>
          </div>

          <div className="p-3 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-default)]">
            <div className="text-[10px] uppercase font-bold text-[var(--text-muted)]">
              Model Confidence
            </div>
            <div className="text-lg font-bold font-mono text-[var(--brand)] mt-1">
              {(r.confidence * 100).toFixed(0)}%
            </div>
            <div className="text-[10px] text-[var(--text-muted)] mt-0.5">
              {r.sustained ? "Sustained congestion confirmed" : "Single forecast cycle"}
            </div>
          </div>
        </div>

        {/* Reference Cost Model Info */}
        {costModel && (
          <div className="p-3 rounded-md bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] space-y-1 text-[11px] text-[var(--text-muted)]">
            <div className="font-semibold text-[var(--text-secondary)]">Cost Model Parameters:</div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[10px]">
              <span>Daily Vessel Op Cost: ${costModel.daily_op_cost_usd.toLocaleString()}/day</span>
              <span>Reefer Cargo Value: ${costModel.reefer_value_usd}/container</span>
              <span>Alternate Ports: {costModel.alt_ports.join(", ")}</span>
            </div>
          </div>
        )}
      </div>
    </Drawer>
  );
}
