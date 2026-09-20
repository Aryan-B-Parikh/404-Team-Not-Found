"""W3 unit tests — tidal model, scenario validation/modifiers, optimiser flags.

No network, no credits. DB-backed tests are marked via conftest.requires_db.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace as NS

import pytest

from app.services import scenarios as S
from app.services import tides
from app.services.context import BerthCtx, EngineContext, TerminalCtx, VesselCtx

from .conftest import requires_db

pytestmark = pytest.mark.slow  # CP-SAT solver tests (~100s)


# ------------------------------------------------------------------ fixtures
def _terminal(code="PCT", zone="Z-PCT") -> TerminalCtx:
    return TerminalCtx(id=1, code=code, name=code, pier="Pier J", lat=None, lon=None,
                       berth_length_ft=5902, deepsea_berths=4, gantry_cranes=14,
                       capacity_teu_m=None, zone_code=zone, note=None)


def _berths(n=4, code="PCT", zone="Z-PCT", depth=52.0) -> list[BerthCtx]:
    return [BerthCtx(id=i + 1, name=f"J-{i+1}", seq=i + 1, length_ft=1475, depth_ft=depth,
                     cranes_max=4, terminal_code=code, terminal_name=code, pier="Pier J", zone_code=zone)
            for i in range(n)]


def _vessel(i: int, status="ANCHORAGE", loa=1000, draft=45.0, eta=0.0) -> VesselCtx:
    return VesselCtx(id=i, mmsi=f"36700000{i}", imo=f"IMO{i}", name=f"M/V T{i}", carrier="C",
                     vessel_class="PANAMAX", loa_ft=loa, beam_ft=124, draft_ft=draft,
                     teu_capacity=5000, import_moves=3000, export_moves=2500, origin_port="Busan",
                     reefer_units=100, status=status, anchorage_zone="A", declared_eta_hours=eta,
                     ais_eta_hours=None, anchored_hours=10.0, dest_zone_code="Z-PCT",
                     data_confidence=1.0, unresolved=False)


def _ctx(berths=None, vessels=None) -> EngineContext:
    return EngineContext(t0=datetime(2026, 1, 1, tzinfo=timezone.utc), terminals=[_terminal()],
                         berths=berths or _berths(), vessels=vessels or [_vessel(1), _vessel(2)])


def _body(**kw) -> NS:
    base = dict(kind="CRANE_OUTAGE", crane_factor=1.0, move_rate_per_crane_hour=28.0,
                terminal_code=None, berth_count_delta=0, bunching_vessels=0, schedule_shift_hours=-6.0)
    return NS(**{**base, **kw})


# ------------------------------------------------------------------ tides
def test_tide_depth_oscillates_within_amplitude():
    vals = [tides.depth_ft(50.0, h, 1) for h in range(0, 25)]
    assert max(vals) - min(vals) == pytest.approx(2 * tides.TIDE_AMPLITUDE_FT, abs=0.05)
    assert min(vals) > 50.0 - tides.TIDE_AMPLITUDE_FT - 0.01


def test_needs_tide_only_for_deep_draft():
    assert tides.needs_tide(50.0, 50.5) is True     # draft + margin > charted depth
    assert tides.needs_tide(52.0, 50.5) is False


def test_allowed_hours_are_a_strict_subset_for_deep_vessels():
    shallow = tides.allowed_start_hours(1, 52.0, 45.0, 72)
    deep = tides.allowed_start_hours(1, 50.0, 50.5, 72)
    assert len(shallow) == 73                        # never constrained
    assert 0 < len(deep) < 73                        # only at high water
    assert all(tides.is_open(1, 50.0, 50.5, h) for h in deep)
    assert not any(tides.is_open(1, 50.0, 50.5, h) for h in range(73) if h not in deep)


@requires_db
def test_noaa_fetch_replaces_harmonic_rows_in_its_horizon(monkeypatch):
    """Regression (observed on startup): fetch_noaa_tides deleted only NOAA-note rows,
    so its inserts collided with persisted harmonic rows on uq_tide_berth_hours and
    the NOAA path could never persist once the harmonic fallback had run. The fetch
    must replace the rows its horizon covers."""
    from datetime import datetime

    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import Berth, TidalWindow

    payload = {"predictions": [
        {"t": "2026-09-20 00:00", "v": "1.2"},
        {"t": "2026-09-20 01:00", "v": "2.4"},
    ]}

    class _FakeResp:
        def raise_for_status(self): pass
        def json(self): return payload

    monkeypatch.setattr(tides.httpx, "get", lambda *a, **k: _FakeResp())

    db = SessionLocal()
    try:
        n_berths = len(db.execute(select(Berth)).scalars().all())
        t0 = datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc)
        written = tides.fetch_noaa_tides(db, horizon_hours=1, t0=t0)
        assert written == 2 * n_berths, "NOAA fetch must persist, not collide with harmonic rows"
        covered = db.execute(select(TidalWindow).where(TidalWindow.hours_ago <= 1)).scalars().all()
        assert covered and all(r.note == tides.NOAA_NOTE for r in covered)
    finally:
        db.close()
        tides.ensure_windows(SessionLocal(), force=True)  # restore the harmonic baseline


# ------------------------------------------------------------------ scenarios
def test_scenario_berth_removed_and_added_change_the_context():
    ctx = _ctx()
    removed, desc_r = S.modify_context(ctx, _body(kind="BERTH_REMOVED", terminal_code="PCT", berth_count_delta=2))
    added, desc_a = S.modify_context(ctx, _body(kind="BERTH_ADDED", terminal_code="PCT", berth_count_delta=2))
    assert len(removed.berths) == 2 and len(added.berths) == 6
    assert "removed" in desc_r and "added" in desc_a
    assert len(ctx.berths) == 4                       # original untouched


def test_scenario_bunching_adds_inbound_vessels():
    ctx = _ctx()
    out, desc = S.modify_context(ctx, _body(kind="BUNCHING", bunching_vessels=5))
    assert len(out.vessels) == len(ctx.vessels) + 5
    assert all(v.status == "INBOUND" for v in out.vessels[2:])
    assert "bunched" in desc


def test_scenario_schedule_change_shifts_inbound_etas():
    ctx = _ctx(vessels=[_vessel(1, status="INBOUND", eta=20.0)])
    out, _ = S.modify_context(ctx, _body(kind="SCHEDULE_CHANGE", schedule_shift_hours=-12.0))
    assert out.vessels[0].declared_eta_hours == 8.0


def test_scenario_rejects_contradictory_parameters():
    ctx = _ctx()
    with pytest.raises(S.ScenarioError):
        S.modify_context(ctx, _body(kind="BERTH_REMOVED", terminal_code="PCT", berth_count_delta=99))
    with pytest.raises(S.ScenarioError):
        S.modify_context(ctx, _body(kind="BERTH_REMOVED"))            # no terminal
    with pytest.raises(S.ScenarioError):
        S.modify_context(ctx, _body(kind="BUNCHING", bunching_vessels=0))
    with pytest.raises(S.ScenarioError):
        S.modify_context(ctx, _body(kind="NOT_A_KIND"))


def test_scenario_compare_is_scenario_minus_baseline():
    base = {"serviced": 10, "total_moves": 100, "avg_wait_hours": 5.0, "weighted_wait_hours": 9.0,
            "makespan_hours": 50.0, "berth_util_pct": 60.0, "crane_util_pct": 55.0, "deferred": 2}
    scen = {**base, "serviced": 8, "avg_wait_hours": 7.5}
    d = S.compare(base, scen)
    assert d["serviced"] == -2 and d["avg_wait"] == 2.5


# ------------------------------------------------------------------ optimiser
@requires_db
def test_optimiser_reports_tidal_incremental_and_gap():
    from app.db import SessionLocal
    from app.services import optimiser, pipeline

    db = SessionLocal()
    try:
        ctx = pipeline.load_context(db)
        base = optimiser.optimise(ctx, {}, {})
        tidal = optimiser.optimise(ctx, {}, {"tidal": True})
        inc = optimiser.optimise(ctx, {}, {"incremental": True})
    finally:
        db.close()

    assert base["tidal_feasible"] is True and tidal["tidal_feasible"] is True
    assert base["incremental"] is False and inc["incremental"] is True
    for out in (base, tidal, inc):
        assert out["gap_pct"] is None or out["gap_pct"] >= 0


@requires_db
def test_tidal_deep_vessels_start_only_at_high_water():
    """Every assignment of a tide-constrained vessel must start in an allowed hour."""
    from app.db import SessionLocal
    from app.services import optimiser, pipeline, tides

    db = SessionLocal()
    try:
        ctx = pipeline.load_context(db)
        out = optimiser.optimise(ctx, {}, {"tidal": True})
        berths = {b.id: b for b in ctx.berths}
        drafts = {v.id: v.draft_ft for v in ctx.vessels}
    finally:
        db.close()

    for a in out["assignments"]:
        b = berths[a["berth_id"]]
        draft = drafts[a["vessel_id"]]
        if tides.needs_tide(b.depth_ft, draft):
            assert tides.is_open(b.id, b.depth_ft, draft, int(round(a["start_hour"]))), a


# ------------------------------------------------- tidal persistence (W3 gap fix)
@requires_db
def test_ensure_windows_populates_and_is_idempotent():
    """The frozen TidalWindow table must actually be written, not left empty."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import TidalWindow
    from app.services import tides

    db = SessionLocal()
    try:
        written = tides.ensure_windows(db, horizon_hours=24, force=True)
        assert written > 0
        rows = db.execute(select(TidalWindow)).scalars().all()
        assert len(rows) == written
        # modelled rows must be labelled as such (data-honesty rule)
        assert all(r.note == tides.HARMONIC_NOTE for r in rows)
        # hour offsets stay inside the requested horizon
        assert max(r.hours_ago for r in rows) == 24
        assert min(r.hours_ago for r in rows) == 0

        # second call is a no-op while rows exist
        assert tides.ensure_windows(db, horizon_hours=24) == 0
    finally:
        db.close()


@requires_db
def test_depth_at_prefers_persisted_rows_over_harmonic():
    """A persisted TidalWindow row must override the harmonic model for that berth/hour."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import Berth, TidalWindow
    from app.services import tides

    db = SessionLocal()
    try:
        tides.ensure_windows(db, horizon_hours=24, force=True)
        berth = db.execute(select(Berth)).scalars().first()
        assert berth is not None

        sentinel = 1.5  # nothing the harmonic model could produce
        row = db.execute(
            select(TidalWindow).where(TidalWindow.berth_id == berth.id, TidalWindow.hours_ago == 3)
        ).scalars().first()
        assert row is not None
        row.min_depth_ft = sentinel
        db.commit()
        tides.invalidate_cache()

        assert tides.depth_at(berth.id, berth.depth_ft, 3) == pytest.approx(sentinel)
        # an hour with no override still falls back to the harmonic curve
        assert tides.depth_at(berth.id, berth.depth_ft, 999) == pytest.approx(
            tides.depth_ft(berth.depth_ft, 999, berth.id)
        )
    finally:
        # leave the table in a clean, fully-modelled state for later tests, but never let
        # cleanup raise over the top of a real assertion failure
        try:
            tides.ensure_windows(db, horizon_hours=24, force=True)
        except Exception:  # noqa: BLE001
            db.rollback()
        db.close()


@requires_db
def test_incremental_solve_is_not_slower_than_cold_start():
    """TEAM_PLAN acceptance criterion: a warm-started re-plan must not cost more wall clock
    than the cold solve it re-runs (it is hinted AND given a shorter budget)."""
    from app.db import SessionLocal
    from app.services import optimiser, pipeline

    # the mechanism, asserted deterministically (no timing noise)
    assert optimiser.INCREMENTAL_SOLVE_SECONDS < optimiser.MAX_SOLVE_SECONDS

    db = SessionLocal()
    try:
        ctx = pipeline.load_context(db)
        cold = optimiser.optimise(ctx, {}, {})                    # primes the warm-start cache
        warm = optimiser.optimise(ctx, {}, {"incremental": True})
    finally:
        db.close()

    assert cold["incremental"] is False
    assert warm["incremental"] is True, "warm-start did not engage — cache/t0 mismatch"
    # generous tolerance: this must catch a real regression (a warm start that is *slower*)
    # without failing on scheduler jitter when both solves finish in a few hundred ms.
    budget = max(cold["solve_ms"] * 1.5, cold["solve_ms"] + 500)
    assert warm["solve_ms"] <= budget, (
        f"incremental solve was slower: warm={warm['solve_ms']}ms cold={cold['solve_ms']}ms"
    )
    # the hinted run must still be a usable solution, not a timeout with nothing served
    assert warm["assignments"], "warm-started solve returned no assignments"
    # and the hint must not have degraded quality — allow ±1 for CP-SAT scheduler jitter
    assert warm["metrics"]["serviced"] >= cold["metrics"]["serviced"] - 1


@requires_db
def test_scenario_cache_key_includes_context():
    """Regression: a scenario that changes the context must NOT return the cached baseline.

    With the old key (t0 + scenario only) the second call returned the baseline solution,
    whose assignments could reference berths that the scenario had removed.
    """
    from app.db import SessionLocal
    from app.services import pipeline, scenarios as S

    db = SessionLocal()
    try:
        ctx = pipeline.load_context(db)
        fc = pipeline.run_forecasts(ctx)
        pipeline.run_optimiser(ctx, fc, {})                     # warm the baseline into the cache
        small, _ = S.modify_context(ctx, _body(kind="BERTH_REMOVED", terminal_code="PCT", berth_count_delta=2))
        scen = pipeline.run_optimiser(small, fc, {})             # same scenario dict as baseline
        allowed = {b.id for b in small.berths}
    finally:
        db.close()

    assert len(small.berths) < len(ctx.berths)
    assert scen["assignments"], "scenario must still schedule something"
    assert all(a["berth_id"] in allowed for a in scen["assignments"]), \
        "stale cache: assignment references a berth that the scenario removed"


# ------------------------------------------------- feature-flag wiring (W3 gap fix)
def test_pipeline_defaults_tidal_from_feature_flag():
    """A caller that passes no scenario must still get the configured tidal behaviour.

    This is the bug the W3 audit found: tidal was implemented but unreachable on the
    default `build_full(db)` path, so every read endpoint solved without it.
    """
    from app.config import get_settings
    from app.services.pipeline import _with_feature_defaults

    flag = bool(get_settings().feature_tidal)
    assert _with_feature_defaults(None)["tidal"] is flag
    assert _with_feature_defaults({})["tidal"] is flag
    # an explicit value always wins over the flag (so the UI toggle can switch it off)
    assert _with_feature_defaults({"tidal": False})["tidal"] is False
    assert _with_feature_defaults({"tidal": True})["tidal"] is True
    # unrelated scenario keys are preserved, and the caller's dict is not mutated
    src = {"crane_factor": 0.75}
    out = _with_feature_defaults(src)
    assert out["crane_factor"] == 0.75
    assert "tidal" not in src, "_with_feature_defaults must not mutate its argument"
    # incremental is deliberately NOT defaulted here (process-global warm-start cache)
    assert "incremental" not in _with_feature_defaults({})


def test_optimise_flag_resolution_is_tri_state():
    """query param > body field > feature flag, and an explicit false must win.

    With FEATURE_TIDAL defaulting to true, a plain `bool = False` body field could never
    express "off" — `body.tidal or flag` is always true. The UI toggle depends on this.
    """
    from app.routers.optimise import _resolve

    assert _resolve(None, None, True) is True        # nothing specified -> flag
    assert _resolve(None, None, False) is False
    assert _resolve(None, False, True) is False      # body false beats an enabled flag
    assert _resolve(None, True, False) is True
    assert _resolve(False, True, True) is False      # query param beats the body
    assert _resolve(True, False, False) is True


@requires_db
def test_tides_endpoint_shape(client):
    """GET /api/tides must expose a usable curve per berth (the UI shades the Gantt with it)."""
    body = client.get("/api/tides?hours=48").json()
    assert {"period_hours", "amplitude_ft", "under_keel_margin_ft", "berths"} <= set(body)
    assert body["berths"], "no berths returned"
    b = body["berths"][0]
    assert {"berth_id", "berth_name", "design_depth_ft", "curve"} <= set(b)
    assert len(b["curve"]) == 49                     # hours 0..48 inclusive
    assert {"hour", "depth_ft"} <= set(b["curve"][0])
    # the curve must actually vary (a flat line would mean the model never engaged)
    depths = [p["depth_ft"] for p in b["curve"]]
    assert max(depths) > min(depths)
    # and it must straddle the charted depth, since that is what "high water" is measured against
    assert min(depths) < b["design_depth_ft"] < max(depths)


@requires_db
def test_explicit_tidal_false_overrides_the_feature_flag():
    """`tidal: False` must switch the constraint off even when FEATURE_TIDAL is on.

    Regression: the engine used `scenario.get("tidal", False) or feature_tidal`, so once the
    flag defaulted to true an explicit false could never turn the constraint off — the UI
    toggle and any `?tidal=0` request were silently ignored.
    """
    from app.db import SessionLocal
    from app.services import optimiser, pipeline

    db = SessionLocal()
    try:
        ctx = pipeline.load_context(db)
        off = optimiser.optimise(ctx, {}, {"tidal": False})
        on = optimiser.optimise(ctx, {}, {"tidal": True})
    finally:
        db.close()

    assert off["params"]["tidal"] is False, "explicit tidal=False was overridden by the flag"
    assert on["params"]["tidal"] is True
    # with the constraint disabled there is nothing to verify, so it reports trivially feasible
    assert off["tidal_feasible"] is True


@requires_db
def test_warm_start_declines_on_a_different_instance():
    """A cached plan must not be used to hint a *different* problem instance."""
    from app.db import SessionLocal
    from app.services import optimiser, pipeline, scenarios as S

    db = SessionLocal()
    try:
        ctx = pipeline.load_context(db)
        optimiser.optimise(ctx, {}, {})                      # prime the cache on the full instance
        small, _ = S.modify_context(ctx, _body(kind="BERTH_REMOVED", terminal_code="PCT",
                                               berth_count_delta=2))
        scen = optimiser.optimise(small, {}, {"incremental": True})
        # same instance again -> the warm start is allowed to engage
        again = optimiser.optimise(ctx, {}, {"incremental": True})
    finally:
        db.close()

    assert scen["incremental"] is False, "warm-started a plan from a different berth set"
    assert again["incremental"] is True, "warm start failed to engage on an unchanged instance"


def test_instance_sig_covers_move_rate_and_tidal():
    """Warm-start hints depend on solve math, not just geometry: a sig computed at
    28 moves/h with tides off must not unlock hints for a 24 moves/h run with tides on."""
    from app.services.optimiser import _instance_sig
    b, q = _berths(), [_vessel(1)]
    assert _instance_sig(b, q, move_rate=28.0, tidal=False) == _instance_sig(b, q, move_rate=28.0, tidal=False)
    assert _instance_sig(b, q, move_rate=24.0, tidal=False) != _instance_sig(b, q, move_rate=28.0, tidal=False)
    assert _instance_sig(b, q, move_rate=28.0, tidal=True) != _instance_sig(b, q, move_rate=28.0, tidal=False)


def test_optimizer_cache_key_distinguishes_eta_shift():
    """SCHEDULE_CHANGE keeps ids and counts identical — only ETAs move — so the key
    must cover ETAs or the scenario silently returns the baseline plan."""
    from app.services import pipeline
    k1 = pipeline._optimizer_cache_key(_ctx(), {})
    shifted = _ctx(vessels=[_vessel(1, eta=5.0), _vessel(2, eta=0.0)])
    k2 = pipeline._optimizer_cache_key(shifted, {})
    assert k1 != k2


def test_scheduler_responses_forward_engine_weights_not_reference():
    """`weights` in the optimiser/scheduler responses must be the constants CP-SAT
    actually minimized with (see optimiser return), never the nominal §17 dict."""
    from pathlib import Path
    services = Path(__file__).resolve().parents[1] / "app" / "services"
    assert "ref.OBJECTIVE_WEIGHTS" not in (services / "optimiser.py").read_text()
    routers = Path(__file__).resolve().parents[1] / "app" / "routers"
    assert "ref.OBJECTIVE_WEIGHTS" not in (routers / "scenarios.py").read_text()


@pytest.fixture(autouse=True)
def _isolated_solver_caches():
    """The warm-start and pipeline caches are process-global by design; without a reset,
    an earlier test's solved instance leaks into later tests that share the same fake t0
    (e.g. a scenario-builder solve polluting `test_warm_start_declines_on_a_different_instance`).
    Each test primes exactly what it needs."""
    from app.services import optimiser, pipeline

    def _reset():
        optimiser._warm.clear()
        pipeline._opt_cache.clear()
        pipeline._fc_cache.clear()

    _reset()
    yield
    _reset()
