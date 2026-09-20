"""Weather pipeline (W1).

Fetches wind/gust/visibility from Open-Meteo forecast API (free, no key) and
wave height from the Open-Meteo marine API (free, no key) for San Pedro Bay
(33.74N, -118.20W).  Both calls are non-fatal — if either fails the other still
writes its rows, and the forecast falls back to weather_used=False.

Open-Meteo forecast:  https://api.open-meteo.com/v1/forecast
Open-Meteo marine:    https://marine-api.open-meteo.com/v1/marine

``hours_ago`` convention (shared with CongestionObservation):
  * 0 = current hour
  * -N = N hours ahead (negative = future)
  * positive values are NOT stored here (only forecast rows are kept)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import WeatherObservation

LOGGER = logging.getLogger(__name__)

# Forecast endpoint variables (wind/gust/visibility)
_FORECAST_VARS = "wind_speed_10m,wind_gusts_10m,visibility"
# Marine endpoint variables (wave height)
_MARINE_VARS = "wave_height"

# Knot conversion factor (m/s → knots)
_MS_TO_KN = 1.9438452


def _fetch_forecast(lat: float, lon: float, forecast_days: int, base_url: str) -> dict[str, Any]:
    """Call the Open-Meteo atmospheric forecast endpoint."""
    resp = httpx.get(
        f"{base_url}/v1/forecast",
        params={
            "latitude": lat, "longitude": lon,
            "hourly": _FORECAST_VARS,
            "forecast_days": forecast_days,
            "timezone": "UTC",
            "wind_speed_unit": "ms",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _fetch_marine(lat: float, lon: float, forecast_days: int) -> dict[str, Any]:
    """Call the Open-Meteo marine API for wave height (separate endpoint, no API key)."""
    resp = httpx.get(
        "https://marine-api.open-meteo.com/v1/marine",
        params={
            "latitude": lat, "longitude": lon,
            "hourly": _MARINE_VARS,
            "forecast_days": forecast_days,
            "timezone": "UTC",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def run_weather_pipeline(db: Session, hours: int = 72) -> int:
    """Fetch Open-Meteo atmospheric + marine data and persist WeatherObservation rows.

    Returns the number of rows written. Performs a full-replace (DELETE then INSERT)
    since the table is small (< 336 rows) and idempotency matters more than atomicity.

    Wave height is fetched from the marine API in a separate (non-fatal) call so that
    a marine-API outage never blocks the wind/visibility data.
    """
    settings = get_settings()
    forecast_days = max(1, min(16, (hours // 24) + 1))

    # ── Atmospheric fetch (wind, gust, visibility) ──────────────────────────────
    try:
        atm = _fetch_forecast(settings.reference_lat, settings.reference_lon,
                              forecast_days, settings.open_meteo_base)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Weather pipeline (forecast) failed (non-fatal): %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
        return 0

    hourly = atm.get("hourly", {})
    timestamps: list[str] = hourly.get("time", [])
    if not timestamps:
        LOGGER.warning("Open-Meteo returned no hourly timestamps")
        return 0

    wind_ms: list[Any] = hourly.get("wind_speed_10m", [])
    gust_ms: list[Any] = hourly.get("wind_gusts_10m", [])
    vis_m: list[Any] = hourly.get("visibility", [])

    # ── Marine fetch (wave height) — non-fatal ───────────────────────────────────
    wave_m: list[Any] = []
    try:
        marine = _fetch_marine(settings.reference_lat, settings.reference_lon, forecast_days)
        wave_m = marine.get("hourly", {}).get("wave_height", [])
        LOGGER.info("Weather pipeline (marine): got %d wave_height values", len(wave_m))
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Weather pipeline (marine) failed (non-fatal, wave_m will be None): %s", exc)

    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)

    # Full replace: delete old weather rows then insert fresh ones
    db.execute(delete(WeatherObservation))

    def _safe(lst: list, i: int, scale: float = 1.0) -> float | None:
        v = lst[i] if i < len(lst) else None
        return round(float(v) * scale, 2) if v is not None else None

    count = 0
    for idx, ts_str in enumerate(timestamps):
        if idx >= hours:
            break
        try:
            ts = datetime.fromisoformat(ts_str).replace(tzinfo=UTC)
        except ValueError:
            continue
        hours_ago = int(round((now - ts).total_seconds() / 3600.0))
        # Only store forecast rows (hours_ago <= 0, negative = future) within the window.
        # Sign bug fixed: ts > now (future forecast) must yield NEGATIVE hours_ago,
        # otherwise the filter below dropped exactly the forecast rows this pipeline exists for.
        if hours_ago > 0 or hours_ago < -hours:
            continue

        db.add(WeatherObservation(
            ts=ts,
            hours_ago=hours_ago,
            wind_kn=_safe(wind_ms, idx, _MS_TO_KN),
            gust_kn=_safe(gust_ms, idx, _MS_TO_KN),
            wave_m=_safe(wave_m, idx),            # None when marine API unavailable
            visibility_km=_safe(vis_m, idx, 0.001),  # m → km
            source="OPEN_METEO",
            confidence=0.85,
        ))
        count += 1

    db.commit()
    LOGGER.info("Weather pipeline: inserted %d rows (Open-Meteo)", count)
    return count
