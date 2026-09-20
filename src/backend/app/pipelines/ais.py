"""NOAA AccessAIS ingestion with measured-history and raw-track provenance."""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from .. import reference as ref

BBOX = {"lat_min": 33.55, "lat_max": 33.85, "lon_min": -118.45, "lon_max": -118.05}
ANCHORAGE_RECTS = [
    {"name": "San Pedro Anchorage A/B (approx.)", "lat_min": 33.60, "lat_max": 33.72, "lon_min": -118.30, "lon_max": -118.18},
    {"name": "Long Beach Terminal Berths (approx.)", "lat_min": 33.730, "lat_max": 33.756, "lon_min": -118.223, "lon_max": -118.175},
]
TERMINAL_ANCHORS = {t["zone_code"]: (t["lat"], t["lon"]) for t in ref.TERMINALS}
REQUIRED = ("mmsi", "basedatetime", "lat", "lon", "sog")


def _in_rect(lat: float, lon: float, r: dict) -> bool:
    return r["lat_min"] <= lat <= r["lat_max"] and r["lon_min"] <= lon <= r["lon_max"]


def _in_bbox(lat: float, lon: float) -> bool:
    return _in_rect(lat, lon, BBOX)


def _zone_for(lat: float, lon: float) -> str:
    best, best_d = ref.TERMINAL_ZONES[0], float("inf")
    for zone, (tlat, tlon) in TERMINAL_ANCHORS.items():
        if tlat is None or tlon is None:
            continue
        d = (lat - tlat) ** 2 + (lon - tlon) ** 2
        if d < best_d:
            best, best_d = zone, d
    return best


def _parse_dt(s: str) -> datetime:
    s = s.strip().replace(" UTC", "")
    dt = datetime.fromisoformat(s)
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


def _header_map(fieldnames: list[str]) -> dict[str, str]:
    return {name.lower().strip(): name for name in fieldnames}


def build(ais_csv: str, out_csv: str, min_anchor_min: float = 0.0, sog_max: float = 1.0) -> dict:
    """Convert an AccessAIS export into a per-zone hourly congestion series."""
    first: dict[str, datetime] = {}; last: dict[str, datetime] = {}
    pos_sum: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0]); rows = skipped = 0
    with open(ais_csv, newline="", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh); cols = _header_map(reader.fieldnames or [])
        missing = [c for c in REQUIRED if c not in cols]
        if missing:
            raise ValueError(f"missing required columns {missing}; found {reader.fieldnames}")
        for row in reader:
            rows += 1
            try:
                lat = float(row[cols["lat"]]); lon = float(row[cols["lon"]]); sog = float(row[cols["sog"]])
                mmsi = str(row[cols["mmsi"]]).strip(); ts = _parse_dt(row[cols["basedatetime"]])
            except (KeyError, ValueError, TypeError):
                skipped += 1; continue
            if not mmsi or not _in_bbox(lat, lon) or sog >= sog_max:
                continue
            if not any(_in_rect(lat, lon, r) for r in ANCHORAGE_RECTS):
                continue
            first[mmsi] = min(first.get(mmsi, ts), ts); last[mmsi] = max(last.get(mmsi, ts), ts)
            agg = pos_sum[mmsi]; agg[0] += lat; agg[1] += lon; agg[2] += 1

    vessels: list[tuple[str, datetime, datetime, float, str]] = []
    for mmsi, t0 in first.items():
        t1 = last[mmsi]; span_min = (t1 - t0).total_seconds() / 60.0
        if span_min < min_anchor_min:
            continue
        agg = pos_sum[mmsi]; zone = _zone_for(agg[0] / agg[2], agg[1] / agg[2])
        vessels.append((mmsi, t0, t1, span_min / 60.0, zone))
    if not vessels:
        raise ValueError("no anchored vessels found — check bbox / SOG threshold / columns")

    start = min(v[1] for v in vessels).replace(minute=0, second=0, microsecond=0)
    end = max(v[2] for v in vessels).replace(minute=0, second=0, microsecond=0)
    series: list[dict] = []; hour = start
    while hour <= end:
        per_zone: dict[str, list[float]] = {z: [] for z in ref.TERMINAL_ZONES}
        for _mmsi, t0, t1, dwell, zone in vessels:
            if t0 < hour + timedelta(hours=1) and t1 >= hour:
                per_zone[zone].append(dwell)
        port_q = 0; port_wsum = 0.0
        for zone, dwells in per_zone.items():
            q = len(dwells); wait = sum(dwells) / q if q else 0.0
            series.append({"zoneCode": zone, "ts": hour, "queueCount": q, "avgWaitHrs": round(wait, 2), "index": round(_index(q, wait), 2)})
            port_q += q; port_wsum += wait * q
        port_wait = port_wsum / port_q if port_q else 0.0
        series.append({"zoneCode": "Z-PORT", "ts": hour, "queueCount": port_q, "avgWaitHrs": round(port_wait, 2), "index": round(_index(port_q, port_wait), 2)})
        hour += timedelta(hours=1)

    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["zoneCode", "ts", "queueCount", "avgWaitHrs", "index"])
        for r in series:
            w.writerow([r["zoneCode"], r["ts"].strftime("%Y-%m-%dT%H:%M:%SZ"), r["queueCount"], r["avgWaitHrs"], r["index"]])
    return {"rows_scanned": rows, "skipped": skipped, "vessels": len(vessels), "hours": (end - start).total_seconds() / 3600 + 1, "output_rows": len(series)}


def persist_tracks(ais_csv: str, dataset_id: str | None = None, sog_max: float = 1.0, max_rows: int = 500_000) -> dict:
    """Persist filtered NOAA points so historical AIS is queryable beyond the aggregate series."""
    from sqlalchemy import delete
    from ..ais_track_model import AISTrack
    from ..db import SessionLocal, init_db

    init_db()
    dataset_id = dataset_id or hashlib.sha256(f"{ais_csv}:{datetime.now(UTC).isoformat()}".encode()).hexdigest()[:20]
    inserted = skipped = 0
    db = SessionLocal()
    try:
        db.execute(delete(AISTrack).where(AISTrack.dataset_id == dataset_id))
        with open(ais_csv, newline="", encoding="utf-8", errors="replace") as fh:
            reader = csv.DictReader(fh); cols = _header_map(reader.fieldnames or [])
            missing = [c for c in REQUIRED if c not in cols]
            if missing:
                raise ValueError(f"missing required columns {missing}")
            for row in reader:
                if inserted >= max_rows:
                    break
                try:
                    lat = float(row[cols["lat"]]); lon = float(row[cols["lon"]]); sog = float(row[cols["sog"]])
                    mmsi = str(row[cols["mmsi"]]).strip(); ts = _parse_dt(row[cols["basedatetime"]])
                    if not mmsi or not _in_bbox(lat, lon) or sog >= sog_max or not any(_in_rect(lat, lon, r) for r in ANCHORAGE_RECTS):
                        continue
                    raw = {k: row[k] for k in row if k is not None}
                    db.add(AISTrack(dataset_id=dataset_id, mmsi=mmsi, ts=ts, lat=lat, lon=lon, sog=sog,
                                    cog=float(row[cols["cog"]]) if "cog" in cols and row.get(cols["cog"]) else None,
                                    zone_code=_zone_for(lat, lon), raw=raw))
                    inserted += 1
                    if inserted % 5000 == 0:
                        db.flush()
                except (KeyError, ValueError, TypeError, OverflowError):
                    skipped += 1
        db.commit()
        return {"dataset_id": dataset_id, "track_points": inserted, "skipped": skipped, "truncated": inserted >= max_rows}
    finally:
        db.close()


def _index(queue: float, wait_hours: float) -> float:
    return max(0.0, min(100.0, 60 * (queue / ref.CONGESTION_QUEUE_CAP) + 40 * (wait_hours / ref.CONGESTION_WAIT_CAP)))


def import_series(series_csv: str, source: str = "AIS", is_measured: bool = True) -> dict:
    """Replace congestion history and preserve provenance."""
    from sqlalchemy import delete
    from ..db import SessionLocal, init_db
    from ..models import CongestionObservation
    if source not in {"AIS", "DEMO_AIS", "SIM"}:
        raise ValueError(f"unsupported congestion source: {source}")
    with open(series_csv, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError("series CSV is empty")
    newest = max(_parse_dt(r["ts"]) for r in rows).replace(minute=0, second=0, microsecond=0)
    init_db(); db = SessionLocal()
    try:
        db.execute(delete(CongestionObservation)); seen: set[tuple[str, int]] = set(); count = 0
        for r in rows:
            ts = _parse_dt(r["ts"]); hours_ago = int(round((newest - ts).total_seconds() / 3600)); key = (r["zoneCode"], hours_ago)
            if key in seen: continue
            seen.add(key)
            db.add(CongestionObservation(zone_code=r["zoneCode"], ts=ts, hours_ago=hours_ago,
                                         queue_count=int(float(r["queueCount"])), avg_wait_hours=float(r["avgWaitHrs"]),
                                         index=float(r["index"]), yard_util_pct=None, source=source,
                                         is_measured=is_measured, confidence=0.85 if is_measured else 0.70)); count += 1
        db.commit()
        return {"inserted": count, "source": source, "is_measured": is_measured,
                "zones": len({r["zoneCode"] for r in rows}), "newest_ts": newest.isoformat()}
    finally:
        db.close()


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="app.pipelines.ais", description="NOAA AccessAIS → congestion series → PostgreSQL")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="AccessAIS CSV → congestion-series CSV")
    b.add_argument("ais_csv"); b.add_argument("out_csv"); b.add_argument("--min-anchor-min", type=float, default=0.0); b.add_argument("--sog-max", type=float, default=1.0)
    i = sub.add_parser("import", help="congestion-series CSV → database")
    i.add_argument("series_csv")
    args = p.parse_args(argv)
    if args.cmd == "build": print(build(args.ais_csv, args.out_csv, args.min_anchor_min, args.sog_max))
    else: print(import_series(args.series_csv))


if __name__ == "__main__":
    main(sys.argv[1:])
