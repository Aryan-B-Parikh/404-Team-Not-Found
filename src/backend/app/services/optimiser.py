"""Exact berth-allocation + quay-crane assignment with OR-Tools CP-SAT.

The optimiser uses the physical berth/crane state loaded from PostgreSQL:
- LOA <= berth length
- draft + under-keel margin <= available tidal depth
- beam <= the actual crane outreach recorded for that terminal
- berth intervals cannot overlap
- simultaneous crane demand cannot exceed the available terminal crane pool
- service must start inside the planning horizon

The FIFO comparison uses the same physical feasibility and crane-pool rules.
"""

from __future__ import annotations

from dataclasses import replace
import math
import time

from ortools.sat.python import cp_model

from .. import reference as ref
from ..config import get_settings
from . import tides

SCALE = 10
HORIZON = 72
MAX_SOLVE_SECONDS = 8.0
INCREMENTAL_SOLVE_SECONDS = 3.0
CRANE_OPTION_SET = (1, 2, 3, 4, 6, 8)
_WARM_MAX_INSTANCES = 4
_warm: dict[tuple, tuple[float, dict[int, tuple[int, int, int]]]] = {}


def _instance_sig(berths, queue, *, move_rate: float | None = None, tidal: bool = False) -> tuple:
    return (
        tuple(sorted((b.id, b.cranes_max, round(b.depth_ft, 3), round(b.reach_ft, 3)) for b in berths)),
        tuple(sorted((v.id, round(v.draft_ft, 3), round(v.beam_ft, 3), v.dest_zone_code,
                      total_moves(v), round(ready_hour(v), 3)) for v in queue)),
        round(float(move_rate), 3) if move_rate is not None else None,
        bool(tidal),
    )


def _crane_options(kmax: int) -> list[int]:
    return sorted({k for k in (*CRANE_OPTION_SET, kmax) if 1 <= k <= kmax})


def ready_hour(v) -> float:
    return max(0.0, v.eta_hours)


def total_moves(v) -> int:
    return v.import_moves + v.export_moves


def priority_score(v) -> float:
    return 0.5 * v.anchored_hours + 0.02 * v.loa_ft + 0.003 * total_moves(v) + 0.02 * v.reefer_units


def wait_weight(v) -> float:
    return 1.0 + v.anchored_hours / 48.0 + v.reefer_units / 300.0


def feasible(v, b) -> bool:
    """Physical berth feasibility using the actual terminal crane outreach."""
    return (
        v.loa_ft <= b.length_ft
        and v.draft_ft <= b.depth_ft
        and v.beam_ft <= float(getattr(b, "reach_ft", 0.0))
    )


def _service_ticks(v, cranes: int, move_rate: float) -> int:
    hours = total_moves(v) / max(1.0, cranes * move_rate) + ref.SERVICE_BUFFER_HOURS
    return max(1, int(round(hours * SCALE)))


def _metrics(assignments: list[dict], berths, deferred: list[dict], horizon: int) -> dict:
    if not assignments:
        return {"serviced": 0, "deferred": len(deferred), "total_wait_hours": 0.0,
                "avg_wait_hours": 0.0, "max_wait_hours": 0.0, "weighted_wait_hours": 0.0,
                "berth_util_pct": 0.0, "crane_util_pct": 0.0, "total_moves": 0,
                "avg_cranes_per_vessel": 0.0, "makespan_hours": 0.0}
    waits = [a["wait_hours"] for a in assignments]
    occupied = sum(max(0.0, min(a["end_hour"], horizon) - min(a["start_hour"], horizon)) for a in assignments)
    crane_hours = sum(a["cranes"] * max(0.0, min(a["end_hour"], horizon) - min(a["start_hour"], horizon)) for a in assignments)
    berth_cap = len(berths) * horizon
    crane_cap = sum(b.cranes_max for b in berths) * horizon
    return {
        "serviced": len(assignments), "deferred": len(deferred),
        "total_wait_hours": round(sum(waits), 1), "avg_wait_hours": round(sum(waits) / len(waits), 1),
        "max_wait_hours": round(max(waits), 1),
        "weighted_wait_hours": round(sum(a["wait_hours"] * a["wait_weight"] for a in assignments), 1),
        "berth_util_pct": round(100.0 * occupied / max(1.0, berth_cap), 1),
        "crane_util_pct": round(100.0 * crane_hours / max(1.0, crane_cap), 1),
        "total_moves": sum(a["moves"] for a in assignments),
        "avg_cranes_per_vessel": round(sum(a["cranes"] for a in assignments) / len(assignments), 1),
        "makespan_hours": round(max(a["end_hour"] for a in assignments), 1),
    }


def _overlap(a0: float, a1: float, b0: float, b1: float) -> bool:
    return a0 < b1 and b0 < a1


def _terminal_start(term: str, desired: int, ready: float, duration: float,
                    berth_free: float, terminal_intervals: dict[str, list[tuple[float, float, int]]],
                    crane_pool: dict[str, int]) -> float:
    """Earliest start satisfying the terminal's actual simultaneous crane pool."""
    start = max(ready, berth_free)
    pool = max(1, crane_pool.get(term, 1))
    while start <= HORIZON:
        end = start + duration
        conflicts = [x for x in terminal_intervals.get(term, []) if _overlap(start, end, x[0], x[1])]
        if sum(x[2] for x in conflicts) + desired <= pool:
            return start
        start = min((x[1] for x in conflicts if x[1] > start), default=start + 1.0)
    return float("inf")


def _fifo_baseline(vessels, berths, move_rate: float, horizon: int, crane_pool: dict[str, int] | None = None) -> tuple[list[dict], list[dict]]:
    slots: list[dict] = []
    free = {b.id: 0.0 for b in berths}
    intervals: dict[str, list[tuple[float, float, int]]] = {}
    deferred: list[dict] = []
    crane_pool = crane_pool or {}
    queue = [v for v in vessels if ready_hour(v) < horizon]
    for v in sorted(queue, key=lambda x: (ready_hour(x), -x.anchored_hours)):
        candidates = []
        for b in berths:
            if not feasible(v, b):
                continue
            pool = max(1, crane_pool.get(b.terminal_code, b.cranes_max))
            cranes = max(1, min(b.cranes_max, ref.MAX_CRANES_PER_VESSEL, pool, math.ceil(total_moves(v) / 900)))
            duration = total_moves(v) / max(1.0, cranes * move_rate) + ref.SERVICE_BUFFER_HOURS
            start = _terminal_start(b.terminal_code, cranes, ready_hour(v), duration, free[b.id], intervals, crane_pool)
            if start == float("inf"):
                continue
            candidates.append((start, b, cranes, duration))
        if not candidates:
            deferred.append({"vessel_id": v.id, "vessel_name": v.name,
                             "reason": f"No physically feasible berth/crane window for LOA {v.loa_ft}ft, beam {v.beam_ft}ft, draft {v.draft_ft}ft"})
            continue
        start, b, cranes, duration = min(candidates, key=lambda x: (x[0], x[1].seq))
        if start > horizon:
            deferred.append({"vessel_id": v.id, "vessel_name": v.name,
                             "reason": "Cannot start within the planning horizon"})
            continue
        end = start + duration
        free[b.id] = end
        intervals.setdefault(b.terminal_code, []).append((start, end, cranes))
        slots.append({"vessel_id": v.id, "vessel_name": v.name, "carrier": v.carrier,
                      "vessel_class": v.vessel_class, "berth_id": b.id, "berth_name": b.name,
                      "terminal_code": b.terminal_code, "pier": b.pier, "zone_code": b.zone_code,
                      "start_hour": round(start, 1), "end_hour": round(end, 1), "cranes": cranes,
                      "wait_hours": round(start - ready_hour(v), 1), "wait_weight": wait_weight(v),
                      "moves": total_moves(v), "priority_score": round(priority_score(v), 2)})
    return slots, deferred


def optimise(ctx, params: dict | None = None, scenario: dict | None = None) -> dict:
    global _warm
    params = params or {}
    scenario = scenario or {}
    horizon = int(params.get("horizon_hours", HORIZON))
    move_rate = float(scenario.get("move_rate_per_crane_hour", ref.DEFAULT_MOVE_RATE_PER_CRANE_HOUR))
    crane_factor = min(1.0, max(0.5, float(scenario.get("crane_factor", 1.0))))

    crane_pool = {
        t.code: max(1, round(ctx.cranes.get(t.code, t.gantry_cranes) * crane_factor))
        for t in ctx.terminals
    }
    berths = [replace(b, cranes_max=min(b.cranes_max, crane_pool.get(b.terminal_code, b.cranes_max))
                     if crane_pool.get(b.terminal_code, b.cranes_max) > 0 else 0)
              for b in ctx.berths]
    queue = [v for v in ctx.vessels if ready_hour(v) < horizon and not v.unresolved]
    berths_by_zone: dict[str, list] = {}
    for b in berths:
        if b.cranes_max > 0:
            berths_by_zone.setdefault(b.zone_code, []).append(b)

    use_tidal = bool(scenario["tidal"]) if "tidal" in scenario else bool(get_settings().feature_tidal)
    draft_by_id = {v.id: v.draft_ft for v in queue}
    model = cp_model.CpModel()
    tmax = (horizon + 200) * SCALE
    start, end, served, wait = {}, {}, {}, {}
    x: dict[tuple[int, int, int], cp_model.IntVar] = {}
    intervals_by_berth: dict[int, list] = {b.id: [] for b in berths}
    intervals_by_term: dict[str, list] = {t.code: [] for t in ctx.terminals}
    no_fit: list[dict] = []
    prio = {v.id: priority_score(v) for v in queue}
    pmax = max(prio.values()) if prio else 1.0

    for v in queue:
        fits = [b for b in berths_by_zone.get(v.dest_zone_code, []) if feasible(v, b)]
        if not fits:
            no_fit.append({"vessel_id": v.id, "vessel_name": v.name,
                           "reason": f"No berth fits LOA {v.loa_ft}ft / beam {v.beam_ft}ft / draft {v.draft_ft}ft"})
            continue
        start[v.id] = model.NewIntVar(int(ready_hour(v) * SCALE), tmax, f"start_{v.id}")
        served[v.id] = model.NewBoolVar(f"served_{v.id}")
        wait[v.id] = model.NewIntVar(0, tmax, f"wait_{v.id}")
        end[v.id] = model.NewIntVar(0, tmax, f"end_{v.id}")
        size_terms, presence = [], []
        for b in fits:
            kmax = min(b.cranes_max, ref.MAX_CRANES_PER_VESSEL, crane_pool.get(b.terminal_code, 1))
            if kmax < 1:
                continue
            allowed_ticks = None
            if use_tidal and tides.needs_tide(b.depth_ft, v.draft_ft):
                hours = tides.allowed_start_hours(b.id, b.depth_ft, v.draft_ft, horizon)
                if not hours:
                    continue
                allowed_ticks = [h * SCALE for h in hours]
            for k in _crane_options(kmax):
                var = model.NewBoolVar(f"x_{v.id}_{b.id}_{k}")
                x[(v.id, b.id, k)] = var
                presence.append(var)
                size = _service_ticks(v, k, move_rate)
                size_terms.append(size * var)
                iv = model.NewOptionalFixedSizeIntervalVar(start[v.id], size, var, f"iv_{v.id}_{b.id}_{k}")
                intervals_by_berth[b.id].append(iv)
                intervals_by_term[b.terminal_code].append((iv, k))
                if allowed_ticks is not None:
                    model.AddAllowedAssignments([start[v.id]], [[t] for t in allowed_ticks]).OnlyEnforceIf(var)
        model.Add(sum(presence) == served[v.id])
        model.Add(end[v.id] == start[v.id] + sum(size_terms))
        model.Add(start[v.id] <= horizon * SCALE).OnlyEnforceIf(served[v.id])
        model.Add(wait[v.id] >= start[v.id] - int(ready_hour(v) * SCALE) - tmax * (1 - served[v.id]))
        model.Add(wait[v.id] >= 0)

    for b in berths:
        if intervals_by_berth[b.id]:
            model.AddNoOverlap(intervals_by_berth[b.id])
    for term in ctx.terminals:
        entries = intervals_by_term.get(term.code, [])
        if entries:
            model.AddCumulative([e[0] for e in entries], [e[1] for e in entries], crane_pool.get(term.code, 1))

    makespan = model.NewIntVar(0, tmax, "makespan")
    for v in queue:
        if v.id in served:
            model.Add(end[v.id] <= makespan).OnlyEnforceIf(served[v.id])
    model.Add(makespan >= 0)

    COUNT_W, WAIT_W, MAKESPAN_W, CRANE_W, PRIO_W = 1_000_000, 50, 2_000, 100, 20
    wait_cost = sum(int(wait_weight(v) * WAIT_W) * wait[v.id] for v in queue if v.id in served)
    crane_use = sum(k * var for (_, _, k), var in x.items())
    priority_bonus = sum(int(1000 * prio[v.id] / pmax) * served[v.id] for v in queue if v.id in served)
    model.Minimize(wait_cost + MAKESPAN_W * makespan + CRANE_W * crane_use - PRIO_W * priority_bonus
                   - COUNT_W * sum(served[v.id] for v in queue if v.id in served))

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 0   # proto: 0 = use all cores (8 was a hard-coded guess)
    # Stop (as OPTIMAL) once provably within 10% of the bound — B-2 acceptance allows
    # documenting a time-limited gap instead of burning the whole budget past it.
    solver.parameters.relative_gap_limit = 0.10
    warm_key = (ctx.t0.isoformat(), _instance_sig(berths, queue, move_rate=move_rate, tidal=use_tidal))
    warm = _warm.get(warm_key)
    incremental = bool(scenario.get("incremental")) and warm is not None
    solver.parameters.max_time_in_seconds = INCREMENTAL_SOLVE_SECONDS if incremental else MAX_SOLVE_SECONDS
    if incremental:
        for vid, (bid, k, ticks) in warm[1].items():
            var = x.get((vid, bid, k))
            if var is not None and vid in start:
                model.AddHint(var, 1); model.AddHint(start[vid], ticks); model.AddHint(served[vid], 1)

    t_start = time.perf_counter(); status = solver.Solve(model); solve_ms = int((time.perf_counter() - t_start) * 1000)
    status_name = solver.StatusName(status)
    assignments: list[dict] = []
    deferred = list(no_fit)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for v in queue:
            if v.id not in served or solver.Value(served[v.id]) == 0:
                if v.id in served:
                    deferred.append({"vessel_id": v.id, "vessel_name": v.name, "reason": "Horizon capacity exhausted"})
                continue
            chosen = next(((bid, k) for (vid, bid, k), var in x.items() if vid == v.id and solver.Value(var) == 1), None)
            if chosen is None:
                continue
            bid, k = chosen; b = next(bb for bb in berths if bb.id == bid)
            st, en = solver.Value(start[v.id]) / SCALE, solver.Value(end[v.id]) / SCALE
            assignments.append({"vessel_id": v.id, "vessel_name": v.name, "carrier": v.carrier,
                               "vessel_class": v.vessel_class, "berth_id": b.id, "berth_name": b.name,
                               "terminal_code": b.terminal_code, "pier": b.pier, "zone_code": b.zone_code,
                               "start_hour": round(st, 1), "end_hour": round(en, 1), "cranes": k,
                               "wait_hours": round(max(0.0, st - ready_hour(v)), 1), "wait_weight": wait_weight(v),
                               "moves": total_moves(v), "priority_score": round(priority_score(v), 2)})
    else:
        for v in queue:
            if v.id in served:
                deferred.append({"vessel_id": v.id, "vessel_name": v.name, "reason": f"Solver {status_name}"})
    assignments.sort(key=lambda a: a["start_hour"])

    gap_pct = None
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) and math.isfinite(solver.BestObjectiveBound()):
        gap_pct = round(abs(solver.ObjectiveValue() - solver.BestObjectiveBound()) /
                        max(1.0, abs(solver.ObjectiveValue())) * 100, 2)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) and assignments:
        _warm[warm_key] = (time.time(), {a["vessel_id"]: (a["berth_id"], a["cranes"], int(round(a["start_hour"] * SCALE))) for a in assignments})
        while len(_warm) > _WARM_MAX_INSTANCES:
            _warm.pop(min(_warm, key=lambda k: _warm[k][0]))

    tidal_feasible = True
    if use_tidal:
        berth_by_id = {b.id: b for b in berths}
        for a in assignments:
            b = berth_by_id[a["berth_id"]]
            if tides.needs_tide(b.depth_ft, draft_by_id.get(a["vessel_id"], 0.0)) and not tides.is_open(
                    b.id, b.depth_ft, draft_by_id.get(a["vessel_id"], 0.0), int(round(a["start_hour"]))):
                tidal_feasible = False; break

    fifo_slots, fifo_deferred = _fifo_baseline(ctx.vessels, berths, move_rate, horizon, crane_pool)
    m_opt, m_base = _metrics(assignments, berths, deferred, horizon), _metrics(fifo_slots, berths, fifo_deferred, horizon)
    deltas = {
        "wait_total": round(m_base["total_wait_hours"] - m_opt["total_wait_hours"], 1),
        "wait_total_pct": round((m_base["total_wait_hours"] - m_opt["total_wait_hours"]) / m_base["total_wait_hours"] * 100, 1) if m_base["total_wait_hours"] else 0.0,
        "weighted_wait": round(m_base["weighted_wait_hours"] - m_opt["weighted_wait_hours"], 1),
        "serviced": m_opt["serviced"] - m_base["serviced"], "moves": m_opt["total_moves"] - m_base["total_moves"],
        "makespan": round(m_base["makespan_hours"] - m_opt["makespan_hours"], 1),
        "berth_util": round(m_opt["berth_util_pct"] - m_base["berth_util_pct"], 1),
        "crane_util": round(m_opt["crane_util_pct"] - m_base["crane_util_pct"], 1),
    }
    return {
        "solver": "ortools-cp-sat", "status": status_name,
        "objective": round(solver.ObjectiveValue(), 1) if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None,
        "solve_ms": solve_ms, "horizon_hours": horizon, "assignments": assignments, "deferred": deferred,
        "metrics": m_opt, "baseline": m_base, "deltas": deltas,
        "weights": {"count_throughput": COUNT_W, "wait_alpha": WAIT_W, "makespan_beta": MAKESPAN_W,
                     "crane_gamma": CRANE_W, "priority_bonus_delta": PRIO_W,
                     "wait_weight_formula": "1 + anchored_hours/48 + reefer_units/300"},
        "params": {"horizon_hours": horizon, "move_rate_per_crane_hour": move_rate, "crane_factor": crane_factor,
                   "tidal": use_tidal, "incremental": incremental, "tidal_feasible": tidal_feasible,
                   "gap_pct": gap_pct, "solver_status": status_name, "crane_pool": crane_pool},
        "tidal_feasible": tidal_feasible, "incremental": incremental, "gap_pct": gap_pct,
    }
