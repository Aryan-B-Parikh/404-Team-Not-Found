export interface ScenarioParams {
  crane_factor: number;
  move_rate_per_crane_hour: number;
  kind?: string;
}

export interface SolverMetrics {
  serviced: number;
  total_moves: number;
  avg_wait_hours: number;
  total_hours?: number;
  [key: string]: any;
}

export interface SolverStats {
  status: string;
  wall_time_s?: number;
  branches?: number;
  objective_value?: number;
  [key: string]: any;
}

export interface ScenarioResponse {
  scenario_id: number;
  params: ScenarioParams;
  baseline: SolverMetrics;
  scenario: SolverMetrics;
  impact: {
    serviced: number;
    moves: number;
    avg_wait: number;
  };
  weights: Record<string, number>;
  solver: {
    baseline: SolverStats;
    scenario: SolverStats;
  };
}

export interface ScenarioPreset {
  id: string;
  name: string;
  description: string;
  crane_factor: number;
  move_rate: number;
  category: "STANDARD" | "DISRUPTION" | "PRODUCTIVITY" | "STRESS";
  badgeColor: string;
}
