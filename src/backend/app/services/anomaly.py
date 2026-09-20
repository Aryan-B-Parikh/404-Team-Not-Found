"""Anomaly & disruption detection — scikit-learn Isolation Forest.

Implements rolling-window anomaly detection with optional weather signals.
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest

from ..config import get_settings

MIN_SAMPLES = 96
# sklearn 'auto' uses the original paper's offset (flag only genuinely short
# isolation paths). A float here (e.g. 0.04) *defines* the threshold so that
# ~4% of every training window is labelled an outlier — it manufactures noise.
# Backlog B-1: 3 of 4 zones flagged every run was this parameter, not real signal.
CONTAMINATION = "auto"
# Minimum evidence strength for is_anomaly: on non-stationary series the forest
# alone flags routine regime drift (documented floor per backlog B-1).
SCORE_FLOOR = 0.2
ANOMALY_WINDOW = 72
MIN_WEATHER_ROWS = 24
WEATHER_SEVERITY_REF = 0.40
STAT_Z = 3.5


def _matrix(history, weather_rows=None):
    idx = np.array([h.index for h in history], dtype=float)
    q = np.array([h.queue_count for h in history], dtype=float)
    w = np.array([h.avg_wait_hours for h in history], dtype=float)
    yard = np.array([(h.yard_util_pct or 0.0) for h in history], dtype=float)
    dq = np.diff(q, prepend=q[:1])
    di = np.diff(idx, prepend=idx[:1])
    win = 6
    roll_std = np.array([np.std(idx[max(0, i - win):i + 1]) for i in range(len(idx))])
    X = np.column_stack([idx, q, w, yard, dq, di, roll_std])
    names = ["index", "queue", "wait", "yard_util", "d_queue", "d_index", "index_roll_std"]
    weather_used = False
    if weather_rows:
        wa = {w.get("hours_ago"): w for w in weather_rows if w.get("hours_ago") is not None}
        covered = sum(1 for h in history if h.hours_ago in wa)
        if covered >= MIN_WEATHER_ROWS:
            for f in ("wind_kn", "gust_kn", "wave_m"):
                col = [float((wa.get(h.hours_ago) or {}).get(f) or 0.0) for h in history]
                X = np.column_stack([X, np.array(col, dtype=float)])
                names.append(f)
            weather_used = True
    return X, names, weather_used


def _weather_severity(w: dict | None) -> float:
    if not w:
        return 0.0
    gust = w.get("gust_kn") if w.get("gust_kn") is not None else w.get("wind_kn")
    wave = w.get("wave_m")
    vis = w.get("visibility_km")
    sev = 0.0
    if gust is not None:
        sev += 0.6 * _clip((float(gust) - 25.0) / 25.0)
    if wave is not None:
        sev += 0.3 * _clip((float(wave) - 2.5) / 2.5)
    if vis is not None:
        sev += 0.1 * _clip((5.0 - float(vis)) / 5.0)
    return _clip(sev)


def _clip(x, lo=0.0, hi=1.0) -> float:
    return max(lo, min(hi, float(x)))


def detect_anomalies(ctx, weather=None) -> list[dict]:
    """Run Isolation Forest per terminal zone and return flagged disruptions."""
    settings = get_settings()
    weather_rows = weather if (settings.feature_weather and weather) else None
    by_ago = {w.get("hours_ago"): w for w in (weather_rows or []) if w.get("hours_ago") is not None}
    flags: list[dict] = []
    for zone_code, history in ctx.history.items():
        if zone_code == "Z-PORT":
            continue
        n = len(history)
        if n < MIN_SAMPLES:
            flags.append({
                "zone_code": zone_code, "kind": "INSUFFICIENT_DATA", "method": "IsolationForest",
                "score": 0.0, "is_anomaly": False, "sample_size": n,
                "detail": f"Only {n}h of history (< {MIN_SAMPLES}h) — anomaly confidence explicitly low.",
                "features": None, "confidence": 0.1, "window_hours": min(n, ANOMALY_WINDOW),
            })
            continue
        X, names, weather_used = _matrix(history, weather_rows)
        model = IsolationForest(n_estimators=200, contamination=CONTAMINATION, random_state=0)
        model.fit(X)
        scores = model.decision_function(X)
        preds = model.predict(X)
        start = max(0, n - ANOMALY_WINDOW)
        window = slice(start, n)
        window_anoms = int((preds[window] == -1).sum())
        if_anom = bool((preds[window] == -1).any())
        recent_score = float(scores[window].min())
        med = float(np.median(X[:, 0]))
        mad = float(np.median(np.abs(X[:, 0] - med))) or 1.0
        z = (X[:, 0] - med) / (1.4826 * mad)
        z_win = np.abs(z[window])
        stat_anom = bool(z_win.max() >= STAT_Z) if len(z_win) else False
        novel = if_anom or stat_anom
        # Two evidence channels: forest novelty (score) and magnitude (|z|).
        # A flag needs novelty AND one channel *strong* — a weak forest score alone
        # flags routine regime drift (B-1 noise); a strong z compensates when the
        # forest under-scores a genuine spike (the seeded PCT outage scores -0.19).
        strong_magnitude = float(np.abs(z_win).max()) >= STAT_Z if len(z_win) else False
        recent_anom = novel and (recent_score <= -SCORE_FLOOR or strong_magnitude)
        ai = (start + int(np.argmax(z_win))) if stat_anom else (start + int(np.argmin(scores[window])))
        pt = history[ai]
        dq = float(pt.queue_count - (history[ai - 1].queue_count if ai > 0 else pt.queue_count))
        di = float(pt.index - (history[ai - 1].index if ai > 0 else pt.index))
        sev = _weather_severity(by_ago.get(pt.hours_ago))
        win_idx = np.array([h.index for h in history[start:]], dtype=float)
        win_std = float(np.std(win_idx)) if len(win_idx) > 1 else 0.0
        win_med = float(np.median(win_idx)) if len(win_idx) else 0.0
        if abs(dq) > 14 or abs(di) > 40:
            kind = "DATA_ERROR"
        elif weather_used and sev >= WEATHER_SEVERITY_REF:
            kind = "WEATHER"
        elif dq >= 5:
            kind = "BUNCHING"
        elif (pt.yard_util_pct or 0) >= 92:
            kind = "YARD_SATURATION"
        elif win_med >= 45 and win_std < 8 and win_med > 1.3 * float(np.median(X[:, 0])):
            kind = "OUTAGE"
        elif abs(dq) <= 2 and abs(di) <= 2 and not recent_anom:
            kind = "NOMINAL"
        else:
            kind = "VARIANCE"
        confidence = round(_clip(0.4 * min(1.0, n / 336.0) + 0.6 * _clip(0.5 - recent_score), 0.05, 0.95), 3)
        flags.append({
            "zone_code": zone_code, "kind": kind, "method": "IsolationForest", "score": round(recent_score, 4),
            "is_anomaly": recent_anom and kind != "DATA_ERROR", "sample_size": n,
            "detail": (f"queue={pt.queue_count}, wait={pt.avg_wait_hours:.0f}h, index={pt.index:.0f}, Δqueue(most anomalous h)={dq:+.0f}, Δindex={di:+.0f}. "
                       + (f"Window ({window_anoms} flagged in last {min(n, ANOMALY_WINDOW)}h)." if recent_anom
                          else (f"Weak signal held below evidence floor (|score| < {SCORE_FLOOR})." if novel
                                else "Recent window within normal range."))
                       + (f" Adverse weather coincident (severity {sev:.2f})." if weather_used and sev >= WEATHER_SEVERITY_REF else "")
                       + (" Flagged as probable DATA ERROR (implausible jump) — not a confirmed disruption." if kind == "DATA_ERROR" else "")),
            "features": {k: round(float(X[ai, i]), 2) for i, k in enumerate(names)}, "confidence": confidence,
            "window_hours": min(n, ANOMALY_WINDOW), "weather_used": weather_used,
        })
    return flags
