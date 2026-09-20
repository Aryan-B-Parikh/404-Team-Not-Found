export type RoutingOption = "DIVERT" | "SLOW_STEAM" | "PRIORITY_WINDOW" | "HOLD";

export interface RoutingRecommendation {
  vessel_id: number;
  vessel_name: string;
  carrier: string;
  vessel_class: string;
  dest_zone_code: string;
  status: string;
  predicted_wait_hours: number;
  option: RoutingOption;
  target_port: string | null;
  eta_shift_hours: number;
  est_savings_usd: number;
  confidence: number;
  tier: "critical" | "high" | "medium" | "low";
  sustained: boolean;
  rationale: string;
}

export interface RoutingCostModel {
  daily_op_cost_usd: number;
  reefer_value_usd: number;
  alt_ports: string[];
}

export interface RoutingApiResponse {
  recommendations: RoutingRecommendation[];
  counts: Record<string, number>;
  total_savings_usd: number;
  cost_model: RoutingCostModel;
}
