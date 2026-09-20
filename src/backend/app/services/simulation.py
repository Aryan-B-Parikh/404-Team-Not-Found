"""SimPy discrete-event simulation — synthetic terminal operations layer.

Generates the vessel-call schedule and the per-zone hourly congestion series
that the forecasting and optimisation services consume, exactly as the plan
prescribes ("SimPy generates synthetic live berth/crane/yard/gate state").

Model: for each terminal, every berth is a ``simpy.Resource(capacity=1)``.
A vessel arrival process requests a berth it physically fits; the wait time is
observable; the berth is occupied for a move-rate service time; the yard fills
on discharge and drains through the gate. An hourly monitor snapshots queue
length, average anchorage wait and yard utilisation per zone.

Deterministic given ``seed`` (default 20240817). Everything it emits is
labelled ``source="DEMO_AIS"`` — the operational layer no public dataset
covers — while terminal capacities come from the REAL POLB reference table.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import simpy

from .. import reference as ref

HISTORY_HOURS = 336          # 14 days of hourly history to train on
FUTURE_HOURS = 72            # ETAs scheduled inside the forecast horizon
WARMUP_HOURS = 48            # let the queue reach steady state before recording
# Base mean inter-arrival gap. B-4 acceptance: across seeds 1-5 the median port index at
# t0 must land 40-75 (plausible mixed state, not a permanent crisis) with berth util <= 90%.
# 4.6 was deliberately crisis-prone (median index 100, 3/5 seeds pinned at the cap);
# 5.4 gives median 62.5 with max berth util 61.2% across the same seeds.
DEMAND_BASE_GAP_HOURS = 5.4
# W3: zone weights are uniform over terminals so no zone drains to zero for the last ~90h of
# history (which made the Z-TTI forecast train on a flat zero series and the anomaly detector
# misclassify it). The weights still differ slightly per terminal, just not enough to starve one.
ZONE_WEIGHTS = {"Z-LBCT": 0.28, "Z-ITS": 0.25, "Z-PCT": 0.25, "Z-TTI": 0.22}

CLASSES = [
    {"cls": "ULCV", "loa": 1312, "beam": 200, "draft": 50.5, "teu": (20000, 24000), "moves": (8500, 12500), "w": 3},
    {"cls": "POST_PANAMAX", "loa": 1148, "beam": 158, "draft": 49.0, "teu": (13000, 16000), "moves": (6000, 9000), "w": 5},
    {"cls": "NEO_PANAMAX", "loa": 1200, "beam": 168, "draft": 50.0, "teu": (15000, 16800), "moves": (6500, 9500), "w": 4},
    {"cls": "PANAMAX", "loa": 964, "beam": 124, "draft": 45.0, "teu": (5000, 6500), "moves": (3200, 4800), "w": 6},
    {"cls": "FEEDER", "loa": 636, "beam": 106, "draft": 36.0, "teu": (1800, 2800), "moves": (1200, 2200), "w": 4},
]
CARRIERS = [
    "Pacific Gateway Line", "Meridian Container Co.", "TransPacific Express",
    "Blue Harbour Shipping", "Golden Anchor Lines", "Osprey Maritime",
]
NAME_A = ["Pacific", "Meridian", "Osprey", "Golden", "Harbour", "Coral", "Trade", "Marlin",
          "Albatross", "Cobalt", "Sierra", "Aurora", "Keel", "Tidewater"]
NAME_B = ["Star", "Voyager", "Trader", "Pioneer", "Guardian", "Runner", "Banner", "Comet", "Pilot", "Crest"]
ORIGINS = ["Busan", "Shanghai", "Yokohama", "Xiamen", "Kaohsiung", "Hong Kong", "Vancouver BC",
           "Oakland", "Manzanillo", "Qingdao", "Ningbo", "Kobe"]
ANCH_ZONES = ["San Pedro Anchorage A", "San Pedro Anchorage B", "Long Beach Anchorage C",
              "Anchorage 241-243", "Outside Point Fermin (drift)"]
ZONE_WEIGHTS = {"Z-LBCT": 0.28, "Z-ITS": 0.25, "Z-PCT": 0.25, "Z-TTI": 0.22}  # no zone starves


def congestion_index(queue: float, wait_hours: float) -> float:
    """Composite index: 60% queue size (20 vessels = 60 pts) + 40% average wait (72h = 40 pts)."""
    x = 60 * (queue / ref.CONGESTION_QUEUE_CAP) + 40 * (wait_hours / ref.CONGESTION_WAIT_CAP)
    return max(0.0, min(100.0, x))


@dataclass
class BerthUnit:
    id: int
    name: str
    terminal_code: str
    zone_code: str
    pier: str
    length_ft: int
    depth_ft: float
    cranes_max: int
    resource: simpy.Resource | None = None
    free_at: float = 0.0
    busy_hours: float = 0.0


@dataclass
class VesselSpec:
    mmsi: str
    name: str
    carrier: str
    service_string: str
    vessel_class: str
    loa_ft: int
    beam_ft: int
    draft_ft: float
    teu_capacity: int
    import_moves: int
    export_moves: int
    origin_port: str
    reefer_units: int
    dest_zone_code: str
    arrival_hour: float
    waited: float = 0.0
    berthed: bool = False
    no_fit: bool = False


@dataclass
class SimResult:
    t0: datetime
    vessels: list[dict] = field(default_factory=list)
    observations: list[dict] = field(default_factory=list)
    yard_state: dict[str, list[dict]] = field(default_factory=dict)
    gate_state: dict[str, dict] = field(default_factory=dict)
    berth_stats: dict[str, dict] = field(default_factory=dict)


def _pick_class(rng: random.Random) -> dict:
    total = sum(c["w"] for c in CLASSES)
    r = rng.random() * total
    for c in CLASSES:
        r -= c["w"]
        if r <= 0:
            return c
    return CLASSES[1]


def _pick_zone(rng: random.Random) -> str:
    r = rng.random()
    for zone, w in ZONE_WEIGHTS.items():
        r -= w
        if r <= 0:
            return zone
    return "Z-LBCT"


def _build_vessel(rng: random.Random, seq: int, arrival_hour: float, zone: str) -> VesselSpec:
    c = _pick_class(rng)
    name = f"M/V {rng.choice(NAME_A)} {rng.choice(NAME_B)}"
    import_moves = int(rng.uniform(*c["moves"]))
    export_moves = int(import_moves * rng.uniform(0.8, 1.15))
    return VesselSpec(
        mmsi=str(367_000_000 + seq * 137 + rng.randint(0, 999)),
        name=name,
        carrier=rng.choice(CARRIERS),
        service_string=rng.choice(["NEU1", "TPA", "PCS", "AEX", "MSC-AM"]),
        vessel_class=c["cls"],
        loa_ft=int(c["loa"] + rng.gauss(0, 25)),
        beam_ft=c["beam"],
        draft_ft=c["draft"],
        teu_capacity=int(rng.uniform(*c["teu"])),
        import_moves=import_moves,
        export_moves=export_moves,
        origin_port=rng.choice(ORIGINS),
        reefer_units=int(rng.random() * 480),
        dest_zone_code=zone,
        arrival_hour=arrival_hour,
    )


def _generate_arrivals(rng: random.Random, total_hours: float) -> list[VesselSpec]:
    """Poisson arrivals with a diurnal arrival bank, a past bunching event, and
    a future bunching event (the demo narrative: 3 vessels within ~10h)."""
    vessels: list[VesselSpec] = []
    t = 0.0
    seq = 0
    # base mean inter-arrival ~5.5h/zone-equivalent; crisis-oversubscribed on purpose
    while t < total_hours:
        # diurnal arrival bank: more arrivals 04:00-11:00 UTC
        hod = (t % 24)
        diurnal = 1.35 if 4 <= hod <= 11 else 0.85
        mean_gap = DEMAND_BASE_GAP_HOURS / diurnal
        gap = rng.expovariate(1.0 / mean_gap)
        t += gap
        if t >= total_hours:
            break
        vessels.append(_build_vessel(rng, seq, t, _pick_zone(rng)))
        seq += 1

    # ---- past bunching event: 3 mega-vessels within 10h, ~144h before t0 (drives history spike)
    for k, zone in enumerate(["Z-LBCT", "Z-LBCT", "Z-PCT"]):
        v = _build_vessel(rng, 900 + k, (WARMUP_HOURS + HISTORY_HOURS - 144) - k * 4.0, zone)
        v.vessel_class = "ULCV"
        v.loa_ft = 1310
        v.draft_ft = 50.5
        vessels.append(v)

    # ---- future bunching event: 3 post-panamax within 10h inside the 72h horizon
    for k, zone in enumerate(["Z-LBCT", "Z-LBCT", "Z-ITS"]):
        v = _build_vessel(rng, 950 + k, (WARMUP_HOURS + HISTORY_HOURS + 30.0) + k * 4.0, zone)
        v.vessel_class = "POST_PANAMAX"
        v.loa_ft = 1148
        v.draft_ft = 49.0
        vessels.append(v)

    vessels.sort(key=lambda v: v.arrival_hour)
    return vessels


def simulate(seed: int = 20240817, t0: datetime | None = None) -> SimResult:
    """Run the SimPy simulation and return vessels + hourly observations."""
    rng = random.Random(seed)
    if t0 is None:
        t0 = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    total_hours = WARMUP_HOURS + HISTORY_HOURS + FUTURE_HOURS
    arrivals = _generate_arrivals(rng, total_hours)

    env = simpy.Environment()
    terminals: dict[str, dict] = {}
    berth_units: list[BerthUnit] = []
    for term in ref.TERMINALS:
        units: list[BerthUnit] = []
        per = term["berth_length_ft"] // term["deepsea_berths"]
        for i in range(term["deepsea_berths"]):
            cranes_max = max(2, round(term["gantry_cranes"] / term["deepsea_berths"]))
            unit = BerthUnit(
                id=len(berth_units),
                name=f"{term['code'][0]}-{i + 1}",
                terminal_code=term["code"],
                zone_code=term["zone_code"],
                pier=term["pier"],
                length_ft=per,
                depth_ft=term["depth_ft"],
                cranes_max=cranes_max,
            )
            units.append(unit)
            berth_units.append(unit)
        capacity_teu = sum(y["ground_slots_teu"] for y in term["yards"])
        terminals[term["code"]] = {
            "ref": term,
            "units": units,
            "yard_capacity": capacity_teu,
            "yard_used": capacity_teu * rng.uniform(0.45, 0.62),
            "yard_target": capacity_teu * rng.uniform(0.45, 0.62),
            "gate": term["gate"],
            "gate_queue": float(rng.randint(4, 22)),
        }

    for u in berth_units:
        u.resource = simpy.Resource(env, capacity=1)

    # PCT crane-pool collapse: ~96h ending 24h before t0. A rate-only cut cannot
    # strengthen this event: any in-window service outlasts the sim horizon, so the
    # observable signature is berth denial + queue accumulation. Duration is the knob.
    outage_start = HISTORY_HOURS + WARMUP_HOURS - 120
    outage_end = outage_start + 96

    waiting: dict[str, dict[str, float]] = {z: {} for z in ref.TERMINAL_ZONES}
    hourly: list[dict] = []

    def vessel_process(v: VesselSpec):
        if v.arrival_hour >= HISTORY_HOURS + WARMUP_HOURS:
            return  # future arrival — not simulated (scheduled inbound)
        if v.arrival_hour > env.now:
            yield env.timeout(v.arrival_hour - env.now)  # wait until the vessel actually arrives
        zone = v.dest_zone_code
        waiting[zone][v.mmsi] = env.now
        term = next(t for t in ref.TERMINALS if t["zone_code"] == zone)
        units = terminals[term["code"]]["units"]
        fitting = [u for u in units if v.loa_ft <= u.length_ft and v.draft_ft <= u.depth_ft]
        if not fitting:
            v.no_fit = True
            waiting[zone].pop(v.mmsi, None)
            return
        free = [u for u in fitting if u.resource.count == 0 and len(u.resource.queue) == 0]
        if free:
            chosen = rng.choice(free)
        else:
            chosen = min(fitting, key=lambda u: (len(u.resource.queue), u.free_at))
        req = chosen.resource.request()
        arr_t = env.now
        yield req
        v.waited = env.now - arr_t
        v.berthed = True
        waiting[zone].pop(v.mmsi, None)

        cranes = max(2, min(chosen.cranes_max, ref.MAX_CRANES_PER_VESSEL, math.ceil((v.import_moves + v.export_moves) / 900)))
        rate = ref.DEFAULT_MOVE_RATE_PER_CRANE_HOUR
        if term["code"] == "PCT" and outage_start <= env.now < outage_end:
            rate *= 0.12  # unplanned crane-pool collapse (~90% capacity lost)
        service_h = (v.import_moves + v.export_moves) / (cranes * rate) + ref.SERVICE_BUFFER_HOURS
        yield env.timeout(service_h)
        chosen.free_at = env.now
        chosen.busy_hours += service_h
        chosen.resource.release(req)
        # yard fills on discharge, gate drains continuously
        st = terminals[term["code"]]
        st["yard_used"] = min(st["yard_capacity"], st["yard_used"] + v.import_moves - v.export_moves * 0.9)

    def gate_process(code: str):
        st = terminals[code]
        gate = st["gate"]
        while True:
            yield env.timeout(1.0)
            # Gate flow is two-way and yard-managed: exports fill, imports drain, and the
            # terminal pulls inventory back toward its operating target so the yard tracks
            # a realistic 45-65% band instead of random-walking to an extreme.
            flow = gate["trucks_per_hour"] * 1.5  # TEU moved per hour through the gate
            correction = 0.10 * (st["yard_target"] - st["yard_used"])
            net = correction + rng.uniform(-0.25, 0.25) * flow
            st["yard_used"] = max(0.0, st["yard_used"] + net)
            st["gate_queue"] = max(0.0, st["gate_queue"] + rng.uniform(-6, 7))

    def monitor():
        while True:
            yield env.timeout(1.0)
            now = env.now
            if now >= WARMUP_HOURS:
                for zone in ref.TERMINAL_ZONES:
                    q = waiting[zone]
                    avg_wait = (sum(now - a for a in q.values()) / len(q)) if q else 0.0
                    term = next(t for t in ref.TERMINALS if t["zone_code"] == zone)
                    st = terminals[term["code"]]
                    yard_pct = 100.0 * st["yard_used"] / max(1.0, st["yard_capacity"])
                    hourly.append({
                        "zone_code": zone,
                        "env_hour": now,
                        "queue_count": len(q),
                        "avg_wait_hours": round(avg_wait, 2),
                        "index": round(congestion_index(len(q), avg_wait), 2),
                        "yard_util_pct": round(yard_pct, 2),
                    })

    env.process(monitor())
    for code in terminals:
        env.process(gate_process(code))
    for v in arrivals:
        env.process(vessel_process(v))

    env.run(until=HISTORY_HOURS + WARMUP_HOURS)

    # ---------------------------------------------------------- shape outputs
    t0 = t0.replace(minute=0, second=0, microsecond=0)
    # observations: keep the last HISTORY_HOURS, assign hours_ago (0 = newest)
    obs_rows: list[dict] = []
    by_zone: dict[str, list[dict]] = {z: [h for h in hourly if h["zone_code"] == z] for z in ref.TERMINAL_ZONES}
    for zone, rows in by_zone.items():
        for row in rows[-HISTORY_HOURS:]:
            hours_ago = int(round(env.now - row["env_hour"])) - 1
            if hours_ago < 0:
                continue
            ts = t0 - timedelta(hours=hours_ago)
            obs_rows.append({
                "zone_code": zone,
                "ts": ts,
                "hours_ago": hours_ago,
                "queue_count": row["queue_count"],
                "avg_wait_hours": row["avg_wait_hours"],
                "index": row["index"],
                "yard_util_pct": row["yard_util_pct"],
                "source": "DEMO_AIS",
                "is_measured": False,
                "confidence": 0.9,
            })
    # port-wide aggregate per hour (queue-weighted wait)
    port_by_hours: dict[int, list[dict]] = {}
    for r in obs_rows:
        port_by_hours.setdefault(r["hours_ago"], []).append(r)
    for hours_ago, rows in port_by_hours.items():
        q = sum(r["queue_count"] for r in rows)
        w = (sum(r["avg_wait_hours"] * r["queue_count"] for r in rows) / q) if q else 0.0
        obs_rows.append({
            "zone_code": "Z-PORT",
            "ts": t0 - timedelta(hours=hours_ago),
            "hours_ago": hours_ago,
            "queue_count": q,
            "avg_wait_hours": round(w, 2),
            "index": round(congestion_index(q, w), 2),
            "yard_util_pct": round(sum(r["yard_util_pct"] or 0 for r in rows) / len(rows), 2),
            "source": "DEMO_AIS",
            "is_measured": False,
            "confidence": 0.9,
        })

    # vessels: waiting at t0 -> ANCHORAGE/DRIFTING, future -> INBOUND
    vrows: list[dict] = []
    anchor_i = 0
    for v in arrivals:
        if v.arrival_hour < HISTORY_HOURS + WARMUP_HOURS:
            if not v.berthed and not v.no_fit:
                # still waiting at t0 (arrived but never got a berth within the run)
                anchored = (HISTORY_HOURS + WARMUP_HOURS) - v.arrival_hour
                status = "ANCHORAGE" if anchored >= 8 else "DRIFTING"
                anch_zone = ANCH_ZONES[anchor_i % len(ANCH_ZONES)]
                anchor_i += 1
                eta = 0.0
            elif v.berthed:
                continue  # already worked in the past -> not part of the current queue
            else:
                continue  # no-fit (deferred at arrival) -> skip from queue
        else:
            # future arrival inside the horizon -> scheduled inbound
            eta = v.arrival_hour - (HISTORY_HOURS + WARMUP_HOURS)
            if eta < 1 or eta > FUTURE_HOURS:
                continue
            anchored = 0.0
            status = "INBOUND"
            anch_zone = "En route — San Pedro Approach"

        declared = round(float(eta), 1)
        # AIS-derived ETA exists for a subset of inbound vessels, with small disagreement
        ais_eta = None
        if status == "INBOUND" and rng.random() < 0.6:
            ais_eta = round(max(0.5, declared + rng.gauss(0, 2.5)), 1)
        vrows.append({
            "mmsi": v.mmsi,
            "imo": f"IMO9{v.mmsi[-6:]}",
            "voyage_number": f"{v.service_string}-{str(v.arrival_hour)[:2]}{int(v.arrival_hour) % 24:02d}",
            "name": v.name,
            "carrier": v.carrier,
            "service_string": v.service_string,
            "vessel_class": v.vessel_class,
            "loa_ft": v.loa_ft,
            "beam_ft": v.beam_ft,
            "draft_ft": v.draft_ft,
            "teu_capacity": v.teu_capacity,
            "import_moves": v.import_moves,
            "export_moves": v.export_moves,
            "origin_port": v.origin_port,
            "reefer_units": v.reefer_units,
            "status": status,
            "anchorage_zone": anch_zone,
            "declared_eta_hours": declared,
            "ais_eta_hours": ais_eta,
            "etd_hours": round(declared + 26 + rng.random() * 20, 1) if status == "INBOUND" else None,
            "anchored_hours": round(anchored, 1),
            "dest_zone_code": v.dest_zone_code,
            "data_confidence": 1.0,
            "unresolved": False,
        })

    yard_state = {
        code: [
            {**y, "used_teu": int(st["yard_used"] * y["ground_slots_teu"] / st["yard_capacity"])}
            for y in st["ref"]["yards"]
        ]
        for code, st in terminals.items()
    }
    gate_state = {
        code: {**st["gate"], "queue_len": int(round(st["gate_queue"]))}
        for code, st in terminals.items()
    }
    berth_stats = {
        f"{u.terminal_code}:{u.name}": {
            "terminal_code": u.terminal_code,
            "berth_name": u.name,
            "length_ft": u.length_ft,
            "depth_ft": u.depth_ft,
            "cranes_max": u.cranes_max,
            "busy_hours": round(u.busy_hours, 1),
        }
        for u in berth_units
    }
    return SimResult(t0=t0, vessels=vrows, observations=obs_rows, yard_state=yard_state,
                     gate_state=gate_state, berth_stats=berth_stats)
