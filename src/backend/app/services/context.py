"""Shared engine context loaded from PostgreSQL."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import reference as ref
from ..models import Berth, CongestionObservation, Crane, Gate, Terminal, VesselCall, YardZone


@dataclass
class TerminalCtx:
    id: int; code: str; name: str; pier: str; lat: float | None; lon: float | None
    berth_length_ft: int; deepsea_berths: int; gantry_cranes: int; capacity_teu_m: float | None
    zone_code: str; note: str | None


@dataclass
class BerthCtx:
    id: int; name: str; seq: int; length_ft: int; depth_ft: float; cranes_max: int
    terminal_code: str; terminal_name: str; pier: str; zone_code: str; reach_ft: float = 210.0


@dataclass
class VesselCtx:
    id: int; mmsi: str | None; imo: str | None; name: str; carrier: str; vessel_class: str
    loa_ft: int; beam_ft: int; draft_ft: float; teu_capacity: int; import_moves: int; export_moves: int
    origin_port: str; reefer_units: int; status: str; anchorage_zone: str | None
    declared_eta_hours: float; ais_eta_hours: float | None; anchored_hours: float; dest_zone_code: str
    data_confidence: float; unresolved: bool
    @property
    def eta_hours(self) -> float: return self.ais_eta_hours if self.ais_eta_hours is not None else self.declared_eta_hours
    @property
    def total_moves(self) -> int: return self.import_moves + self.export_moves


@dataclass
class HistoryPoint:
    ts: datetime; hours_ago: int; queue_count: int; avg_wait_hours: float; index: float; yard_util_pct: float | None


@dataclass
class EngineContext:
    t0: datetime; terminals: list[TerminalCtx]; berths: list[BerthCtx]; vessels: list[VesselCtx]
    history: dict[str, list[HistoryPoint]] = field(default_factory=dict)
    cranes: dict[str, int] = field(default_factory=dict)
    yard_util: dict[str, float] = field(default_factory=dict)
    gate_queue: dict[str, int] = field(default_factory=dict)
    dataset_source: str = "DEMO_AIS"
    data_version: str = ""


def zone_capacity(ctx: EngineContext, zone_code: str) -> dict:
    if zone_code == "Z-PORT":
        return {"berths": len(ctx.berths), "cranes": sum(t.gantry_cranes for t in ctx.terminals), "berth_length_ft": sum(t.berth_length_ft for t in ctx.terminals)}
    term_berths = [b for b in ctx.berths if b.zone_code == zone_code]
    term = next((t for t in ctx.terminals if t.zone_code == zone_code), None)
    return {"berths": len(term_berths), "cranes": sum(b.cranes_max for b in term_berths), "berth_length_ft": term.berth_length_ft if term else 0}


def _context_fingerprint(observations, vessels, cranes, yards, gates, terminals, berths) -> str:
    h = hashlib.sha256()
    for o in observations:
        h.update(f"O|{o.id}|{o.source}|{o.ts.isoformat()}|{o.hours_ago}|{o.queue_count}|{o.avg_wait_hours}|{o.index}|{o.yard_util_pct}\n".encode())
    for v in vessels:
        h.update(f"V|{v.id}|{v.imo}|{v.status}|{v.declared_eta_hours}|{v.ais_eta_hours}|{v.dest_zone_code}|{v.import_moves}|{v.export_moves}|{v.reefer_units}|{v.loa_ft}|{v.beam_ft}|{v.draft_ft}\n".encode())
    for c in cranes:
        h.update(f"C|{c.id}|{c.terminal_id}|{c.status}|{c.rated_moves_per_hour}|{c.reach_ft}\n".encode())
    for y in yards:
        h.update(f"Y|{y.id}|{y.terminal_id}|{y.ground_slots_teu}|{y.used_teu}\n".encode())
    for g in gates:
        h.update(f"G|{g.id}|{g.terminal_id}|{g.queue_len}|{g.trucks_per_hour}\n".encode())
    for t in terminals:
        h.update(f"T|{t.id}|{t.config_version}|{t.berth_length_ft}|{t.deepsea_berths}|{t.gantry_cranes}\n".encode())
    for b in berths:
        h.update(f"B|{b.id}|{b.length_ft}|{b.depth_ft}|{b.cranes_max}\n".encode())
    return h.hexdigest()[:20]


def load_context(db: Session) -> EngineContext:
    terminals = db.execute(select(Terminal).order_by(Terminal.code)).scalars().all()
    berths = db.execute(select(Berth).order_by(Berth.seq)).scalars().all()
    vessels = db.execute(select(VesselCall).order_by(VesselCall.anchored_hours.desc())).scalars().all()
    observations = db.execute(select(CongestionObservation).order_by(CongestionObservation.hours_ago.desc())).scalars().all()
    cranes = db.execute(select(Crane).order_by(Crane.id)).scalars().all()
    yards = db.execute(select(YardZone).order_by(YardZone.id)).scalars().all()
    gates = db.execute(select(Gate).order_by(Gate.id)).scalars().all()
    term_by_id = {t.id: t for t in terminals}
    reach_by_terminal = {}
    for c in cranes:
        reach_by_terminal[c.terminal_id] = max(reach_by_terminal.get(c.terminal_id, 0.0), float(c.reach_ft or 0.0))
    berth_ctx = [BerthCtx(
        b.id, b.name, b.seq, b.length_ft, b.depth_ft, b.cranes_max,
        term_by_id[b.terminal_id].code, term_by_id[b.terminal_id].name,
        term_by_id[b.terminal_id].pier, term_by_id[b.terminal_id].zone_code,
        reach_by_terminal.get(b.terminal_id, 210.0),
    ) for b in berths]
    vessel_ctx = [VesselCtx(v.id, v.mmsi, v.imo, v.name, v.carrier, v.vessel_class, v.loa_ft, v.beam_ft,
                             v.draft_ft, v.teu_capacity, v.import_moves, v.export_moves, v.origin_port,
                             v.reefer_units, v.status, v.anchorage_zone, v.declared_eta_hours, v.ais_eta_hours,
                             v.anchored_hours, v.dest_zone_code, v.data_confidence, v.unresolved) for v in vessels]
    history: dict[str, list[HistoryPoint]] = {}
    for o in observations:
        history.setdefault(o.zone_code, []).append(HistoryPoint(o.ts, o.hours_ago, o.queue_count, o.avg_wait_hours, o.index, o.yard_util_pct))
    latest = max((o.ts for o in observations), default=datetime.utcnow())
    avail = {}
    for c in cranes:
        code = term_by_id[c.terminal_id].code
        if c.status == "AVAILABLE":
            avail[code] = avail.get(code, 0) + 1
    yard_util = {}
    for term in terminals:
        zs = [y for y in yards if y.terminal_id == term.id]; cap = sum(y.ground_slots_teu for y in zs) or 1; used = sum(y.used_teu for y in zs)
        yard_util[term.code] = round(100.0 * used / cap, 1)
    gate_queue = {term_by_id[g.terminal_id].code: g.queue_len for g in gates}
    source = observations[0].source if observations else "DEMO_AIS"
    data_version = _context_fingerprint(observations, vessels, cranes, yards, gates, terminals, berths)
    return EngineContext(t0=latest, terminals=terminals, berths=berth_ctx, vessels=vessel_ctx,
                         history=history, cranes=avail, yard_util=yard_util, gate_queue=gate_queue,
                         dataset_source=source, data_version=data_version)


__all__ = ["EngineContext", "TerminalCtx", "BerthCtx", "VesselCtx", "HistoryPoint", "load_context", "zone_capacity", "ref"]
