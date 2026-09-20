from types import SimpleNamespace

import pytest

from app.pipelines.schedule import parse_schedule
from app.services.context import EngineContext, BerthCtx, VesselCtx
from app.services.scenarios import modify_context


def test_schedule_rejects_missing_physical_fields():
    csv = b"imo,voyage_number,declared_eta_hours,dest_zone_code\nIMO123,V1,8,Z-LBCT\n"
    result = parse_schedule(csv)
    assert result["rows"] == 1
    assert result["accepted"] == []
    assert result["rejected"][0]["row_no"] == 2
    assert "loa_ft" in result["rejected"][0]["error"] or "beam_ft" in result["rejected"][0]["error"]


def test_schedule_accepts_complete_physical_record():
    csv = (
        b"imo,voyage_number,declared_eta_hours,loa_ft,beam_ft,draft_ft,teu_capacity,"
        b"import_moves,export_moves,dest_zone_code\n"
        b"IMO123,V1,8,1100,150,48,8000,2000,1800,Z-LBCT\n"
    )
    result = parse_schedule(csv)
    assert result["rows"] == 1
    assert len(result["accepted"]) == 1
    assert result["accepted"][0]["draft_ft"] == 48.0


def test_scenario_changes_context_version_for_bunching():
    vessel = VesselCtx(1, "123", "IMO1", "V1", "Carrier", "ULCV", 1100, 150, 48, 8000,
                       2000, 1800, "Origin", 0, "ANCHORAGE", "Anchorage", 8.0, None, 4.0,
                       "Z-LBCT", 1.0, False)
    berth = BerthCtx(1, "B-1", 1, 1400, 50, 4, "LBCT", "LBCT", "Pier E", "Z-LBCT")
    ctx = EngineContext(None, [], [berth], [vessel], data_version="baseline")
    body = SimpleNamespace(kind="BUNCHING", bunching_vessels=2, terminal_code=None,
                           berth_count_delta=0, crane_factor=1.0, move_rate_per_crane_hour=28.0,
                           schedule_shift_hours=-6.0)
    changed, _ = modify_context(ctx, body)
    assert len(changed.vessels) == 3
    assert changed.data_version != ctx.data_version


def test_unknown_scenario_kind_is_rejected():
    ctx = EngineContext(None, [], [], [], data_version="baseline")
    body = SimpleNamespace(kind="MAGIC", bunching_vessels=0, terminal_code=None,
                           berth_count_delta=0, crane_factor=1.0, move_rate_per_crane_hour=28.0,
                           schedule_shift_hours=-6.0)
    with pytest.raises(ValueError):
        modify_context(ctx, body)
