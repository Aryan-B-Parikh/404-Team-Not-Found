"""Hotspot / bottleneck detector with resource-specific operational evidence."""

from __future__ import annotations

import numpy as np

from .. import reference as ref

_GATE_TPH = {t["code"]: float(t.get("gate", {}).get("trucks_per_hour") or 120.0) for t in ref.TERMINALS}
_MOVE_RATE = ref.DEFAULT_MOVE_RATE_PER_CRANE_HOUR


def _pressure(ctx, zone_code: str, fpoint) -> dict[str, float]:
    """Calculate capacity pressure from forecast queue + known vessel workload.

    When vessel-level moves are available, berth/crane pressure is calculated from
    actual move workload. When a forecast contains no vessel-level horizon mapping,
    the forecast queue itself is the observed workload signal and is normalised
    against berth count and available crane capacity. This prevents an empty vessel
    catalogue from falsely reporting zero pressure.
    """
    term = next((t for t in ctx.terminals if t.zone_code == zone_code), None)
    berths = [b for b in ctx.berths if b.zone_code == zone_code]
    available_cranes = ctx.cranes.get(term.code, 0) if term else 0
    if available_cranes <= 0:
        available_cranes = sum(b.cranes_max for b in berths)
    horizon_h = max(1.0, float(fpoint.hour))
    incoming = [v for v in ctx.vessels if v.dest_zone_code == zone_code and v.eta_hours <= fpoint.hour and not v.unresolved]
    if incoming:
        work_hours = sum(v.total_moves / (3.0 * _MOVE_RATE) for v in incoming)
        berth = min(1.0, work_hours / max(1.0, len(berths) * horizon_h))
        crane = min(1.0, work_hours / max(1.0, available_cranes * horizon_h))
    else:
        queue = max(0.0, float(fpoint.queue))
        berth = min(1.0, queue / max(1.0, len(berths) * 3.5))
        crane = min(1.0, (queue * 3.0) / max(1.0, available_cranes))
    yard = min(1.0, max(0.0, float(fpoint.yard_util or 0.0)) / 100.0)
    gate_q = ctx.gate_queue.get(term.code, 0) if term else 0
    gate = min(1.0, gate_q / max(1.0, _GATE_TPH.get(term.code, 120.0)) if term else 0.0)
    return {"BERTH": berth, "CRANE": crane, "YARD": yard, "GATE": gate}


def compute_hotspots(ctx, forecasts: dict, anomalies: list[dict]) -> dict:
    """Rank zones and identify the resource with the strongest capacity pressure."""
    anom_by_zone = {a["zone_code"]: a for a in anomalies}
    ranked: list[dict] = []
    for zone_code, fc in forecasts.items():
        if zone_code == "Z-PORT":
            continue
        peak = max(fc.points, key=lambda p: p.index)
        recent = ctx.history.get(zone_code, [])[-24:]
        idx_std = float(np.std([h.index for h in recent])) if recent else 0.0
        press = _pressure(ctx, zone_code, peak)
        order = sorted(press.items(), key=lambda kv: kv[1], reverse=True)
        binding, binding_p = order[0]
        runner_up, runner_up_p = order[1] if len(order) > 1 else (None, 0.0)
        anom = anom_by_zone.get(zone_code)
        disruption = 1.0 if (anom and anom["is_anomaly"]) else 0.0
        band = max(0.0, peak.hi - peak.lo)
        comp = {
            "queue": min(1.0, peak.queue / max(1.0, ref.CONGESTION_QUEUE_CAP)),
            "utilisation": max(press.values()), "variance": min(1.0, idx_std / 25.0),
            "uncertainty": min(1.0, band / 100.0), "disruption": disruption,
        }
        w = ref.RISK_WEIGHTS
        risk = 100.0 * sum(w[k] * comp[k] for k in w)
        data_conf = 0.9
        if len(recent) < 48: data_conf -= 0.25
        if anom and anom["kind"] == "DATA_ERROR": data_conf -= 0.2
        if any(v.unresolved for v in ctx.vessels if v.dest_zone_code == zone_code): data_conf -= 0.1
        confidence = 0.5 * float(getattr(fc, "confidence", 0.8) or 0.8) + 0.5 * max(0.3, data_conf)
        terminal_code = next((t.code for t in ctx.terminals if t.zone_code == zone_code), None)
        incoming_count = len([v for v in ctx.vessels if v.dest_zone_code == zone_code and v.eta_hours <= peak.hour and not v.unresolved])
        ranked.append({
            "zone_code": zone_code, "zone_name": fc.zone_name, "peak_hour": peak.hour,
            "peak_index": peak.index, "risk_score": round(risk, 1), "binding_constraint": binding,
            "resource_pressure": {k: round(v, 3) for k, v in press.items()},
            "binding_evidence": {"resource": binding, "pressure": round(binding_p, 3),
                                 "runner_up": runner_up, "runner_up_pressure": round(runner_up_p, 3),
                                 "margin": round(binding_p - runner_up_p, 3),
                                 "gate_throughput_ref_tph": _GATE_TPH.get(terminal_code),
                                 "incoming_vessels_by_peak": incoming_count},
            "components": {k: round(v, 3) for k, v in comp.items()}, "weights": w,
            "confidence": round(max(0.05, min(0.98, confidence)), 2),
            "explanation": (f"Risk {risk:.0f}/100 at +{peak.hour}h; binding resource = {binding} "
                            f"(capacity pressure {binding_p:.2f}, margin {binding_p - runner_up_p:+.2f} over {runner_up}). "
                            + (f"Disruption signal: {anom['kind']}." if disruption else "No disruption signal.")),
        })
    ranked.sort(key=lambda r: r["risk_score"], reverse=True)
    return {"ranked": ranked, "most_actionable": ranked[0] if ranked else None,
            "method": "composite risk score + capacity/workload pressure attribution"}
