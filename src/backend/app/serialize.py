"""Small serialization helpers (dataclasses -> JSON-friendly dicts)."""

from __future__ import annotations


def point_to_dict(p) -> dict:
    return {"hour": p.hour, "ts": p.ts.isoformat(), "index": p.index, "queue": p.queue,
            "wait": p.wait, "yard_util": p.yard_util, "lo": p.lo, "hi": p.hi}


def forecast_to_dict(fc) -> dict:
    return {
        "zone_code": fc.zone_code, "zone_name": fc.zone_name,
        "current": fc.current, "peak": fc.peak, "avg_index": fc.avg_index,
        "points": [point_to_dict(p) for p in fc.points],
        "drivers": fc.drivers, "model": fc.model, "validation": fc.validation,
        "capacity": fc.capacity,
    }


def vessel_to_dict(v) -> dict:
    return {"id": v.id, "mmsi": v.mmsi, "imo": v.imo, "name": v.name, "carrier": v.carrier,
            "vessel_class": v.vessel_class, "loa_ft": v.loa_ft, "beam_ft": v.beam_ft,
            "draft_ft": v.draft_ft, "teu_capacity": v.teu_capacity, "import_moves": v.import_moves,
            "export_moves": v.export_moves, "origin_port": v.origin_port, "reefer_units": v.reefer_units,
            "status": v.status, "anchorage_zone": v.anchorage_zone,
            "declared_eta_hours": v.declared_eta_hours, "ais_eta_hours": v.ais_eta_hours,
            "eta_hours": v.eta_hours, "anchored_hours": v.anchored_hours,
            "dest_zone_code": v.dest_zone_code, "data_confidence": v.data_confidence,
            "unresolved": v.unresolved}


def terminal_to_dict(t, berths, cranes, yards, gate) -> dict:
    return {"code": t.code, "name": t.name, "pier": t.pier, "lat": t.lat, "lon": t.lon,
            "berth_length_ft": t.berth_length_ft, "deepsea_berths": t.deepsea_berths,
            "gantry_cranes": t.gantry_cranes, "capacity_teu_m": t.capacity_teu_m,
            "zone_code": t.zone_code, "note": t.note,
            "berths": berths, "cranes": cranes, "yard_zones": yards, "gate": gate}
