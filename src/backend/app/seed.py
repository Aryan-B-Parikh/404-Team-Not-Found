"""Database seed: REAL POLB reference data + the SimPy synthetic operations layer.

    uv run python -m app.seed [--reset]

Wipes and repopulates terminals / berths / cranes / yard zones / gates from the
REAL Port of Long Beach fact-sheet table, then generates the vessel queue,
ETA-revision history and 14-day hourly congestion series with the SimPy
simulation (labelled source="DEMO_AIS").
"""

from __future__ import annotations

import sys

from sqlalchemy import delete, select

from . import reference as ref
from .db import SessionLocal, ensure_schema
from .models import (
    AnomalyFlag,
    Assignment,
    Berth,
    ChatMessage,
    CongestionObservation,
    Crane,
    EtaRevision,
    ForecastPoint,
    ForecastRun,
    Gate,
    HotspotFlag,
    ImpactAssessment,
    OperationsPlan,
    OptimiserRun,
    RoutingRecommendation,
    Scenario,
    Terminal,
    VesselCall,
    YardZone,
)
from .services.simulation import congestion_index, simulate


def _clear(db) -> None:
    for model in (ImpactAssessment, Scenario, RoutingRecommendation, Assignment, OptimiserRun,
                  HotspotFlag, ForecastPoint, ForecastRun, OperationsPlan, AnomalyFlag, ChatMessage,
                  EtaRevision, VesselCall, CongestionObservation, Gate, YardZone, Crane, Berth, Terminal):
        db.execute(delete(model))
    db.commit()


def seed(reset: bool = False) -> None:
    ensure_schema()
    db = SessionLocal()
    try:
        if not reset:
            # If terminals already exist, skip re-seeding to preserve live data.
            existing = db.execute(select(Terminal)).scalars().first()
            if existing:
                print("Seed skipped — data already present (use --reset to wipe and re-seed).")
                return
        _clear(db)

        # ---------------------------------------------------------- REAL terminals
        terminal_by_code: dict[str, Terminal] = {}
        for t in ref.TERMINALS:
            term = Terminal(
                code=t["code"], name=t["name"], pier=t["pier"], lat=t["lat"], lon=t["lon"],
                berth_length_ft=t["berth_length_ft"], deepsea_berths=t["deepsea_berths"],
                gantry_cranes=t["gantry_cranes"], capacity_teu_m=t["capacity_teu_m"],
                zone_code=t["zone_code"], note=t["note"], config_version=1,
            )
            db.add(term)
            db.flush()
            terminal_by_code[t["code"]] = term

            # berths (published totals split into working berths)
            per = t["berth_length_ft"] // t["deepsea_berths"]
            for i in range(t["deepsea_berths"]):
                db.add(Berth(terminal_id=term.id, name=f"{t['code'][0]}-{i + 1}", seq=i + 1,
                             length_ft=per, depth_ft=t["depth_ft"],
                             cranes_max=max(2, round(t["gantry_cranes"] / t["deepsea_berths"]))))

            # crane inventory (per-crane reach + rated moves/h; maintenance vs available)
            for c in range(t["gantry_cranes"]):
                maintenance = (t["code"] == "PCT" and c >= t["gantry_cranes"] - 1)  # 1 PCT crane under maintenance
                db.add(Crane(
                    terminal_id=term.id, code=f"{t['code']}-STS-{c + 1:02d}",
                    crane_type="dual-hoist" if t["code"] == "LBCT" else "STS",
                    reach_ft=210.0 if t["code"] != "LBCT" else 224.0,
                    rated_moves_per_hour=32.0 if t["code"] == "LBCT" else 28.0,
                    status="MAINTENANCE" if maintenance else "AVAILABLE",
                    status_reason="planned maintenance" if maintenance else None,
                ))

            # yard zones
            for y in t["yards"]:
                db.add(YardZone(terminal_id=term.id, code=y["code"],
                                ground_slots_teu=y["ground_slots_teu"], reefer_plugs=y["reefer_plugs"], used_teu=0))

            # gate
            db.add(Gate(terminal_id=term.id, lanes=t["gate"]["lanes"],
                        trucks_per_hour=t["gate"]["trucks_per_hour"], queue_len=0,
                        open_hours=t["gate"]["open_hours"]))
        db.commit()
        print(f"  terminals: {len(ref.TERMINALS)}  berths: {sum(t['deepsea_berths'] for t in ref.TERMINALS)}  "
              f"cranes: {sum(t['gantry_cranes'] for t in ref.TERMINALS)}")

        # ---------------------------------------------------------- SimPy layer
        sim = simulate(seed=ref.__dict__.get("SIM_SEED", 20240817))
        print(f"  simulation: {len(sim.vessels)} vessel calls, {len(sim.observations)} hourly observations (t0={sim.t0.isoformat()})")

        # yard + gate live state produced by the simulation
        for code, zones in sim.yard_state.items():
            term = terminal_by_code[code]
            db.execute(delete(YardZone).where(YardZone.terminal_id == term.id))
            for y in zones:
                db.add(YardZone(terminal_id=term.id, code=y["code"], ground_slots_teu=y["ground_slots_teu"],
                                reefer_plugs=y["reefer_plugs"], used_teu=int(y["used_teu"])))
        for code, g in sim.gate_state.items():
            term = terminal_by_code[code]
            db.execute(delete(Gate).where(Gate.terminal_id == term.id))
            db.add(Gate(terminal_id=term.id, lanes=g["lanes"], trucks_per_hour=g["trucks_per_hour"],
                        queue_len=g["queue_len"], open_hours=g["open_hours"]))
        db.commit()

        # vessels + ETA revision history
        for v in sim.vessels:
            vc = VesselCall(
                imo=v["imo"], voyage_number=v["voyage_number"], mmsi=v["mmsi"], name=v["name"], carrier=v["carrier"],
                service_string=v["service_string"], vessel_class=v["vessel_class"], loa_ft=v["loa_ft"],
                beam_ft=v["beam_ft"], draft_ft=v["draft_ft"], teu_capacity=v["teu_capacity"],
                import_moves=v["import_moves"], export_moves=v["export_moves"], origin_port=v["origin_port"],
                reefer_units=v["reefer_units"], status=v["status"], anchorage_zone=v["anchorage_zone"],
                declared_eta_hours=v["declared_eta_hours"], ais_eta_hours=v["ais_eta_hours"],
                etd_hours=v["etd_hours"], anchored_hours=v["anchored_hours"],
                dest_zone_code=v["dest_zone_code"], unresolved=bool(v["unresolved"]),
                data_confidence=v["data_confidence"],
            )
            db.add(vc)
            db.flush()
            # ETA revision history: carrier declaration + optional AIS revision (B req.)
            db.add(EtaRevision(vessel_call_id=vc.id, source="CARRIER", eta_hours=v["declared_eta_hours"],
                               note="initial carrier-declared ETA"))
            if v["ais_eta_hours"] is not None:
                db.add(EtaRevision(vessel_call_id=vc.id, source="AIS", eta_hours=v["ais_eta_hours"],
                                   note="AIS-derived ETA revision"))
        db.commit()
        waiting = sum(1 for v in sim.vessels if v["status"] != "INBOUND")
        print(f"  vessels: {len(sim.vessels)} ({waiting} waiting, {len(sim.vessels) - waiting} inbound)")

        # hourly congestion observations
        rows = [CongestionObservation(
            zone_code=o["zone_code"], ts=o["ts"], hours_ago=o["hours_ago"], queue_count=o["queue_count"],
            avg_wait_hours=o["avg_wait_hours"], index=o["index"], yard_util_pct=o["yard_util_pct"],
            source=o["source"], is_measured=o["is_measured"], confidence=o["confidence"],
        ) for o in sim.observations]
        db.add_all(rows)
        db.commit()
        print(f"  congestion history: {len(rows)} rows across {len(set(o['zone_code'] for o in sim.observations))} zones")

        # sanity: index formula from the same definition used everywhere
        z = next(o for o in sim.observations if o["zone_code"] == "Z-PORT")
        assert abs(z["index"] - congestion_index(z["queue_count"], z["avg_wait_hours"])) < 0.05
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed(reset="--reset" in sys.argv)
