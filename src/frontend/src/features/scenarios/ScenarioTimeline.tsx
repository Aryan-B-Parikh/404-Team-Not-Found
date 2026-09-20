import React from "react";
import {
  Bar,
  BarChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/Card";
import type { ScenarioResponse } from "./types";

export interface ScenarioTimelineProps {
  data: ScenarioResponse;
}

/**
 * Honest solver comparison (density + honesty pass).
 *
 * The previous version here interpolated a per-shift trajectory with Math.sin from
 * four real totals and presented it as "derived from CP-SAT" — fabricated shape,
 * fabricated quota line, hardcoded fallbacks. CP-SAT returns scenario-level totals,
 * so that is the only thing charted: the real baseline vs scenario metrics, one
 * grouped bar per metric. No interpolation, no invented series.
 */
export function ScenarioTimeline({ data }: ScenarioTimelineProps) {
  const { baseline, scenario } = data;
  if (!baseline || !scenario) return null;

  const chartData = [
    {
      metric: "Vessels serviced",
      Baseline: baseline.serviced ?? 0,
      Scenario: scenario.serviced ?? 0,
      unit: "",
    },
    {
      metric: "Total moves",
      Baseline: Math.round((baseline.total_moves ?? 0) / 1000),
      Scenario: Math.round((scenario.total_moves ?? 0) / 1000),
      unit: "k",
    },
    {
      metric: "Avg wait (h)",
      Baseline: baseline.avg_wait_hours ?? 0,
      Scenario: scenario.avg_wait_hours ?? 0,
      unit: "h",
    },
  ];

  return (
    <Card>
      <CardHeader className="pb-2">
        <div>
          <CardTitle className="text-sm">CP-SAT result — baseline vs scenario</CardTitle>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Solver-level totals only. The engine does not produce per-shift trajectories, so none is drawn.
          </p>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-56 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
              <XAxis
                dataKey="metric"
                stroke="var(--text-muted)"
                fontSize={10}
                tickLine={false}
                axisLine={{ stroke: "var(--border-default)" }}
              />
              <YAxis
                stroke="var(--text-muted)"
                fontSize={10}
                tickLine={false}
                axisLine={{ stroke: "var(--border-default)" }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--bg-surface-elevated)",
                  borderColor: "var(--border-default)",
                  borderRadius: "8px",
                  fontSize: "11px",
                  color: "var(--text-primary)",
                }}
                formatter={(val: any, _name: any, item: any) => {
                  const unit = item?.payload?.unit ?? "";
                  return [`${Number(val).toLocaleString()}${unit}`, _name];
                }}
              />
              <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
              <Bar dataKey="Baseline" fill="var(--brand)" radius={[3, 3, 0, 0]} maxBarSize={48} />
              <Bar dataKey="Scenario" fill="var(--status-warning)" radius={[3, 3, 0, 0]} maxBarSize={48} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
