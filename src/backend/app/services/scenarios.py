"""Scenario engine: validated, isolated, data-versioned what-if contexts."""

from __future__ import annotations

from dataclasses import replace
import hashlib

from ..services.context import EngineContext

VALID_KINDS = {"CRANE_OUTAGE", "PRODUCTIVITY", "BERTH_REMOVED", "BERTH_ADDED", "BUNCHING", "SCHEDULE_CHANGE"}


class ScenarioError(ValueError):
    """Raised for contradictory or invalid scenario parameters."""


def _validate(body) -> None:
    kind = (getattr(body, "kind", "") or "").upper()
    if kind not in VALID_KINDS:
        raise ScenarioError(f"unknown scenario kind {kind!r}; expected one of {sorted(VALID_KINDS)}")
    if kind in ("BERTH_REMOVED", "BERTH_ADDED"):
        if not getattr(body, "terminal_code", None):
            raise ScenarioError(f"{kind} requires terminal_code")
        if int(getattr(body, "berth_count_delta", 0) or 0) <= 0:
            raise ScenarioError(f"{kind} requires berth_count_delta > 0")
    if kind == "BUNCHING" and int(getattr(body, "bunching_vessels", 0) or 0) <= 0:
        raise ScenarioError("BUNCHING requires bunching_vessels > 0")


def _scenario_version(ctx: EngineContext) -> str:
    h = hashlib.sha256(ctx.data_version.encode())
    for v in sorted(ctx.vessels, key=lambda x: x.id):
        h.update(repr((v.id, v.imo, v.status, v.declared_eta_hours, v.ais_eta_hours,
                       v.dest_zone_code, v.import_moves, v.export_moves, v.anchored_hours,
                       v.loa_ft, v.beam_ft, v.draft_ft, v.reefer_units, v.unresolved)).encode())
    for b in sorted(ctx.berths, key=lambda x: x.id):
        h.update(repr((b.id, b.length_ft, b.depth_ft, b.cranes_max, b.reach_ft, b.terminal_code)).encode())
    for code, count in sorted(ctx.cranes.items()):
        h.update(repr((code, count)).encode())
    return h.hexdigest()[:20]


def modify_context(ctx: EngineContext, body) -> tuple[EngineContext, str]:
    """Return an isolated context whose forecast inputs reflect the requested disruption."""
    _validate(body)
    kind = (body.kind or "").upper()
    terminal = (getattr(body, "terminal_code", None) or "").upper() or None
    modified = ctx

    if kind in ("CRANE_OUTAGE", "PRODUCTIVITY"):
        factor = min(1.0, max(0.5, float(getattr(body, "crane_factor", 1.0))))
        scaled = {code: max(1, round(count * factor)) for code, count in ctx.cranes.items()}
        modified = replace(ctx, cranes=scaled)
        description = f"crane availability {factor * 100:.0f}% and {body.move_rate_per_crane_hour:g} moves/crane-hour"

    elif kind in ("BERTH_REMOVED", "BERTH_ADDED"):
        term = next((t for t in ctx.terminals if t.code == terminal), None)
        if term is None:
            raise ScenarioError(f"unknown terminal_code {terminal!r}")
        target = [b for b in ctx.berths if b.terminal_code == terminal]
        others = [b for b in ctx.berths if b.terminal_code != terminal]
        n = int(body.berth_count_delta)
        if kind == "BERTH_REMOVED":
            if n >= len(target):
                raise ScenarioError(f"cannot remove {n} berths — {terminal} only has {len(target)}")
            kept = target[:-n]
            description = f"{n} berth(s) removed at {terminal} ({len(target)} → {len(kept)} working berths)"
        else:
            if n > len(target):
                raise ScenarioError(f"cannot add {n} berths from the physical reference pool at {terminal}")
            next_id = max((b.id for b in ctx.berths), default=0) + 1
            added = [replace(b, id=next_id + i, name=f"{b.name}+{i + 1}", seq=b.seq + 100 + i)
                     for i, b in enumerate(target[:n])]
            kept = target + added
            description = f"{n} scenario berth(s) added at {terminal} ({len(target)} → {len(kept)} working berths)"
        modified = replace(ctx, berths=kept + others)

    elif kind == "BUNCHING":
        n = int(body.bunching_vessels)
        pool = [v for v in ctx.vessels if v.status != "INBOUND"] or ctx.vessels
        if not pool:
            raise ScenarioError("BUNCHING requires at least one vessel template")
        next_id = max((v.id for v in ctx.vessels), default=0) + 1
        extra = []
        for i in range(n):
            src = pool[i % len(pool)]
            extra.append(replace(src, id=next_id + i, name=f"{src.name} [bunch {i + 1}]", status="INBOUND",
                                  declared_eta_hours=float(4 + (i * 3) % 20), ais_eta_hours=None,
                                  anchored_hours=0.0, anchorage_zone="En route — San Pedro Approach"))
        modified = replace(ctx, vessels=list(ctx.vessels) + extra)
        description = f"{n} extra inbound call(s) bunched into the next ~24h"

    elif kind == "SCHEDULE_CHANGE":
        shift = float(getattr(body, "schedule_shift_hours", -6.0) or -6.0)
        moved = [replace(v,
                         declared_eta_hours=max(0.5, v.declared_eta_hours + shift),
                         ais_eta_hours=(None if v.ais_eta_hours is None else max(0.5, v.ais_eta_hours + shift)))
                 if v.status == "INBOUND" else v for v in ctx.vessels]
        modified = replace(ctx, vessels=moved)
        description = f"all inbound ETAs shifted by {shift:+.1f}h"

    modified = replace(modified, data_version=_scenario_version(modified))
    return modified, description


def compare(baseline: dict, scenario: dict) -> dict:
    return {
        "serviced": scenario["serviced"] - baseline["serviced"],
        "moves": scenario["total_moves"] - baseline["total_moves"],
        "avg_wait": round(scenario["avg_wait_hours"] - baseline["avg_wait_hours"], 1),
        "weighted_wait": round(scenario["weighted_wait_hours"] - baseline["weighted_wait_hours"], 1),
        "makespan": round(scenario["makespan_hours"] - baseline["makespan_hours"], 1),
        "berth_util": round(scenario["berth_util_pct"] - baseline["berth_util_pct"], 1),
        "crane_util": round(scenario["crane_util_pct"] - baseline["crane_util_pct"], 1),
        "deferred": scenario["deferred"] - baseline["deferred"],
    }
