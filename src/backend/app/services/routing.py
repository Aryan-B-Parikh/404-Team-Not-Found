"""Alternate routing / diversion recommender with explicit live-data gating.

In-port alternatives are driven by the application's live forecast/optimiser state.
External-port diversion is only eligible when a current port-status feed is supplied
through PORT_STATUS_JSON; the static reference table is used only for physical
feasibility and published reference metadata, never for pretending current berth
availability or congestion is live.
"""

from __future__ import annotations

import json
import os

from .. import reference as ref

DIVERT_WAIT_H = 48.0
SLOW_STEAM_WAIT_H = 18.0
PRIORITY_WAIT_H = 10.0
REEFFER_PRIORITY_MIN = 200
SUSTAINED_HOURS = 3


def _live_port_status() -> dict[str, dict]:
    """Read an operator-provided current external-port feed.

    Format: {"Port of Oakland": {"availability": "medium", "wait_hours": 18,
    "updated_at": "..."}}. Missing/malformed feeds return {} so no external
    diversion is recommended from stale constants.
    """
    raw = os.environ.get("PORT_STATUS_JSON", "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        out = {}
        for name, value in data.items():
            if not isinstance(value, dict):
                continue
            availability = str(value.get("availability", "")).lower()
            wait = float(value.get("wait_hours"))
            if availability not in {"high", "medium", "low"} or wait < 0:
                continue
            out[str(name)] = {**value, "availability": availability, "wait_hours": wait}
        return out
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _predicted_wait(ctx, forecasts, assignment_by_vessel, v) -> tuple[float, bool]:
    a = assignment_by_vessel.get(v.id)
    zone = a["zone_code"] if a else v.dest_zone_code
    fc = forecasts.get(zone) or forecasts.get("Z-PORT")
    if fc is None:
        return v.anchored_hours, False
    start = int(max(1, min(72, round(a["start_hour"] if a else max(1, v.eta_hours)))))
    wait = fc.points[start - 1].wait
    segment = fc.points[start - 1:start - 1 + SUSTAINED_HOURS]
    sustained = len(segment) == SUSTAINED_HOURS and all(p.wait >= DIVERT_WAIT_H for p in segment)
    if a is None:
        return max(wait, 78.0), True
    return wait, sustained


def _best_window(fc) -> tuple[int, float] | None:
    if not fc or not fc.points:
        return None
    p = min(fc.points, key=lambda x: x.wait)
    return p.hour, p.wait


def _best_in_port_alternative(ctx, forecasts: dict, v, current_wait: float, min_saving_h: float = 12.0):
    best = None
    for zone, fc in forecasts.items():
        if zone == "Z-PORT" or zone == v.dest_zone_code:
            continue
        fits = [b for b in ctx.berths if b.zone_code == zone and v.loa_ft <= b.length_ft and v.draft_ft <= b.depth_ft]
        if not fits:
            continue
        w = _best_window(fc)
        if not w:
            continue
        wait_alt = w[1]
        if current_wait - wait_alt >= min_saving_h and (best is None or wait_alt < best[1]):
            best = (zone, wait_alt, round(current_wait - wait_alt, 1))
    return best


def _option_detail(ctx, forecasts: dict, v, wait: float, rule: str) -> dict:
    fc = forecasts.get(v.dest_zone_code) or forecasts.get("Z-PORT")
    window = _best_window(fc)
    alt = _best_in_port_alternative(ctx, forecasts, v, wait)
    return {
        "rule": rule,
        "berthing_window": ({"hour": window[0], "wait_hours": round(window[1], 1)} if window else None),
        "alternate_terminal": ({"zone_code": alt[0], "wait_hours": round(alt[1], 1), "savings_hours": alt[2]} if alt else None),
    }


def recommend_routing(ctx, forecasts: dict, optimiser_out: dict | None) -> list[dict]:
    assignment_by_vessel = {a["vessel_id"]: a for a in (optimiser_out or {}).get("assignments", [])}
    live_ports = _live_port_status()
    recs: list[dict] = []

    for v in ctx.vessels:
        wait, sustained = _predicted_wait(ctx, forecasts, assignment_by_vessel, v)
        base = {"vessel_id": v.id, "vessel_name": v.name, "carrier": v.carrier,
                "vessel_class": v.vessel_class, "dest_zone_code": v.dest_zone_code,
                "status": v.status, "predicted_wait_hours": round(wait, 1)}

        def _detail(rule: str) -> dict:
            return _option_detail(ctx, forecasts, v, wait, rule)

        if wait >= DIVERT_WAIT_H and sustained:
            candidates = []
            for p in ref.ALT_PORTS:
                live = live_ports.get(p["name"])
                if not live:
                    continue
                if v.loa_ft > p["max_loa_ft"] or v.draft_ft > p.get("max_berth_depth_ft", 55.0):
                    continue
                candidates.append((p, live))
            best = None
            for p, live in candidates:
                live_wait = float(live["wait_hours"])
                transit = float(p["transit_hours"])
                shift = transit + live_wait
                wait_avoided = max(0.0, wait - shift)
                savings = ((wait_avoided / 24) * ref.DAILY_OP_COST_USD
                            - (shift / 24) * ref.DAILY_OP_COST_USD * 0.35)
                if best is None or savings > best[1]:
                    best = (p, live, savings, shift, wait_avoided)
            if best and best[2] > 0:
                p, live, savings, shift, wait_avoided = best
                recs.append({**base, "option": "DIVERT", "target_port": p["name"],
                             "eta_shift_hours": round(shift, 1), "est_savings_usd": round(savings),
                             "confidence": 0.9, "tier": "critical", "sustained": True,
                             "option_detail": _detail("divert: sustained forecast + live external port status"),
                             "rationale": (f"Predicted {wait:.0f}h wait; live feed reports {live['wait_hours']:.0f}h at {p['name']} "
                                           f"with {live['availability']} availability. Estimated net savings ≈ ${round(savings):,}.")})
                continue

        if SLOW_STEAM_WAIT_H <= wait < DIVERT_WAIT_H and v.status == "INBOUND":
            steam_down = min(wait - 6, 48)
            savings = 0.35 * (steam_down / 24) * ref.DAILY_OP_COST_USD
            recs.append({**base, "option": "SLOW_STEAM", "target_port": None, "eta_shift_hours": round(steam_down, 1),
                         "est_savings_usd": round(savings), "confidence": 0.72, "tier": "high", "sustained": sustained,
                         "option_detail": _detail("slow-steam: 18h<=wait<48h and INBOUND"),
                         "rationale": f"Inbound with predicted {wait:.0f}h queue; slow-steam to target the forecast opening window. Estimated operating saving ≈ ${round(savings):,}."})
            continue

        if wait >= PRIORITY_WAIT_H and v.reefer_units >= REEFFER_PRIORITY_MIN:
            savings = v.reefer_units * ref.REEFER_CONTENT_VALUE_USD * 0.4
            recs.append({**base, "option": "PRIORITY_WINDOW", "target_port": None,
                         "eta_shift_hours": -min(6, wait - 8), "est_savings_usd": round(savings),
                         "confidence": 0.64, "tier": "medium", "sustained": sustained,
                         "option_detail": _detail("priority window: wait>=10h and >=200 reefers"),
                         "rationale": f"{v.reefer_units} reefer units with {wait:.0f}h predicted wait; prioritise the vessel to reduce spoilage exposure."})
            continue

        recs.append({**base, "option": "HOLD", "target_port": None, "eta_shift_hours": 0, "est_savings_usd": 0,
                     "confidence": 0.55, "tier": "low", "sustained": sustained,
                     "option_detail": _detail("hold: within normal rotation or no validated external alternative"),
                     "rationale": (f"Predicted {wait:.0f}h wait within normal rotation — hold current schedule."
                                   if wait < PRIORITY_WAIT_H else
                                   f"Predicted {wait:.0f}h wait but no validated live external alternative; hold and re-evaluate next cycle.")})

    tier_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    recs.sort(key=lambda r: (tier_rank[r["tier"]], -r["est_savings_usd"]))
    return recs
