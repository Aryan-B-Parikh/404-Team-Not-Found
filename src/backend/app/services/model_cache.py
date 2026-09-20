"""Model persistence cache for trained forecasters.

Models are saved under .model_cache/<zone>/<data_version>.pkl so a server
restart re-uses the last trained model as long as the training data hasn't
changed. The cache key is the data_version string (source:Nobs@timestamp),
so any new data automatically triggers a retrain.
"""

from __future__ import annotations

import hashlib
import pickle
from pathlib import Path

_MODEL_CACHE_DIR = Path(__file__).parent.parent.parent / ".model_cache"


def _cache_path(zone_code: str, data_version: str) -> Path:
    safe = hashlib.md5(data_version.encode()).hexdigest()
    return _MODEL_CACHE_DIR / zone_code / f"{safe}.pkl"


def load_cached_models(zone_code: str, data_version: str):
    """Return (models, qlo, qhi, holdout, importances, sigma, resid) or None on miss."""
    p = _cache_path(zone_code, data_version)
    if not p.exists():
        return None
    try:
        with open(p, "rb") as fh:
            return pickle.load(fh)
    except Exception:  # noqa: BLE001 — corrupt cache → retrain
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass
        return None


def save_cached_models(zone_code: str, data_version: str, payload) -> None:
    p = _cache_path(zone_code, data_version)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as fh:
            pickle.dump(payload, fh, protocol=pickle.HIGHEST_PROTOCOL)
        # evict old entries for this zone (keep only the latest 3)
        siblings = sorted(p.parent.glob("*.pkl"), key=lambda f: f.stat().st_mtime)
        for old in siblings[:-3]:
            try:
                old.unlink()
            except Exception:
                pass
    except Exception:  # noqa: BLE001 — cache write failure is non-fatal
        pass
