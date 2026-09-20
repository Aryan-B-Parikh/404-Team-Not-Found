// Types for Phase 2 Congestion Intelligence & MapLibre Heatmap

export interface BerthInfo {
  name: string;
  seq: number;
  length_ft: number;
  depth_ft: number;
  cranes_max: number;
  status?: string;
  current_vessel?: string | null;
}

export interface CraneInfo {
  code: string;
  crane_type: string;
  reach_ft: number;
  rated_moves_per_hour: number;
  status: string;
  status_reason?: string | null;
}

export interface TerminalFeature {
  code: string; // LBCT | ITS | PCT | TTI
  name: string;
  pier: string;
  lat: number;
  lon: number;
  berth_length_ft: number;
  deepsea_berths: number;
  gantry_cranes: number;
  capacity_teu_m?: number | null;
  zone_code: string;
  note?: string | null;
  berths?: BerthInfo[];
  cranes?: CraneInfo[];
}

export interface EnrichedTerminal extends TerminalFeature {
  current_index: number;
  peak_index: number;
  peak_hour: number;
  queue_now: number;
  wait_now: number;
  yard_util_pct: number;
  level: "LOW" | "ELEVATED" | "HIGH" | "CRITICAL" | string;
  risk_score?: number;
  binding_constraint?: string;
  confidence?: string;
  has_anomaly?: boolean;
  anomaly_kind?: string;
  recent_index?: number[];
}

export interface AnchorageZone {
  code: string;
  name: string;
  lat: number;
  lon: number;
  vessels_count: number;
  avg_wait_hours: number;
}

export interface VesselItem {
  id: number;
  name: string;
  carrier: string;
  vessel_class: string;
  loa_ft: number;
  beam_ft: number;
  draft_ft: number;
  teu_capacity: number;
  status: "ANCHORAGE" | "INBOUND" | "BERTHED" | string;
  anchorage_zone?: string | null;
  dest_zone_code?: string | null;
  eta_hours?: number | null;
  anchored_hours?: number | null;
}

export interface MapFilterState {
  horizon: 24 | 48 | 72;
  selectedTerminalCode: string | null;
  severityFilter: "ALL" | "LOW" | "ELEVATED" | "HIGH" | "CRITICAL";
  mode: "CURRENT" | "FORECAST";
  layers: {
    heatmap: boolean;
    markers: boolean;
    anchorage: boolean;
    fairway: boolean;
  };
}
