"""Generate reproducible NOAA AccessAIS-shaped demo records for San Pedro Bay."""

from __future__ import annotations

import argparse
import csv
import math
import random
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path

_COLUMNS = ["MMSI", "BaseDateTime", "LAT", "LON", "SOG", "COG", "Heading", "VesselName", "IMO", "CallSign", "VesselType", "Status", "Length", "Width", "Draft", "Cargo"]
_ANCHORAGES = [("Z-LBCT", 33.750, -118.217, 0.005, 0.005, 3), ("Z-ITS", 33.746, -118.203, 0.005, 0.005, 3), ("Z-PCT", 33.741, -118.181, 0.005, 0.005, 2), ("Z-TTI", 33.736, -118.210, 0.005, 0.005, 2)]
_APPROACH_WAYPOINTS = [(33.20, -118.35), (33.10, -118.10), (33.40, -117.90)]
_CLASSES = [
    {"cls": "ULCV", "loa": 1312, "beam": 200, "draft": 50.5, "type": 70, "w": 3},
    {"cls": "POST_PANAMAX", "loa": 1148, "beam": 158, "draft": 49.0, "type": 70, "w": 5},
    {"cls": "NEO_PANAMAX", "loa": 1200, "beam": 168, "draft": 50.0, "type": 70, "w": 4},
    {"cls": "PANAMAX", "loa": 964, "beam": 124, "draft": 45.0, "type": 70, "w": 6},
    {"cls": "FEEDER", "loa": 636, "beam": 106, "draft": 36.0, "type": 70, "w": 4},
]
_NAME_A = ["Pacific", "Meridian", "Osprey", "Golden", "Harbour", "Coral", "Trade", "Marlin", "Albatross", "Cobalt", "Sierra", "Aurora"]
_NAME_B = ["Star", "Voyager", "Trader", "Pioneer", "Guardian", "Runner", "Banner", "Comet", "Pilot", "Crest"]
_DWELL_MU, _DWELL_SIGMA = 2.9, 0.7


def _pick_class(rng):
    total = sum(c["w"] for c in _CLASSES); r = rng.random() * total
    for c in _CLASSES:
        r -= c["w"]
        if r <= 0: return c
    return _CLASSES[-1]


def _fmt_dt(dt): return dt.strftime("%Y-%m-%dT%H:%M:%S")


def _bearing(lat1, lon1, lat2, lon2):
    d_lon = math.radians(lon2 - lon1); lat1r = math.radians(lat1); lat2r = math.radians(lat2)
    return (math.degrees(math.atan2(math.sin(d_lon) * math.cos(lat2r), math.cos(lat1r) * math.sin(lat2r) - math.sin(lat1r) * math.cos(lat2r) * math.cos(d_lon))) + 360) % 360


def _interp(lat1, lon1, lat2, lon2, frac): return lat1 + frac * (lat2 - lat1), lon1 + frac * (lon2 - lon1)


def _pick_anchorage(rng):
    total = sum(a[5] for a in _ANCHORAGES); r = rng.random() * total
    for a in _ANCHORAGES:
        r -= a[5]
        if r <= 0:
            zone, lat_ctr, lon_ctr, dlat, dlon, _ = a
            return zone, lat_ctr + rng.uniform(-dlat * .8, dlat * .8), lon_ctr + rng.uniform(-dlon * .8, dlon * .8)
    a = _ANCHORAGES[-1]; return a[0], a[1], a[2]


def _generate_vessel_track(rng, arrival_dt, dwell_hours, vessel_class):
    records = []; _zone_code, anch_lat, anch_lon = _pick_anchorage(rng)
    approach_lat, approach_lon = rng.choice(_APPROACH_WAYPOINTS); approach_lat += rng.uniform(-.05, .05); approach_lon += rng.uniform(-.05, .05)
    mmsi = str(rng.randint(300_000_000, 500_000_000)); imo = f"IMO{rng.randint(7_000_000, 9_999_999)}"; name = f"M/V {rng.choice(_NAME_A)} {rng.choice(_NAME_B)}"
    call = "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(4)) + str(rng.randint(10, 99)); loa = int(vessel_class["loa"] + rng.gauss(0, 20)); beam = vessel_class["beam"]; draft = round(vessel_class["draft"] + rng.gauss(0, .4), 1)
    def add(dt, lat, lon, sog, cog, status):
        records.append({"MMSI": mmsi, "BaseDateTime": _fmt_dt(dt), "LAT": round(lat, 5), "LON": round(lon, 5), "SOG": round(max(0, sog + rng.gauss(0, .1)), 1), "COG": round((cog + rng.gauss(0, 2)) % 360, 1), "Heading": round((cog + rng.gauss(0, 5)) % 360), "VesselName": name, "IMO": imo, "CallSign": call, "VesselType": vessel_class["type"], "Status": status, "Length": loa, "Width": beam, "Draft": draft, "Cargo": 71})
    approach_hours = rng.uniform(3, 8); t = arrival_dt - timedelta(hours=approach_hours + dwell_hours); sog = rng.uniform(13, 16); interval_min = rng.uniform(2, 4); mid_lat, mid_lon = _interp(approach_lat, approach_lon, anch_lat, anch_lon, .6); phase1_steps = max(3, int(approach_hours * 60 / interval_min * .6))
    for i in range(phase1_steps):
        frac = i / max(1, phase1_steps - 1); lat, lon = _interp(approach_lat, approach_lon, mid_lat, mid_lon, frac); add(t, lat, lon, sog, _bearing(approach_lat, approach_lon, anch_lat, anch_lon), 0); t += timedelta(minutes=interval_min + rng.gauss(0, .5))
    sog = rng.uniform(3, 6); interval_min = rng.uniform(3, 5); phase2_steps = max(2, int(approach_hours * 60 / interval_min * .4))
    for i in range(phase2_steps):
        frac = i / max(1, phase2_steps - 1); lat, lon = _interp(mid_lat, mid_lon, anch_lat, anch_lon, frac); add(t, lat, lon, sog * (1 - frac * .7), _bearing(mid_lat, mid_lon, anch_lat, anch_lon), 3); t += timedelta(minutes=interval_min + rng.gauss(0, .5))
    t = arrival_dt; depart_dt = arrival_dt + timedelta(hours=dwell_hours)
    while t < depart_dt:
        add(t, anch_lat + rng.gauss(0, .001), anch_lon + rng.gauss(0, .001), max(0, rng.gauss(.1, .08)), rng.uniform(0, 360), 1); t += timedelta(minutes=rng.uniform(3, 10))
    depart_dest_lat = approach_lat + rng.uniform(-.1, .1); depart_dest_lon = approach_lon + rng.uniform(-.1, .1); sog = rng.uniform(8, 14); steps = rng.randint(4, 8)
    for i in range(steps):
        frac = (i + 1) / steps; lat, lon = _interp(anch_lat, anch_lon, depart_dest_lat, depart_dest_lon, frac); add(t, lat, lon, sog, _bearing(anch_lat, anch_lon, depart_dest_lat, depart_dest_lon), 0); t += timedelta(minutes=rng.uniform(2, 5))
    return records


def generate_ais_csv(days=14, seed=20240817, arrivals_per_day=8.0):
    rng = random.Random(seed); now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0); start_dt = now - timedelta(days=days); all_records = []; t = start_dt; mean_gap_hours = 24.0 / arrivals_per_day
    while t < now:
        t += timedelta(hours=rng.expovariate(1.0 / mean_gap_hours))
        if t >= now: break
        dwell = max(2.0, min(math.exp(_DWELL_MU + _DWELL_SIGMA * rng.gauss(0, 1)), 120.0)); all_records.extend(_generate_vessel_track(rng, t, dwell, _pick_class(rng)))
    for k in range(3):
        bunch_t = now - timedelta(hours=144 - k * 4); all_records.extend(_generate_vessel_track(rng, bunch_t, rng.uniform(24, 48), next(c for c in _CLASSES if c["cls"] == "ULCV")))
    for anchor_entry in _ANCHORAGES:
        zone_code, lat_ctr, lon_ctr, dlat, dlon, _ = anchor_entry; arrive_t = now - timedelta(hours=rng.uniform(6, 18)); all_records.extend(_generate_vessel_track(rng, arrive_t, rng.uniform(36, 96), _pick_class(rng)))
    all_records.sort(key=lambda r: r["BaseDateTime"]); buf = StringIO(); writer = csv.DictWriter(buf, fieldnames=_COLUMNS); writer.writeheader(); writer.writerows(all_records); return buf.getvalue()


def generate_and_load(days=14, seed=20240817):
    from tempfile import NamedTemporaryFile
    from . import ais as ais_pipeline
    csv_content = generate_ais_csv(days=days, seed=seed)
    with NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as raw_f, NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as series_f:
        raw_f.write(csv_content); raw_f.flush(); raw_path, series_path = raw_f.name, series_f.name
    try:
        build_stats = ais_pipeline.build(raw_path, series_path, min_anchor_min=5.0, sog_max=1.0); import_stats = ais_pipeline.import_series(series_path, source="DEMO_AIS", is_measured=False)
    finally:
        Path(raw_path).unlink(missing_ok=True); Path(series_path).unlink(missing_ok=True)
    return {**build_stats, **import_stats, "days": days, "seed": seed, "source": "DEMO_AIS"}


def main(argv=None):
    p = argparse.ArgumentParser(prog="app.pipelines.ais_generate", description="Generate synthetic San Pedro Bay AccessAIS-shaped data"); p.add_argument("--days", type=int, default=14); p.add_argument("--seed", type=int, default=20240817); p.add_argument("--out", type=str, default=""); p.add_argument("--no-load", action="store_true"); args = p.parse_args(argv)
    if args.out:
        csv_content = generate_ais_csv(days=args.days, seed=args.seed); Path(args.out).write_text(csv_content, encoding="utf-8"); print(f"Written {csv_content.count(chr(10)) - 1} records to {args.out}"); return
    if args.no_load:
        csv_content = generate_ais_csv(days=args.days, seed=args.seed); print(f"Generated {csv_content.count(chr(10)) - 1} AccessAIS-shaped records (not loaded)"); return
    print(generate_and_load(days=args.days, seed=args.seed))


if __name__ == "__main__":
    main()
