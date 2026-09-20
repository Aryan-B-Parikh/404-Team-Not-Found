"""Reference + state capability: terminals, vessels, anomalies, hotspots."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..models import EtaRevision, Terminal, VesselCall, VesselScheduleUpload
from ..pipelines.schedule import parse_schedule
from ..response_models import Hotspots, TerminalsResponse, UploadResponse, VesselsResponse
from ..serialize import terminal_to_dict, vessel_to_dict
from ..services import pipeline

router = APIRouter(prefix="/api", tags=["catalog"])
_UPLOAD_MAX_BYTES = 10 * 1024 * 1024


@router.get("/terminals", response_model=TerminalsResponse)
def terminals(db: Session = Depends(get_db)):
    ts = db.execute(
        select(Terminal).options(
            joinedload(Terminal.berths), joinedload(Terminal.cranes),
            joinedload(Terminal.yard_zones), joinedload(Terminal.gates),
        ).order_by(Terminal.code)
    ).unique().scalars().all()
    out = []
    for t in ts:
        berths = [{"name": b.name, "seq": b.seq, "length_ft": b.length_ft, "depth_ft": b.depth_ft, "cranes_max": b.cranes_max}
                  for b in sorted(t.berths, key=lambda b: b.seq)]
        cranes = [{"code": c.code, "type": c.crane_type, "reach_ft": c.reach_ft,
                   "rated_moves_per_hour": c.rated_moves_per_hour, "status": c.status, "reason": c.status_reason}
                  for c in t.cranes]
        yards = [{"code": y.code, "ground_slots_teu": y.ground_slots_teu, "reefer_plugs": y.reefer_plugs,
                  "used_teu": y.used_teu, "util_pct": round(100 * y.used_teu / max(1, y.ground_slots_teu), 1)} for y in t.yard_zones]
        gate = t.gates[0] if t.gates else None
        gate_d = ({"lanes": gate.lanes, "trucks_per_hour": gate.trucks_per_hour,
                   "queue_len": gate.queue_len, "open_hours": gate.open_hours} if gate else None)
        out.append(terminal_to_dict(t, berths, cranes, yards, gate_d))
    return {"terminals": out, "source": "Port of Long Beach terminal fact sheets (real berth/crane capacity); yard/gate figures are documented demo values."}


@router.get("/vessels", response_model=VesselsResponse)
def vessels(db: Session = Depends(get_db)):
    full = pipeline.build_full(db, persist=False)
    assignment = {a["vessel_id"]: a for a in full["optimiser"]["assignments"]}
    rows = []
    for v in full["ctx"].vessels:
        d = vessel_to_dict(v)
        a = assignment.get(v.id)
        d["assignment"] = ({"berth_name": a["berth_name"], "terminal_code": a["terminal_code"],
                            "start_hour": a["start_hour"], "cranes": a["cranes"], "wait_hours": a["wait_hours"]} if a else None)
        d["deferred"] = a is None and v.status != "INBOUND"
        rows.append(d)
    return {"vessels": rows}


@router.get("/hotspots", response_model=Hotspots)
def hotspots(db: Session = Depends(get_db)):
    return pipeline.build_full(db, persist=False)["hotspots"]


@router.patch("/terminals/{code}/config_version")
def bump_config_version(code: str, db: Session = Depends(get_db)):
    """Module A: increment config_version so context fingerprint changes and caches invalidate."""
    term = db.execute(select(Terminal).where(Terminal.code == code)).scalars().first()
    if term is None:
        raise HTTPException(404, f"terminal {code!r} not found")
    term.config_version = (term.config_version or 1) + 1
    db.commit()
    return {"code": code, "config_version": term.config_version}


@router.post("/vessels/upload", response_model=UploadResponse)
async def upload_schedule(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import a physically complete vessel schedule and immediately rebuild the plan.

    Physical fields are mandatory. The endpoint never substitutes fabricated vessel
    dimensions, draft, moves or destination values.
    """
    raw = await file.read()
    if len(raw) > _UPLOAD_MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large: max {_UPLOAD_MAX_BYTES // (1024 * 1024)} MB")

    try:
        parsed = parse_schedule(raw)
    except Exception as exc:
        upload = VesselScheduleUpload(filename=file.filename, rows=0, accepted=0, rejected=0,
                                      report={"errors": [str(exc)], "created": []})
        db.add(upload); db.commit(); db.refresh(upload)
        return {"accepted": 0, "rejected": 0, "errors": [str(exc)], "revisions_created": 0,
                "upload_id": upload.id, "filename": file.filename, "bytes": len(raw), "stub": False}

    rows = parsed["rows"]
    zone_by_code = {t.zone_code: t for t in db.execute(select(Terminal)).scalars().all()}
    existing_keys = {(v.imo, v.voyage_number) for v in db.execute(select(VesselCall)).scalars().all()}
    created: list[dict] = []
    errors = [f"row {r['row_no']}: {r['error']}" for r in parsed["rejected"]]
    accepted = revisions_created = 0
    seen_keys = set(existing_keys)

    for r in parsed["accepted"]:
        imo, voyage = r["imo"].strip(), r["voyage_number"].strip()
        key = (imo, voyage)
        if key in seen_keys:
            errors.append(f"duplicate skipped: {imo}/{voyage}")
            continue
        zone = r["dest_zone_code"].strip()
        if zone not in zone_by_code:
            errors.append(f"unknown dest_zone_code {zone!r} for {imo}/{voyage}")
            continue
        vc = VesselCall(
            imo=imo, voyage_number=voyage, mmsi=(r.get("mmsi") or "").strip() or None,
            name=(r.get("name") or "").strip() or f"Uploaded {imo}",
            carrier=(r.get("carrier") or "").strip() or "Unknown",
            vessel_class=(r.get("vessel_class") or "").strip() or "UNKNOWN",
            loa_ft=r["loa_ft"], beam_ft=r["beam_ft"], draft_ft=r["draft_ft"],
            teu_capacity=r["teu_capacity"], import_moves=r["import_moves"], export_moves=r["export_moves"],
            origin_port=(r.get("origin_port") or "").strip() or "Unknown", reefer_units=r.get("reefer_units", 0),
            status="INBOUND", anchorage_zone="En route — San Pedro Approach",
            declared_eta_hours=r["declared_eta_hours"], ais_eta_hours=None,
            etd_hours=float(r["etd_hours"]) if r.get("etd_hours") else r["declared_eta_hours"] + 26.0,
            anchored_hours=0.0,
            dest_zone_code=zone, data_confidence=1.0, unresolved=False,
            raw={"upload_filename": file.filename, "units": {"loa": "ft", "beam": "ft", "draft": "ft", "eta": "h"}},
        )
        db.add(vc); db.flush()
        db.add(EtaRevision(vessel_call_id=vc.id, source="CARRIER", eta_hours=vc.declared_eta_hours, note="uploaded schedule"))
        revisions_created += 1; accepted += 1; seen_keys.add(key)
        created.append({"imo": imo, "voyage_number": voyage})

    rejected = rows - accepted
    upload = VesselScheduleUpload(filename=file.filename, rows=rows, accepted=accepted, rejected=rejected,
                                  report={"errors": errors, "created": created})
    db.add(upload); db.commit(); db.refresh(upload)

    # Module D: run normalisation pass on newly uploaded vessels so normalised column is current
    normalised_count = 0
    if accepted > 0:
        from ..services.dataquality import NormalisationEngine
        normalised_count = NormalisationEngine(db).run()

    replan = {"status": "not_requested"}
    if accepted > 0:
        try:
            full = pipeline.build_full(db, persist=True)
            replan = {"status": "success", "run_id": full.get("plan", {}).get("run_id")}
        except Exception as exc:  # surface failure; do not silently claim success
            replan = {"status": "failed", "error": str(exc)}

    return {"accepted": accepted, "rejected": rejected, "errors": errors,
            "revisions_created": revisions_created, "normalised_rows": normalised_count,
            "upload_id": upload.id, "filename": file.filename, "bytes": len(raw),
            "stub": False, "replan": replan}
