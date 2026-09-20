"""72-hour port operations plan generator (12 x 6h shifts).

Module K: fuses forecast + assignments + routing into a shift-by-shift plan with
arrivals, berthings, crane deployment, congestion alerts, routing decide-by
deadlines and a supervisor checklist; emits JSON + printable text and cites the
forecast/optimiser run ids and model version for auditability.
"""

from __future__ import annotations

from datetime import timedelta

from .. import reference as ref

SHIFT_LEN = 6
NUM_SHIFTS = 12


def _fmt(ts) -> str:
    return ts.strftime("%m/%d %H:%MZ")


def _confidence_by_bucket(port_fc) -> dict:
    """Per-horizon confidence from the forecast's own validation buckets (W3).

    Blends the holdout-style MAE with the forecast σ (the band-width driver):
    ``confidence = 1 - clamp((MAE + σ) / 40, 0, 1)`` — so it degrades with horizon
    instead of reporting a flat "99%" just because the level is near-constant.
    """
    out: dict[str, float] = {}
    for b in (getattr(port_fc, "validation", None) or {}).get("buckets", []):
        mae = float(b.get("mae") or 0.0)
        sigma = float(b.get("sigma") or 0.0)
        out[str(b["label"])] = round(1 - min(1.0, (mae + sigma) / 40.0), 2)
    return out


def build_plan(ctx, forecasts: dict, optimiser_out: dict, routing: list[dict],
               forecast_run_id: int | None = None, optimiser_run_id: int | None = None,
               model_version: str | None = None) -> dict:
    t0 = ctx.t0
    assignments = optimiser_out.get("assignments", [])
    vessel_by_id = {v.id: v for v in ctx.vessels}
    port_fc = forecasts["Z-PORT"]
    confidence_by_bucket = _confidence_by_bucket(port_fc)      # W3: per-horizon confidence

    shifts = []
    total_crane_hours = 0.0
    total_moves = 0.0

    for s in range(NUM_SHIFTS):
        start_h, end_h = s * SHIFT_LEN, (s + 1) * SHIFT_LEN
        in_win = lambda h: start_h < h <= end_h  # noqa: E731

        arrivals = [
            {"vessel_name": v.name, "carrier": v.carrier, "zone_code": v.dest_zone_code,
             "eta_hour": round(v.eta_hours, 1)}
            for v in ctx.vessels if v.status == "INBOUND" and in_win(v.eta_hours)
        ]
        arrivals.sort(key=lambda a: a["eta_hour"])

        berthings = [
            {"vessel_name": a["vessel_name"], "berth_name": f"{a['pier']} {a['berth_name']}",
             "terminal_code": a["terminal_code"], "start_hour": a["start_hour"], "cranes": a["cranes"]}
            for a in assignments if in_win(a["start_hour"])
        ]
        berthings.sort(key=lambda b: b["start_hour"])

        crane_dep: dict[str, float] = {}
        for a in assignments:
            overlap = max(0.0, min(a["end_hour"], end_h) - max(a["start_hour"], start_h))
            if overlap <= 0:
                continue
            crane_dep[a["terminal_code"]] = crane_dep.get(a["terminal_code"], 0.0) + a["cranes"] * (overlap / SHIFT_LEN)
            total_crane_hours += a["cranes"] * overlap
            total_moves += a["moves"] * (overlap / max(1e-6, a["end_hour"] - a["start_hour"]))
        crane_dep_int = {k: int(round(v)) for k, v in crane_dep.items()}

        alerts = []
        for zone, fc in forecasts.items():
            if zone == "Z-PORT":
                continue
            seg = [p for p in fc.points if start_h < p.hour <= end_h]
            if not seg:
                continue
            peak = max(seg, key=lambda p: p.index)
            level = "CRIT" if peak.index >= 75 else "WARN" if peak.index >= 60 else "WATCH" if peak.index >= 45 else None
            if level:
                alerts.append({"zone_code": zone, "peak_index": peak.index, "peak_hour": peak.hour, "level": level})
        alerts.sort(key=lambda a: -a["peak_index"])

        routing_actions = []
        for r in routing:
            v = vessel_by_id.get(r["vessel_id"])
            if v is None or r["option"] == "HOLD":
                continue
            decide_by = max(1, round(v.eta_hours - (12 if r["option"] == "DIVERT" else 4)))
            if in_win(decide_by):
                if r["option"] == "DIVERT":
                    routing_actions.append(f"FINALISE by +{decide_by:02d}h: divert {r['vessel_name']} → {r['target_port']} (est. save ${r['est_savings_usd']:,}).")
                elif r["option"] == "SLOW_STEAM":
                    routing_actions.append(f"ORDER by +{decide_by:02d}h: {r['vessel_name']} slow-steam to +{r['eta_shift_hours']}h arrival (save ${r['est_savings_usd']:,}).")
                else:
                    routing_actions.append(f"GRANT by +{decide_by:02d}h: {r['vessel_name']} priority window ({v.reefer_units} reefers aboard).")

        checklist = []
        if arrivals:
            checklist.append(f"Confirm VTS queue position for {len(arrivals)} arriving vessel(s).")
        if berthings:
            checklist.append("Line-handlers & tugs booked for " + ", ".join(f"{b['vessel_name']} @ {b['berth_name']}" for b in berthings) + ".")
        reefers = [a["vessel_name"] for a in assignments if in_win(a["start_hour"])
                   and vessel_by_id.get(a["vessel_id"]) and vessel_by_id[a["vessel_id"]].reefer_units > 200]
        if reefers:
            checklist.append("Stage reefer monitoring for: " + ", ".join(reefers) + ".")
        for ca in alerts[:2]:
            checklist.append(f"Watch {ref.ZONE_LABELS.get(ca['zone_code'], ca['zone_code'])}: index peak {ca['peak_index']:.0f} @ +{ca['peak_hour']}h — {'prep contingency berthing' if ca['level'] == 'CRIT' else 'verify crane gangs'}.")
        if not checklist:
            checklist.append("No special actions — routine rotation and crane maintenance windows apply.")

        import_h = sum(vessel_by_id[a["vessel_id"]].import_moves for a in assignments
                       if in_win(a["start_hour"]) and a["vessel_id"] in vessel_by_id)
        yard_note = (f"Heavy discharge window (~{round(import_h / 1000)}k import TEU) — pre-stage yard blocks & extra hostlers."
                     if import_h > 9000 else None)

        shifts.append({
            "seq": s + 1,
            "label": f"Shift {s + 1:02d} · +{start_h}h → +{end_h}h",
            "start_hour": start_h, "end_hour": end_h,
            "window_label": f"{_fmt(t0 + timedelta(hours=start_h))} → {_fmt(t0 + timedelta(hours=end_h))}",
            "arrivals": arrivals, "berthings": berthings, "crane_deployment": crane_dep_int,
            "congestion_alerts": alerts, "routing_actions": routing_actions,
            "checklist": checklist, "yard_note": yard_note,
        })

    peak = max(port_fc.points, key=lambda p: p.index)
    peak_zone = max((f for f in forecasts.values() if f.zone_code != "Z-PORT"),
                    key=lambda f: f.peak["index"])
    occupied = sum(max(0.0, min(a["end_hour"], 72) - min(a["start_hour"], 72)) for a in assignments)
    idle_pct = round((1 - occupied / (len(ctx.berths) * 72)) * 100, 1)
    risk = "SEVERE" if peak.index >= 80 else "HIGH" if peak.index >= 65 else "ELEVATED" if peak.index >= 45 else "LOW"

    top_actions = [a for s in shifts for a in s["routing_actions"]][:3]
    top_actions.append(f"Monitor port-wide peak index {peak.index:.0f} at +{peak.hour}h; trigger contingency plan if revised ≥ 80.")

    summary = {
        "generated_at": t0.isoformat(),
        "horizon_hours": 72,
        "total_arrivals": sum(len(s["arrivals"]) for s in shifts),
        "total_berthings": sum(len(s["berthings"]) for s in shifts),
        "total_moves": int(round(total_moves)),
        "crane_hours": int(round(total_crane_hours)),
        "peak_index": round(peak.index, 1),
        "peak_zone": peak_zone.zone_code,
        "risk_level": risk,
        "top_actions": top_actions[:4],
        "idle_berth_hours_pct": max(0.0, idle_pct),
        "deferred_count": len(optimiser_out.get("deferred", [])),
        "confidence_by_bucket": confidence_by_bucket,
        # auditability (K req.): which runs produced this plan
        "forecast_run_id": forecast_run_id,
        "optimiser_run_id": optimiser_run_id,
        "model_version": model_version,
    }
    text = render_text(summary, shifts)
    return {"summary": summary, "shifts": shifts, "text": text}


def render_text(summary: dict, shifts: list[dict]) -> str:
    line = "─" * 78
    L = [line, "SAN PEDRO BAY — 72-HOUR PORT OPERATIONS PLAN",
         f"Generated: {summary['generated_at']}   |   Risk: {summary['risk_level']}",
         f"Arrivals: {summary['total_arrivals']}   Berthings: {summary['total_berthings']}   "
         f"Moves: {summary['total_moves']:,} TEU   Crane-hours: {summary['crane_hours']:,}",
         f"Idle berth-hours: {summary['idle_berth_hours_pct']}%   Deferred: {summary['deferred_count']}   "
         f"Peak index: {summary['peak_index']} ({summary['peak_zone']})",
         f"Source runs: forecast #{summary['forecast_run_id']} / optimiser #{summary['optimiser_run_id']} "
         f"| model {summary['model_version']}", line]
    for s in shifts:
        L.append("")
        L.append(f"{s['label']}   [{s['window_label']}]")
        if s["arrivals"]:
            L.append("  Arrivals : " + ", ".join(f"{a['vessel_name'].replace('M/V ', '')}→{a['zone_code'].replace('Z-', '')}@+{a['eta_hour']}h" for a in s["arrivals"]))
        else:
            L.append("  Arrivals : none")
        for b in s["berthings"]:
            L.append(f"  Berth    : {b['vessel_name']} → {b['berth_name']} ({b['terminal_code']}) @ +{b['start_hour']}h w/ {b['cranes']} cranes")
        if s["crane_deployment"]:
            L.append("  Cranes   : " + "  ".join(f"{k}={v}" for k, v in s["crane_deployment"].items()))
        for a in s["congestion_alerts"]:
            L.append(f"  ALERT    : [{a['level']}] {a['zone_code']} peak {a['peak_index']:.0f} @ +{a['peak_hour']}h")
        for r in s["routing_actions"]:
            L.append(f"  ROUTE    : {r}")
        if s["yard_note"]:
            L.append(f"  YARD     : {s['yard_note']}")
        L.append("  Checklist:")
        for c in s["checklist"]:
            L.append(f"    □ {c}")
    L += ["", line,
          "Sources: forecast = LightGBM (quantile bands); assignments = OR-Tools CP-SAT BAP/QCAP;",
          "routing = rule + cost model. Terminal capacity: Port of Long Beach fact sheets (real)."]
    return "\n".join(L)
