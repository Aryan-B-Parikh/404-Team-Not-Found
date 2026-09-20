"""W2 tests — forecasting / anomaly / hotspot / confidence / weather.

Unit tests need no database. API + seeded-data tests are gated by ``requires_db``
so `pytest` still passes on a machine without PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import numpy as np
import pytest

from app.services import forecasting as fc
from app.services import weather_adjust as wa
from app.services import hotspot as hs
from app.services.anomaly import MIN_SAMPLES, detect_anomalies
from app.services.context import BerthCtx, EngineContext, TerminalCtx

from .conftest import requires_db

pytestmark = pytest.mark.slow  # LightGBM training tests

T0 = datetime(2024, 8, 17, 0, 0, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- helpers
def _history(n, index=60.0):
    return [SimpleNamespace(index=index, queue_count=10, avg_wait_hours=24.0,
                            yard_util_pct=70.0, hours_ago=n - 1 - i) for i in range(n)]


def _fake_settings(weather: bool):
    return lambda: SimpleNamespace(
        feature_weather=weather, feature_quality=False, feature_upload=False,
        feature_tidal=False, feature_incremental=False, feature_scenarios_ext=False)


def _weather_rows(n=24, gust=45.0):
    return [{"hours_ahead": h, "hours_ago": -h, "wind_kn": 30.0, "gust_kn": gust,
             "wave_m": 4.0, "visibility_km": 2.0} for h in range(1, n + 1)]


def _fc_points(n=72, index=60.0):
    return [fc.ForecastPoint(hour=h, ts=T0 + timedelta(hours=h), index=index, queue=10.0,
                             wait=24.0, yard_util=70.0, lo=index - 8, hi=index + 8)
            for h in range(1, n + 1)]


# --------------------------------------------------------------------------- confidence
def test_confidence_bounds_and_monotonic():
    holdout = {"skill_pct": 20.0, "r2": 0.5}
    full = fc._compute_confidence(_history(336), 5.0, holdout, False, False)
    sparse = fc._compute_confidence(_history(96), 5.0, holdout, False, False)
    wide = fc._compute_confidence(_history(336), 30.0, holdout, False, False)
    assert 0.05 <= full <= 0.98
    assert full > sparse, "more history must raise confidence"
    assert full > wide, "wider bands must lower confidence"


def test_confidence_weather_requested_unavailable_is_lower():
    on = fc._compute_confidence(_history(336), 5.0, {"skill_pct": 20.0}, False, True)
    off = fc._compute_confidence(_history(336), 5.0, {"skill_pct": 20.0}, False, False)
    assert on < off


# --------------------------------------------------------------------------- horizons
def test_horizon_summary_covers_24_48_72():
    points = _fc_points(index=50.0)
    points[47].index = 90.0  # peak inside the 48h bucket
    out = fc._horizon_summary(points)
    assert set(out) == {"h24", "h48", "h72"}
    assert out["h48"]["peak_index"] == 90.0
    assert out["h48"]["peak_hour"] == 48


# --------------------------------------------------------------------------- weather
# apply_weather_adjustment lives in weather_adjust.py; patch its settings accessor,
# not forecasting's re-export (a module attribute patch never follows aliases).
def test_weather_off_leaves_forecast_untouched(monkeypatch):
    monkeypatch.setattr(wa, "get_settings", _fake_settings(False))
    result = fc.ForecastResult(zone_code="Z-LBCT", zone_name="LBCT", points=_fc_points())
    assert fc.apply_weather_adjustment(result, _weather_rows()) is False
    assert result.weather_used is False


def test_weather_on_adjusts_and_widens(monkeypatch):
    monkeypatch.setattr(wa, "get_settings", _fake_settings(True))
    points = _fc_points(index=60.0)
    before_lo = points[0].lo
    result = fc.ForecastResult(zone_code="Z-LBCT", zone_name="LBCT", points=points)
    assert fc.apply_weather_adjustment(result, _weather_rows()) is True
    assert result.weather_used is True
    assert points[0].index > 60.0
    assert points[0].lo < before_lo
    assert any(d["label"] == "Adverse weather" for d in result.drivers)


def test_weather_loader_without_db_is_empty():
    assert fc.load_weather_series(None) == []


# --------------------------------------------------------------------------- sparse forecast
def test_sparse_history_uses_low_confidence_baseline():
    result = fc.forecast_zone("Z-LBCT", "LBCT", _history(20), [], 
                              {"berths": 3, "cranes": 18, "berth_length_ft": 4200}, T0)
    assert len(result.points) == 72
    assert "baseline" in result.model["algorithm"]
    assert result.confidence < 0.6
    assert all(p.lo <= p.index <= p.hi for p in result.points)
    assert all(p.queue_lo <= p.queue <= p.queue_hi for p in result.points)
    assert all(p.wait_lo <= p.wait <= p.wait_hi for p in result.points)
    assert all(p.yard_lo <= p.yard_util <= p.yard_hi for p in result.points)


# --------------------------------------------------------------------------- anomaly
def _ctx(history, zones=("Z-LBCT",)):
    return EngineContext(t0=T0, terminals=[], berths=[], vessels=[], history={z: history for z in zones})


def test_anomaly_insufficient_data_is_flagged():
    flags = detect_anomalies(_ctx(_history(MIN_SAMPLES - 1)))
    assert flags and flags[0]["kind"] == "INSUFFICIENT_DATA"
    assert flags[0]["is_anomaly"] is False


def test_anomaly_shape_and_no_error_on_normal_history():
    flags = detect_anomalies(_ctx(_history(200, index=50.0)))
    assert len(flags) == 1
    f = flags[0]
    assert {"zone_code", "kind", "method", "score", "is_anomaly", "sample_size", "detail",
            "features", "confidence", "window_hours"} <= set(f)
    assert f["window_hours"] == 72


def test_recent_outage_is_detected():
    """A sustained outage inside the 72h window must surface (AUDIT B9 regression, no DB)."""
    n = 336
    hist = []
    for i in range(n):
        hours_ago = n - 1 - i
        idx = 45.0 + 3.0 * np.sin(i / 24.0)
        q, wait = 8, 20.0
        if 36 <= hours_ago <= 72:  # outage window
            idx += 25
            q += 6
            wait += 25
        hist.append(SimpleNamespace(index=idx, queue_count=q, avg_wait_hours=wait,
                                    yard_util_pct=60.0, hours_ago=hours_ago))
    flags = detect_anomalies(_ctx(hist))
    assert flags[0]["is_anomaly"] is True
    assert flags[0]["kind"] != "DATA_ERROR"


# --------------------------------------------------------------------------- hotspot
def _terminal(code="LBCT", zone="Z-LBCT"):
    return TerminalCtx(id=1, code=code, name=code, pier="Pier", lat=None, lon=None,
                       berth_length_ft=4200, deepsea_berths=3, gantry_cranes=18,
                       capacity_teu_m=None, zone_code=zone, note=None)


def _berth(cranes_max, zone="Z-LBCT", code="LBCT"):
    return BerthCtx(id=1, name="A-1", seq=1, length_ft=1400, depth_ft=50.0, cranes_max=cranes_max,
                    terminal_code=code, terminal_name=code, pier="Pier", zone_code=zone)


def _forecast(zone="Z-LBCT", index=60.0, queue=10.0, yard=50.0, confidence=0.8):
    points = [SimpleNamespace(index=index, queue=queue, yard_util=yard, lo=index - 5, hi=index + 5, hour=12)]
    return SimpleNamespace(zone_code=zone, zone_name=zone, points=points, confidence=confidence)


def _hotspot_ctx(gate_queue=0, yard_util=None, cranes=None, berth_cranes_max=100):
    return EngineContext(
        t0=T0, terminals=[_terminal()], berths=[_berth(berth_cranes_max)], vessels=[],
        history={"Z-LBCT": _history(48, index=50.0)}, cranes=cranes or {},
        yard_util=yard_util or {}, gate_queue={"LBCT": gate_queue}, dataset_source="DEMO_AIS")


def test_hotspot_binding_berth():
    ctx = _hotspot_ctx()
    out = hs.compute_hotspots(ctx, {"Z-LBCT": _forecast(queue=30.0, yard=20.0)}, [])
    assert out["ranked"][0]["binding_constraint"] == "BERTH"


def test_hotspot_binding_crane():
    ctx = _hotspot_ctx(berth_cranes_max=1)
    out = hs.compute_hotspots(ctx, {"Z-LBCT": _forecast(queue=3.0, yard=20.0)}, [])
    assert out["ranked"][0]["binding_constraint"] == "CRANE"


def test_hotspot_binding_yard():
    ctx = _hotspot_ctx()
    out = hs.compute_hotspots(ctx, {"Z-LBCT": _forecast(queue=0.0, yard=95.0)}, [])
    assert out["ranked"][0]["binding_constraint"] == "YARD"


def test_hotspot_binding_gate_and_nominal_gate_suppressed():
    # an implausibly huge gate queue vs real throughput becomes binding ...
    ctx = _hotspot_ctx(gate_queue=400)
    out = hs.compute_hotspots(ctx, {"Z-LBCT": _forecast(queue=0.0, yard=10.0)}, [])
    assert out["ranked"][0]["binding_constraint"] == "GATE"
    # ... but an ordinary gate queue must NOT dominate any more (AUDIT B10)
    nominal = _hotspot_ctx(gate_queue=18)
    out2 = hs.compute_hotspots(nominal, {"Z-LBCT": _forecast(queue=9.0, yard=60.0)}, [])
    assert out2["ranked"][0]["binding_constraint"] != "GATE"
    assert "binding_evidence" in out2["ranked"][0]


def test_hotspot_confidence_folds_in_forecast_confidence():
    ctx = _hotspot_ctx()
    hi = hs.compute_hotspots(ctx, {"Z-LBCT": _forecast(confidence=0.95)}, [])["ranked"][0]["confidence"]
    lo = hs.compute_hotspots(ctx, {"Z-LBCT": _forecast(confidence=0.3)}, [])["ranked"][0]["confidence"]
    assert hi > lo


# --------------------------------------------------------------------------- API (DB)
@requires_db
def test_forecast_api_additive_keys(client):
    body = client.get("/api/forecast?zone=Z-PORT").json()
    assert {"t0", "dataset_source", "summary", "selected", "weather_used", "confidence"} <= set(body)
    assert 0.0 <= body["confidence"] <= 1.0
    assert isinstance(body["weather_used"], bool)
    assert set(body["confidence_by_horizon"]) == {"h24", "h48", "h72"}
    assert {"model_version", "data_version", "feature_flags"} <= set(body["provenance"])
    assert len(body["selected"]["points"]) == 72
    p0 = body["selected"]["points"][0]
    assert {"queue_lo", "queue_hi", "wait_lo", "wait_hi", "yard_lo", "yard_hi"} <= set(p0)
    assert p0["queue_lo"] <= p0["queue"] <= p0["queue_hi"]


@requires_db
def test_forecast_invalid_zone_400(client):
    assert client.get("/api/forecast?zone=NOPE").status_code == 400


@requires_db
def test_anomalies_api_additive_keys(client):
    body = client.get("/api/anomalies").json()
    assert "anomalies" in body
    assert {"weather_used", "method", "generated_at"} <= set(body)


@requires_db
def test_pct_outage_is_detected(client):
    """AUDIT B9 regression: the injected PCT crane outage must surface as an anomaly."""
    body = client.get("/api/anomalies").json()
    pct = [a for a in body["anomalies"] if a["zone_code"] == "Z-PCT"]
    assert pct, "expected a Z-PCT anomaly row"
    assert pct[0]["is_anomaly"] is True
