"""Reference data + documented constants.

Terminal capacities are REAL Port of Long Beach fact-sheet figures (cited in
docs/setup-guide.md). Yard/gate figures and all cost/productivity constants are
documented demo assumptions.
"""

from __future__ import annotations

# ---------------------------------------------------------------- REAL terminals
# Source: Port of Long Beach terminal fact sheets (polb.com).
TERMINALS: list[dict] = [
    {
        "code": "LBCT",
        "name": "Long Beach Container Terminal",
        "pier": "Pier E",
        "lat": 33.750,
        "lon": -118.217,
        "berth_length_ft": 4200,
        "deepsea_berths": 3,
        "gantry_cranes": 18,
        "capacity_teu_m": 3.5,
        "zone_code": "Z-LBCT",
        "note": "3.5M+ TEU annual capacity; 18 STS dual-hoist/tandem cranes (POLB fact sheet)",
        "depth_ft": 50.0,
        "yards": [
            {"code": "E-N", "ground_slots_teu": 18000, "reefer_plugs": 900},
            {"code": "E-S", "ground_slots_teu": 16500, "reefer_plugs": 750},
            {"code": "E-REEF", "ground_slots_teu": 4200, "reefer_plugs": 1400},
            {"code": "E-EMP", "ground_slots_teu": 6000, "reefer_plugs": 0},
        ],
        "gate": {"lanes": 14, "trucks_per_hour": 130.0, "open_hours": "06:00-18:00"},
    },
    {
        "code": "ITS",
        "name": "International Transportation Service",
        "pier": "Pier G",
        "lat": 33.746,
        "lon": -118.203,
        "berth_length_ft": 4250,
        "deepsea_berths": 3,
        "gantry_cranes": 14,
        "capacity_teu_m": None,
        "zone_code": "Z-ITS",
        "note": "4,250 ft continuous berth (POLB fact sheet)",
        "depth_ft": 50.0,
        "yards": [
            {"code": "G-1", "ground_slots_teu": 14000, "reefer_plugs": 600},
            {"code": "G-2", "ground_slots_teu": 13000, "reefer_plugs": 500},
            {"code": "G-3", "ground_slots_teu": 11000, "reefer_plugs": 300},
            {"code": "G-REEF", "ground_slots_teu": 3600, "reefer_plugs": 900},
        ],
        "gate": {"lanes": 12, "trucks_per_hour": 110.0, "open_hours": "06:00-18:00"},
    },
    {
        "code": "PCT",
        "name": "Pier J Port Container Terminal",
        "pier": "Pier J",
        "lat": 33.741,
        "lon": -118.181,
        "berth_length_ft": 5902,
        "deepsea_berths": 4,
        "gantry_cranes": 14,
        "capacity_teu_m": None,
        "zone_code": "Z-PCT",
        "note": "5,902 ft berth, longest in the harbour (POLB fact sheet)",
        "depth_ft": 52.0,
        "yards": [
            {"code": "J-1", "ground_slots_teu": 16000, "reefer_plugs": 500},
            {"code": "J-2", "ground_slots_teu": 15000, "reefer_plugs": 450},
            {"code": "J-3", "ground_slots_teu": 13500, "reefer_plugs": 350},
            {"code": "J-4", "ground_slots_teu": 12000, "reefer_plugs": 250},
        ],
        "gate": {"lanes": 16, "trucks_per_hour": 150.0, "open_hours": "06:00-18:00"},
    },
    {
        "code": "TTI",
        "name": "Total Terminals International",
        "pier": "Pier T",
        "lat": 33.736,
        "lon": -118.210,
        "berth_length_ft": 5000,
        "deepsea_berths": 3,
        "gantry_cranes": 16,
        "capacity_teu_m": None,
        "zone_code": "Z-TTI",
        "note": "5,000 ft berth (POLB fact sheet)",
        "depth_ft": 50.0,
        "yards": [
            {"code": "T-1", "ground_slots_teu": 17000, "reefer_plugs": 400},
            {"code": "T-2", "ground_slots_teu": 15000, "reefer_plugs": 350},
            {"code": "T-3", "ground_slots_teu": 12000, "reefer_plugs": 300},
            {"code": "T-4", "ground_slots_teu": 9000, "reefer_plugs": 150},
        ],
        "gate": {"lanes": 14, "trucks_per_hour": 120.0, "open_hours": "06:00-18:00"},
    },
]

TERMINAL_ZONES = ["Z-LBCT", "Z-ITS", "Z-PCT", "Z-TTI"]
ALL_ZONES = ["Z-PORT", *TERMINAL_ZONES]
ZONE_LABELS = {
    "Z-PORT": "San Pedro Bay (port-wide)",
    "Z-LBCT": "LBCT · Pier E",
    "Z-ITS": "ITS · Pier G",
    "Z-PCT": "PCT · Pier J",
    "Z-TTI": "TTI · Pier T",
}

# ---------------------------------------------------------------- documented constants
CONGESTION_QUEUE_CAP = 20          # queue that maps to 60% of the index
CONGESTION_WAIT_CAP = 72           # wait (h) that maps to 40% of the index
DAILY_OP_COST_USD = 32_000         # mid-range public estimate for a mid/large container ship
REEFER_CONTENT_VALUE_USD = 180     # expected spoilage-risk per reefer unit per event
DEFAULT_MOVE_RATE_PER_CRANE_HOUR = 28  # mid-point of the 25-35 moves/h STS range
SERVICE_BUFFER_HOURS = 2               # mooring/unmooring + paperwork
MAX_CRANES_PER_VESSEL = 8
BERTH_TURNAROUND_HOURS = 36            # occupancy + buffer; per-zone outflow ~ berths/36 per hour
MISMATCH_RESERVE_FT = 700              # reserve long berths for ULCVs

# Alternate ports for diversion.
# Sources: great-circle distance at 15 kn; berth depths / LOA limits from published port fact sheets.
# availability: "high" = typically <24h berth wait, "medium" = 24-72h, "low" = >72h or severe congestion.
# max_berth_depth_ft: shallowest deep-sea berth at that port (limits which vessels can divert).
# congestion_index_ref: 0-100 indicative current congestion (manually calibrated; update when live feed available).
ALT_PORTS = [
    {
        "name": "Port of Oakland",
        "distance_nm": 500, "transit_hours": 33,
        "availability": "medium", "max_loa_ft": 1320,
        "max_berth_depth_ft": 50.0, "berths": 6,
        "congestion_index_ref": 35,
        "note": "Outer Harbor + Middle Harbor terminals; 50 ft depth at Berths 20-24 (Port of Oakland fact sheet).",
    },
    {
        "name": "Port of Seattle (Terminal 18/46)",
        "distance_nm": 1090, "transit_hours": 73,
        "availability": "medium", "max_loa_ft": 1312,
        "max_berth_depth_ft": 51.0, "berths": 4,
        "congestion_index_ref": 28,
        "note": "SSA Terminal 18 + TraPac T-46; 51 ft MLW depth (Port of Seattle harbour master).",
    },
    {
        "name": "Port of Tacoma (PCT/SSA)",
        "distance_nm": 1130, "transit_hours": 75,
        "availability": "low", "max_loa_ft": 1312,
        "max_berth_depth_ft": 51.0, "berths": 5,
        "congestion_index_ref": 42,
        "note": "PCT Husky Terminal + SSA Pier 2; 51 ft MLW (Northwest Seaport Alliance fact sheet).",
    },
    {
        "name": "Prince Rupert (Fairview CRT)",
        "distance_nm": 1260, "transit_hours": 84,
        "availability": "low", "max_loa_ft": 1300,
        "max_berth_depth_ft": 55.0, "berths": 3,
        "congestion_index_ref": 22,
        "note": "55 ft depth; limited berth count constrains availability (Prince Rupert Port Authority).",
    },
    {
        "name": "Port of Vancouver (DP World Centerm)",
        "distance_nm": 1150, "transit_hours": 77,
        "availability": "low", "max_loa_ft": 1200,
        "max_berth_depth_ft": 46.0, "berths": 4,
        "congestion_index_ref": 38,
        "note": "46 ft depth limits ULCV drafts; rail-connected (Vancouver Fraser Port Authority).",
    },
    {
        "name": "Port of Ensenada (ECT)",
        "distance_nm": 150, "transit_hours": 10,
        "availability": "high", "max_loa_ft": 1000,
        "max_berth_depth_ft": 45.0, "berths": 2,
        "congestion_index_ref": 12,
        "note": "Closest alternative; 45 ft depth caps at Post-Panamax (Ensenada Cruiseport Village + ECT).",
    },
    {
        "name": "Port of Manzanillo (SSA Mexico)",
        "distance_nm": 780, "transit_hours": 52,
        "availability": "high", "max_loa_ft": 1148,
        "max_berth_depth_ft": 48.0, "berths": 3,
        "congestion_index_ref": 18,
        "note": "Growing transhipment hub; 48 ft at SSA berths (ASIPONA Manzanillo).",
    },
    {
        "name": "Port of Portland (T-6)",
        "distance_nm": 1140, "transit_hours": 76,
        "availability": "high", "max_loa_ft": 964,
        "max_berth_depth_ft": 43.0, "berths": 2,
        "congestion_index_ref": 8,
        "note": "Very low congestion but 43 ft depth limits to Panamax; feeder/niche only (Port of Portland).",
    },
]
AVAILABILITY_BUFFER_HOURS = {"high": 6, "medium": 18, "low": 36}

# Composite congestion risk-score weights (doc §17): queue, utilisation, throughput variance,
# forecast uncertainty, disruption signal.
RISK_WEIGHTS = {"queue": 0.34, "utilisation": 0.24, "variance": 0.16, "uncertainty": 0.16, "disruption": 0.10}

# Nominal §17 objective weights in the spec's formula language (documentation only — NOT what
# CP-SAT minimises). The solver's actual integer constants live in services/optimiser.py and are
# returned per-run in the optimiser output's `weights` field (and persisted on OptimiserRun.weights)
# so a supervisor always sees the real numbers. Do not re-point any code at this dict.
OBJECTIVE_WEIGHTS = {"wait": 1.0, "makespan": 0.05, "crane_imbalance": 0.15, "priority_bonus": 0.10}
