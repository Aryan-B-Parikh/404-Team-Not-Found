"""SQLAlchemy ORM models — the PortPulse AI data model.

Implements the entity flow from the requirements doc §18:
  Terminal -> Berth/Crane/YardZone/Gate -> VesselCall (+EtaRevision)
  -> CongestionObservation -> ForecastRun -> HotspotFlag / AnomalyFlag
  -> OptimiserRun -> Assignment / RoutingRecommendation
  -> OperationsPlan -> Scenario -> ImpactAssessment (+ ChatMessage)

Real vs. demo discipline is preserved: terminal capacity columns are REAL Port
of Long Beach fact-sheet figures; vessel calls + hourly congestion history are
the labelled DEMO_AIS synthetic layer produced by the SimPy simulation
(source = "DEMO_AIS") unless replaced by the AIS pipeline (source = "AIS").
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


# --------------------------------------------------------------------------- A/C
class Terminal(Base):
    __tablename__ = "terminal"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)          # LBCT | ITS | PCT | TTI
    name: Mapped[str] = mapped_column(String(160))
    pier: Mapped[str] = mapped_column(String(40))
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    berth_length_ft: Mapped[int] = mapped_column(Integer)               # REAL (POLB fact sheet)
    deepsea_berths: Mapped[int] = mapped_column(Integer)                # REAL
    gantry_cranes: Mapped[int] = mapped_column(Integer)                 # REAL
    capacity_teu_m: Mapped[float | None] = mapped_column(Float)         # REAL where published
    zone_code: Mapped[str] = mapped_column(String(16), index=True)
    note: Mapped[str | None] = mapped_column(Text)
    config_version: Mapped[int] = mapped_column(Integer, default=1)     # versioned configuration
    raw: Mapped[dict | None] = mapped_column(JSONB)                     # original unit/value payload

    berths: Mapped[list["Berth"]] = relationship(back_populates="terminal", cascade="all,delete")
    cranes: Mapped[list["Crane"]] = relationship(back_populates="terminal", cascade="all,delete")
    yard_zones: Mapped[list["YardZone"]] = relationship(back_populates="terminal", cascade="all,delete")
    gates: Mapped[list["Gate"]] = relationship(back_populates="terminal", cascade="all,delete")


class Berth(Base):
    __tablename__ = "berth"
    __table_args__ = (UniqueConstraint("terminal_id", "name", name="uq_berth_terminal_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    terminal_id: Mapped[int] = mapped_column(ForeignKey("terminal.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(40))
    seq: Mapped[int] = mapped_column(Integer)
    length_ft: Mapped[int] = mapped_column(Integer)      # physical hard constraint
    depth_ft: Mapped[float] = mapped_column(Float)       # alongside design draft (hard constraint)
    cranes_max: Mapped[int] = mapped_column(Integer)     # max simultaneous STS cranes

    terminal: Mapped[Terminal] = relationship(back_populates="berths")


class Crane(Base):
    __tablename__ = "crane"

    id: Mapped[int] = mapped_column(primary_key=True)
    terminal_id: Mapped[int] = mapped_column(ForeignKey("terminal.id", ondelete="CASCADE"), index=True)
    berth_id: Mapped[int | None] = mapped_column(ForeignKey("berth.id", ondelete="SET NULL"))
    code: Mapped[str] = mapped_column(String(40))
    crane_type: Mapped[str] = mapped_column(String(40), default="STS")   # STS | dual-hoist | tandem
    reach_ft: Mapped[float] = mapped_column(Float, default=200.0)        # outreach (hard constraint vs beam)
    rated_moves_per_hour: Mapped[float] = mapped_column(Float, default=30.0)
    status: Mapped[str] = mapped_column(String(16), default="AVAILABLE")  # AVAILABLE | MAINTENANCE | DOWN
    status_reason: Mapped[str | None] = mapped_column(String(120))        # planned vs unplanned (C req.)

    terminal: Mapped[Terminal] = relationship(back_populates="cranes")


class YardZone(Base):
    __tablename__ = "yard_zone"
    __table_args__ = (UniqueConstraint("terminal_id", "code", name="uq_yard_terminal_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    terminal_id: Mapped[int] = mapped_column(ForeignKey("terminal.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(24))
    ground_slots_teu: Mapped[int] = mapped_column(Integer)
    reefer_plugs: Mapped[int] = mapped_column(Integer)
    used_teu: Mapped[int] = mapped_column(Integer, default=0)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    terminal: Mapped[Terminal] = relationship(back_populates="yard_zones")


class Gate(Base):
    __tablename__ = "gate"

    id: Mapped[int] = mapped_column(primary_key=True)
    terminal_id: Mapped[int] = mapped_column(ForeignKey("terminal.id", ondelete="CASCADE"), index=True)
    lanes: Mapped[int] = mapped_column(Integer)
    trucks_per_hour: Mapped[float] = mapped_column(Float)
    queue_len: Mapped[int] = mapped_column(Integer, default=0)
    open_hours: Mapped[str] = mapped_column(String(40), default="06:00-18:00")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    terminal: Mapped[Terminal] = relationship(back_populates="gates")


# --------------------------------------------------------------------------- B
class VesselCall(Base):
    __tablename__ = "vessel_call"

    id: Mapped[int] = mapped_column(primary_key=True)
    imo: Mapped[str | None] = mapped_column(String(16), index=True)
    mmsi: Mapped[str | None] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    carrier: Mapped[str] = mapped_column(String(80))
    service_string: Mapped[str | None] = mapped_column(String(40))
    vessel_class: Mapped[str] = mapped_column(String(24))          # ULCV | POST_PANAMAX | ...
    loa_ft: Mapped[int] = mapped_column(Integer)
    beam_ft: Mapped[int] = mapped_column(Integer)
    draft_ft: Mapped[float] = mapped_column(Float)
    teu_capacity: Mapped[int] = mapped_column(Integer)
    import_moves: Mapped[int] = mapped_column(Integer)
    export_moves: Mapped[int] = mapped_column(Integer)
    origin_port: Mapped[str] = mapped_column(String(80))
    reefer_units: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))                # ANCHORAGE | DRIFTING | INBOUND
    anchorage_zone: Mapped[str | None] = mapped_column(String(80))
    # ETAs are FORECASTS, not facts: carrier-declared vs AIS-derived are stored apart (B req.)
    declared_eta_hours: Mapped[float] = mapped_column(Float)
    ais_eta_hours: Mapped[float | None] = mapped_column(Float)
    etd_hours: Mapped[float | None] = mapped_column(Float)
    anchored_hours: Mapped[float] = mapped_column(Float)
    dest_zone_code: Mapped[str] = mapped_column(String(16), index=True)
    unresolved: Mapped[bool] = mapped_column(Boolean, default=False)   # missing/incomplete data flag
    data_confidence: Mapped[float] = mapped_column(Float, default=1.0) # 0..1 record quality
    raw: Mapped[dict | None] = mapped_column(JSONB)                    # original units/values
    # --- Phase 0 freeze (W1): schedule dedupe key + unit-normalisation ledger ---
    voyage_number: Mapped[str | None] = mapped_column(String(40), index=True)
    normalised: Mapped[dict | None] = mapped_column(JSONB)             # {field: {original, unit, value_si}}

    @property
    def eta_hours(self) -> float:
        """Effective ETA: prefer AIS-derived when present, else carrier-declared."""
        return self.ais_eta_hours if self.ais_eta_hours is not None else self.declared_eta_hours

    revisions: Mapped[list["EtaRevision"]] = relationship(back_populates="vessel", cascade="all,delete")


class EtaRevision(Base):
    __tablename__ = "eta_revision"

    id: Mapped[int] = mapped_column(primary_key=True)
    vessel_call_id: Mapped[int] = mapped_column(ForeignKey("vessel_call.id", ondelete="CASCADE"), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source: Mapped[str] = mapped_column(String(16), default="CARRIER")   # CARRIER | AIS | MANUAL
    eta_hours: Mapped[float] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(String(160))

    vessel: Mapped[VesselCall] = relationship(back_populates="revisions")


# --------------------------------------------------------------------------- E/D
class CongestionObservation(Base):
    __tablename__ = "congestion_observation"
    __table_args__ = (
        UniqueConstraint("zone_code", "hours_ago", name="uq_obs_zone_hours"),
        Index("ix_obs_zone_ts", "zone_code", "ts"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    zone_code: Mapped[str] = mapped_column(String(16))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    hours_ago: Mapped[int] = mapped_column(Integer)         # 0 = most recent
    queue_count: Mapped[int] = mapped_column(Integer)
    avg_wait_hours: Mapped[float] = mapped_column(Float)
    index: Mapped[float] = mapped_column(Float)             # composite congestion index 0..100
    yard_util_pct: Mapped[float | None] = mapped_column(Float)   # yard-utilisation target (F req.)
    source: Mapped[str] = mapped_column(String(16), default="DEMO_AIS")  # DEMO_AIS | AIS
    is_measured: Mapped[bool] = mapped_column(Boolean, default=False)    # measured vs estimated (D req.)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)        # per-record quality (D req.)
    raw: Mapped[dict | None] = mapped_column(JSONB)                      # original value/unit (D req.)


# --------------------------------------------------------------------------- F/G/H
class ForecastRun(Base):
    __tablename__ = "forecast_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_version: Mapped[str] = mapped_column(String(64))     # reproducibility (F req.)
    algorithm: Mapped[str] = mapped_column(String(80), default="LightGBM")
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    horizon_hours: Mapped[int] = mapped_column(Integer, default=72)
    metrics: Mapped[dict | None] = mapped_column(JSONB)        # per-zone MAE/R2/skill + quantile coverage
    # --- Phase 0 freeze (W2): provenance/registry ---
    data_version: Mapped[str | None] = mapped_column(String(64))
    feature_flags: Mapped[dict | None] = mapped_column(JSONB)

    points: Mapped[list["ForecastPoint"]] = relationship(back_populates="run", cascade="all,delete")
    hotspots: Mapped[list["HotspotFlag"]] = relationship(back_populates="run", cascade="all,delete")


class ForecastPoint(Base):
    __tablename__ = "forecast_point"
    __table_args__ = (UniqueConstraint("run_id", "zone_code", "hour", name="uq_fc_run_zone_hour"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("forecast_run.id", ondelete="CASCADE"), index=True)
    zone_code: Mapped[str] = mapped_column(String(16))
    hour: Mapped[int] = mapped_column(Integer)                  # 1..72
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    index: Mapped[float] = mapped_column(Float)
    queue: Mapped[float] = mapped_column(Float)
    wait: Mapped[float] = mapped_column(Float)
    yard_util_pct: Mapped[float | None] = mapped_column(Float)
    lo: Mapped[float] = mapped_column(Float)                    # uncertainty band (quantile)
    hi: Mapped[float] = mapped_column(Float)

    run: Mapped[ForecastRun] = relationship(back_populates="points")


class HotspotFlag(Base):
    __tablename__ = "hotspot_flag"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("forecast_run.id", ondelete="CASCADE"), index=True)
    zone_code: Mapped[str] = mapped_column(String(16))
    hour: Mapped[int] = mapped_column(Integer)
    index: Mapped[float] = mapped_column(Float)
    risk_score: Mapped[float] = mapped_column(Float)            # w1..w5 composite (G req.)
    binding_constraint: Mapped[str] = mapped_column(String(24))  # BERTH | CRANE | YARD | GATE
    components: Mapped[dict | None] = mapped_column(JSONB)      # w1..w5 contributions + evidence
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[ForecastRun] = relationship(back_populates="hotspots")


class AnomalyFlag(Base):
    __tablename__ = "anomaly_flag"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    zone_code: Mapped[str] = mapped_column(String(16), index=True)
    kind: Mapped[str] = mapped_column(String(32))               # BUNCHING | OUTAGE | WEATHER | LABOUR
    method: Mapped[str] = mapped_column(String(40), default="IsolationForest")
    score: Mapped[float] = mapped_column(Float)                 # anomaly score (lower = more anomalous)
    is_anomaly: Mapped[bool] = mapped_column(Boolean)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    detail: Mapped[str | None] = mapped_column(Text)
    features: Mapped[dict | None] = mapped_column(JSONB)


# --------------------------------------------------------------------------- J
class OptimiserRun(Base):
    __tablename__ = "optimiser_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    solver: Mapped[str] = mapped_column(String(40), default="ortools-cp-sat")   # exact solver (J req.)
    status: Mapped[str] = mapped_column(String(24), default="OPTIMAL")
    objective: Mapped[float | None] = mapped_column(Float)
    solve_ms: Mapped[int | None] = mapped_column(Integer)
    params: Mapped[dict | None] = mapped_column(JSONB)
    metrics: Mapped[dict | None] = mapped_column(JSONB)
    baseline: Mapped[dict | None] = mapped_column(JSONB)         # FIFO baseline metrics
    deltas: Mapped[dict | None] = mapped_column(JSONB)
    deferred: Mapped[list | None] = mapped_column(JSONB)
    weights: Mapped[dict | None] = mapped_column(JSONB)          # exposed objective weights (J req.)

    assignments: Mapped[list["Assignment"]] = relationship(back_populates="run", cascade="all,delete")


class Assignment(Base):
    __tablename__ = "assignment"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("optimiser_run.id", ondelete="CASCADE"), index=True)
    vessel_call_id: Mapped[int] = mapped_column(ForeignKey("vessel_call.id", ondelete="CASCADE"))
    berth_id: Mapped[int] = mapped_column(ForeignKey("berth.id", ondelete="CASCADE"))
    start_hour: Mapped[float] = mapped_column(Float)
    end_hour: Mapped[float] = mapped_column(Float)
    cranes: Mapped[int] = mapped_column(Integer)
    wait_hours: Mapped[float] = mapped_column(Float)
    priority_score: Mapped[float] = mapped_column(Float)
    sequence: Mapped[int] = mapped_column(Integer, default=0)

    run: Mapped[OptimiserRun] = relationship(back_populates="assignments")


# --------------------------------------------------------------------------- I
class RoutingRecommendation(Base):
    __tablename__ = "routing_recommendation"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    vessel_call_id: Mapped[int] = mapped_column(ForeignKey("vessel_call.id", ondelete="CASCADE"), index=True)
    option: Mapped[str] = mapped_column(String(20))              # DIVERT | SLOW_STEAM | PRIORITY_WINDOW | HOLD
    target_port: Mapped[str | None] = mapped_column(String(80))
    eta_shift_hours: Mapped[float] = mapped_column(Float, default=0)
    predicted_wait_hours: Mapped[float] = mapped_column(Float)
    est_savings_usd: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    tier: Mapped[str] = mapped_column(String(16))
    rationale: Mapped[str | None] = mapped_column(Text)
    sustained: Mapped[bool] = mapped_column(Boolean, default=False)   # sustained congestion, not 1 noisy pt
    # --- Phase 0 freeze (W3): in-port terminal / berthing-window detail ---
    option_detail: Mapped[dict | None] = mapped_column(JSONB)


# --------------------------------------------------------------------------- K/L
class OperationsPlan(Base):
    __tablename__ = "operations_plan"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    horizon_hours: Mapped[int] = mapped_column(Integer, default=72)
    forecast_run_id: Mapped[int | None] = mapped_column(ForeignKey("forecast_run.id", ondelete="SET NULL"))
    optimiser_run_id: Mapped[int | None] = mapped_column(ForeignKey("optimiser_run.id", ondelete="SET NULL"))
    summary: Mapped[dict | None] = mapped_column(JSONB)
    shifts: Mapped[list | None] = mapped_column(JSONB)
    text_plan: Mapped[str] = mapped_column(Text)
    narrative_source: Mapped[str] = mapped_column(String(16), default="deterministic")  # llm | deterministic
    # --- Phase 0 freeze (W3): per-horizon confidence ---
    confidence_json: Mapped[dict | None] = mapped_column(JSONB)


class Scenario(Base):
    __tablename__ = "scenario"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    name: Mapped[str] = mapped_column(String(120))
    base_run_id: Mapped[int | None] = mapped_column(ForeignKey("optimiser_run.id", ondelete="SET NULL"))
    params: Mapped[dict | None] = mapped_column(JSONB)
    kind: Mapped[str] = mapped_column(String(24), default="CRANE_OUTAGE")
    # --- Phase 0 freeze (W3): clone lineage + rollback state ---
    parent_scenario_id: Mapped[int | None] = mapped_column(ForeignKey("scenario.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")   # DRAFT | APPLIED | ROLLED_BACK


class ImpactAssessment(Base):
    __tablename__ = "impact_assessment"

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    baseline: Mapped[dict | None] = mapped_column(JSONB)
    scenario: Mapped[dict | None] = mapped_column(JSONB)
    deltas: Mapped[dict | None] = mapped_column(JSONB)
    feasible: Mapped[bool] = mapped_column(Boolean, default=True)


# --------------------------------------------------------------------------- M
class ChatMessage(Base):
    __tablename__ = "chat_message"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    role: Mapped[str] = mapped_column(String(16))               # user | assistant
    content: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict | None] = mapped_column(JSONB)            # actions, mode (llm|deterministic), evidence


# ===========================================================================
# Phase 0 interface freeze — new tables owned by W1 / W3.
# ===========================================================================
class WeatherObservation(Base):
    """W1: Open-Meteo wind/wave/visibility series for San Pedro Bay."""

    __tablename__ = "weather_observation"
    __table_args__ = (UniqueConstraint("hours_ago", name="uq_weather_hours"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    hours_ago: Mapped[int] = mapped_column(Integer)             # 0 = now, negative = forecast ahead
    wind_kn: Mapped[float | None] = mapped_column(Float)
    gust_kn: Mapped[float | None] = mapped_column(Float)
    wave_m: Mapped[float | None] = mapped_column(Float)
    visibility_km: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(24), default="OPEN_METEO")
    confidence: Mapped[float] = mapped_column(Float, default=0.8)


class TerminalQuality(Base):
    """W1: per-terminal data-completeness score (Module D)."""

    __tablename__ = "terminal_quality"

    id: Mapped[int] = mapped_column(primary_key=True)
    terminal_id: Mapped[int] = mapped_column(ForeignKey("terminal.id", ondelete="CASCADE"), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completeness_pct: Mapped[float] = mapped_column(Float)
    missing: Mapped[list | None] = mapped_column(JSONB)          # ["draft_ft", "reefer_units", ...]
    rules_version: Mapped[str] = mapped_column(String(24), default="v1")


class TidalWindow(Base):
    """W3: berth draft availability over time (time-varying depth constraint)."""

    __tablename__ = "tidal_window"
    __table_args__ = (UniqueConstraint("berth_id", "hours_ago", name="uq_tide_berth_hours"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    berth_id: Mapped[int] = mapped_column(ForeignKey("berth.id", ondelete="CASCADE"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    hours_ago: Mapped[int] = mapped_column(Integer)
    min_depth_ft: Mapped[float] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(String(80))


class VesselScheduleUpload(Base):
    """W1: audit row for a CSV/EDI schedule upload (Module B)."""

    __tablename__ = "vessel_schedule_upload"

    id: Mapped[int] = mapped_column(primary_key=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    filename: Mapped[str] = mapped_column(String(200))
    rows: Mapped[int] = mapped_column(Integer, default=0)
    accepted: Mapped[int] = mapped_column(Integer, default=0)
    rejected: Mapped[int] = mapped_column(Integer, default=0)
    report: Mapped[dict | None] = mapped_column(JSONB)          # {errors:[...], created:[...]}
