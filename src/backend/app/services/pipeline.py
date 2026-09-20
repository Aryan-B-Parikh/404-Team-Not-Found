"""Orchestration pipeline: runs the engines in dependency order.

Split (B-6): compute lives in the ``services/*`` engines, writes in
``services/persistence.py``, the dashboard projection in ``services/overview.py``,
memoisation in ``services/run_cache.py``. This module is sequencing only —
plus compatibility re-exports so existing ``pipeline.X`` importers keep working.
"""

from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import reference as ref
from ..config import get_settings
from ..models import ForecastRun, OptimiserRun
from . import anomaly as anomaly_svc
from . import forecasting as fc_svc
from . import hotspot as hotspot_svc
from . import optimiser as opt_svc
from . import plan as plan_svc
from . import routing as routing_svc
from .context import EngineContext, load_context, zone_capacity
from .overview import DATASET_NOTE as DATASET_NOTE  # re-export (mcp_server, bob)
from .overview import DAILY_OP_COST_USD as DAILY_OP_COST_USD
from .overview import all_zone_codes, build_overview as _build_overview_impl
from .persistence import persist_anomalies, persist_forecast_run, persist_optimiser_run
from .persistence import persist_plan as _persist_plan_impl
from .persistence import persist_routing
from .run_cache import TTLCache

CACHE_TTL = 120.0
_fc_cache = TTLCache(CACHE_TTL)
_opt_cache = TTLCache(CACHE_TTL)

build_overview = _build_overview_impl  # re-export (routers/overview, bob, mcp_server)
persist_plan = _persist_plan_impl      # re-export (routers/plan)


def _forecast_cache_key(ctx: EngineContext) -> str:
    return f"{ctx.t0.isoformat()}|{ctx.data_version}|{get_settings().feature_weather}"


def run_forecasts(ctx: EngineContext, db: Session | None = None, force: bool = False) -> dict:
    key = _forecast_cache_key(ctx)
    cached = _fc_cache.get(key)
    if cached is not None and not force:
        return cached["forecasts"]
    weather = fc_svc.load_weather_series(db, ctx.t0, fc_svc.HORIZON) if db is not None and get_settings().feature_weather else []
    forecasts = {}
    model_source = f"{ctx.dataset_source}|ctx:{ctx.data_version}"
    for zone in all_zone_codes():
        zone_vessels = ctx.vessels if zone == "Z-PORT" else [v for v in ctx.vessels if v.dest_zone_code == zone]
        # AIS history records no yard data; the measured inventory snapshot is the live level.
        # Z-PORT is a pseudo-zone with no inventory rows — it gets the fleet-mean level.
        if zone == "Z-PORT":
            live_yard = round(sum(ctx.yard_util.values()) / len(ctx.yard_util), 1) if ctx.yard_util else None
        else:
            live_yard = ctx.yard_util.get(zone.removeprefix("Z-"))
        forecasts[zone] = fc_svc.forecast_zone(zone, ref.ZONE_LABELS[zone], ctx.history.get(zone, []), zone_vessels,
                                               zone_capacity(ctx, zone), ctx.t0, weather=weather, source=model_source,
                                               live_yard=live_yard)
    run_id = persist_forecast_run(db, forecasts, ctx) if db is not None else None
    _fc_cache.set(key, {"forecasts": forecasts, "run_id": run_id})
    return forecasts


def run_anomalies(ctx: EngineContext, db: Session | None = None) -> list[dict]:
    flags = anomaly_svc.detect_anomalies(ctx)
    if db is not None:
        persist_anomalies(db, flags)
    return flags


def run_hotspots(ctx, forecasts, anomalies, db=None): return hotspot_svc.compute_hotspots(ctx, forecasts, anomalies)


def _with_feature_defaults(scenario: dict | None) -> dict:
    out = dict(scenario or {}); out.setdefault("tidal", bool(get_settings().feature_tidal)); return out


def _optimizer_cache_key(ctx: EngineContext, scenario: dict) -> str:
    """Fingerprint all optimisation inputs, including test/fallback contexts without data_version."""
    h = hashlib.sha256()
    h.update((ctx.data_version or "").encode())
    h.update(ctx.t0.isoformat().encode())
    for v in sorted(ctx.vessels, key=lambda x: x.id):
        h.update(repr((v.id, v.eta_hours, v.dest_zone_code, v.import_moves, v.export_moves,
                       v.loa_ft, v.beam_ft, v.draft_ft, v.reefer_units, v.unresolved)).encode())
    for b in sorted(ctx.berths, key=lambda x: x.id):
        h.update(repr((b.id, b.length_ft, b.depth_ft, b.cranes_max, getattr(b, "reach_ft", 0), b.terminal_code)).encode())
    for code, count in sorted(ctx.cranes.items()): h.update(repr((code, count)).encode())
    h.update(repr(sorted(scenario.items())).encode())
    return h.hexdigest()


def run_optimiser(ctx: EngineContext, forecasts: dict, scenario: dict | None = None, db: Session | None = None) -> dict:
    scenario = _with_feature_defaults(scenario); ckey = _optimizer_cache_key(ctx, scenario)
    if db is None:
        # get/set are two lock acquisitions: a race would only recompute an identical
        # run, so the old double-checked pattern is not worth extra machinery here.
        cached = _opt_cache.get(ckey)
        if cached is not None:
            return dict(cached)
        out = opt_svc.optimise(ctx, {}, scenario)
        _opt_cache.set(ckey, out)
        return dict(out)
    out = opt_svc.optimise(ctx, {}, scenario)
    out["run_id"] = persist_optimiser_run(db, out)
    return out


def run_routing(ctx, forecasts, optimiser_out, db=None):
    recs = routing_svc.recommend_routing(ctx, forecasts, optimiser_out)
    if db is not None:
        persist_routing(db, recs)
    return recs


def build_plan_output(ctx, forecasts, optimiser_out, routing, forecast_run_id=None, model_version=None):
    return plan_svc.build_plan(ctx, forecasts, optimiser_out, routing, forecast_run_id=forecast_run_id, optimiser_run_id=optimiser_out.get("run_id"), model_version=model_version)


def build_full(db: Session, scenario: dict | None = None, persist: bool = True) -> dict:
    ctx = load_context(db); forecasts = run_forecasts(ctx, db if persist else None); anomalies = run_anomalies(ctx, db if persist else None); hotspots = run_hotspots(ctx, forecasts, anomalies); optimiser_out = run_optimiser(ctx, forecasts, scenario, db if persist else None); routing = run_routing(ctx, forecasts, optimiser_out, db if persist else None); model_version = forecasts["Z-PORT"].model["model_version"]
    entry = _fc_cache.get(_forecast_cache_key(ctx)) or {}
    forecast_run_id = entry.get("run_id") or db.execute(select(ForecastRun.id).order_by(ForecastRun.id.desc())).scalars().first()
    if optimiser_out.get("run_id") is None: optimiser_out["run_id"] = db.execute(select(OptimiserRun.id).order_by(OptimiserRun.id.desc())).scalars().first()
    plan_out = build_plan_output(ctx, forecasts, optimiser_out, routing, forecast_run_id=forecast_run_id, model_version=model_version)
    return {"ctx": ctx, "forecasts": forecasts, "anomalies": anomalies, "hotspots": hotspots, "optimiser": optimiser_out, "routing": routing, "plan": plan_out}
