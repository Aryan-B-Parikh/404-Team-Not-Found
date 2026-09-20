"""Response models for the main read endpoints (backlog B-7 step 0).

Most service-layer builders return plain dicts; without a ``response_model``
FastAPI's OpenAPI output for those routes is generic, so the frontend contract
lives only in hand-written TypeScript. These models make the contract real and
machine-readable. ``model_config = ConfigDict(extra="forbid")`` is deliberate:
if the backend grows a field the model does not declare, the endpoint *fails
loudly in tests* instead of silently dropping the field from every client.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------- overview
class Dataset(_Strict):
    source: str
    note: str


class Kpis(_Strict):
    port_index_now: float
    berth_util_pct: float
    crane_util_pct: float
    vessels_at_anchor: float
    vessels_inbound: float
    avg_anchorage_wait: float
    max_anchored_hours: float
    arrivals_next24: float
    moves_pending: float
    daily_fleet_burn_usd: float
    peak_forecast_index: float
    peak_forecast_hour: float


class Zone(_Strict):
    zone_code: str
    label: str
    level: str
    trend: str
    current_index: float
    peak_index: float
    peak_hour: float
    recent_index: list[float]  # recent index series, not a scalar
    queue_now: float
    wait_now: float
    berths: float
    cranes: float
    yard_util_pct: float


class Alert(_Strict):
    severity: str
    title: str
    detail: str
    hour: float | None = None  # absent on non-timeline alerts (anchorage, anomaly)


class Hotspot(_Strict):
    zone_code: str
    zone_name: str
    risk_score: float
    confidence: float
    peak_index: float
    peak_hour: float
    binding_constraint: str
    binding_evidence: dict[str, Any]
    resource_pressure: dict[str, Any]
    explanation: str
    components: dict[str, Any]
    weights: dict[str, Any]


class Hotspots(_Strict):
    ranked: list[Hotspot]
    most_actionable: Hotspot | None = None
    method: str | None = None


class Arrival(_Strict):
    hour: int
    count: int


class Overview(_Strict):
    t0: str
    dataset: Dataset
    data_version: str
    weather_used: bool
    confidence: float
    kpis: Kpis
    zones: list[Zone]
    alerts: list[Alert]
    hotspots: Hotspots
    # flag dicts (zone/kind/score/detail/...); pinned in depth by /api/anomalies below
    anomalies: list[dict[str, Any]]
    arrivals_timeline: list[Arrival]
    last_updated: str


# --------------------------------------------------------------- anomalies
class AnomalyFlag(_Strict):
    zone_code: str
    kind: str
    method: str
    score: float
    is_anomaly: bool
    sample_size: int
    detail: str
    confidence: float
    window_hours: int
    features: dict[str, Any] | None = None
    weather_used: bool | None = None


class AnomaliesResponse(_Strict):
    anomalies: list[AnomalyFlag]
    method: str
    generated_at: str
    weather_used: bool


# --------------------------------------------------------------------- plan
class PlanResponse(_Strict):
    """Spec §6 traceability: the plan exposes the snapshot that produced it."""

    summary: dict[str, Any]
    shifts: list[dict[str, Any]]
    text: str
    narrative_source: str
    plan_id: int | None = None
    created_at: str | None = None  # ISO timestamp of the persisted plan row
    forecast_run_id: int | None = None
    optimiser_run_id: int | None = None


# ---------------------------------------------------------------- optimise
class OptimiseLatest(_Strict):
    run_id: int | None = None
    solver: str
    status: str
    objective: float | None = None
    solve_ms: int
    assignments: list[dict[str, Any]]
    metrics: dict[str, Any]
    baseline: dict[str, Any]
    deltas: dict[str, Any]
    deferred: list[dict[str, Any]]
    weights: dict[str, Any]
    tidal_feasible: bool = True
    incremental: bool = False
    gap_pct: float | None = None
    # POST /optimise returns the raw engine output, which also carries these;
    # GET /optimise/latest builds its dict without them (defaults keep both valid).
    horizon_hours: int | None = None
    params: dict[str, Any] | None = None


# ---------------------------------------------------------------- forecast
class ForecastResponse(_Strict):
    t0: str
    dataset_source: str
    summary: dict[str, Any]                      # per-zone {zone_name, current, peak, avg_index}
    selected: dict[str, Any]                     # points[] + bands + confidence detail
    hotspots: Hotspots
    anomalies: list[dict[str, Any]]
    weather_used: bool
    confidence: float
    confidence_by_horizon: dict[str, Any]
    horizons: dict[str, Any]                    # h24/h48/h72 → per-horizon peak metrics
    provenance: dict[str, Any]                   # model_version / data_version / feature_flags


# ----------------------------------------------------------------- catalog
class TerminalsResponse(_Strict):
    terminals: list[dict[str, Any]]
    source: str


class VesselsResponse(_Strict):
    vessels: list[dict[str, Any]]


# ----------------------------------------------------------------- routing
class RoutingResponse(_Strict):
    recommendations: list[dict[str, Any]]
    counts: dict[str, int]
    total_savings_usd: float
    cost_model: dict[str, Any]


# ----------------------------------------------------------------- quality
class QualityResponse(_Strict):
    """Read-only snapshot (B-5): normalisation writes live at startup + POST /quality/refresh."""

    terminals: list[dict[str, Any]]
    rules_version: str
    last_run_at: str | None = None
    stub: bool = False


class WeatherResponse(_Strict):
    points: list[dict[str, Any]]
    source: str
    hours: int
    stub: bool = False


# --------------------------------------------------------------------- bob
class BobHistoryResponse(_Strict):
    messages: list[dict[str, Any]]


class BobAnswerResponse(_Strict):
    content: str
    actions: list[Any]
    mode: str
    provider: str
    intent: str
    grounded: bool = True  # False only when the primary agent path failed the tool-evidence gate


# --------------------------------------------------------------- scenarios
class ScenarioResponse(_Strict):
    scenario_id: int
    params: dict[str, Any]
    baseline: dict[str, Any]
    scenario: dict[str, Any]
    impact: dict[str, Any]
    weights: dict[str, Any]
    solver: dict[str, Any]


class ScenarioExtendedResponse(_Strict):
    baseline: dict[str, Any]
    scenario: dict[str, Any]
    impact: dict[str, Any]
    feasible: bool
    kind: str
    parent_scenario_id: int | None = None
    scenario_id: int
    description: str
    forecast: dict[str, Any]
    solver: dict[str, Any]
    weights: dict[str, Any]


class ScenarioRollbackResponse(_Strict):
    restored: bool
    scenario_id: int
    status: str


# ---------------------------------------------------------------------- ais
class AisStatusResponse(_Strict):
    source: str
    rows: int
    zones: int
    track_points: int
    newest_ts: str | None = None
    oldest_ts: str | None = None
    stub: bool = False


class AisGenerateResponse(_Strict):
    """Keys = build stats + import stats + generator params (all declared)."""

    status: str
    source: str
    message: str
    rows_scanned: int
    skipped: int
    vessels: int
    hours: float
    output_rows: int
    inserted: int
    is_measured: bool
    zones: int
    newest_ts: str
    days: int
    seed: int
    stub: bool = False


# -------------------------------------------------------------------- tides
class TidesResponse(_Strict):
    period_hours: float
    amplitude_ft: float
    under_keel_margin_ft: float
    source: str
    berths: list[dict[str, Any]]


# ------------------------------------------------------------------- upload
class UploadResponse(_Strict):
    """Both upload paths: the parse-failure path omits normalised_rows/replan."""

    accepted: int
    rejected: int
    errors: list[str]
    revisions_created: int
    normalised_rows: int | None = None
    upload_id: int | None = None
    filename: str | None = None
    bytes: int | None = None
    stub: bool = False
    replan: dict[str, Any] | None = None


# --------------------------------------------------------------- bob / meta
class BobStatusResponse(_Strict):
    provider: str
    configured: bool
    cli_available: bool
    mcp: str
    tools: int
    fallback: str


class HealthResponse(_Strict):
    status: str
