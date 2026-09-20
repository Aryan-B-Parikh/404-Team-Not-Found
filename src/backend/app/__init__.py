"""Package bootstrap for the PortPulse AI app.

Loaded before any submodule, this makes the app runnable on hosts whose Python
runtime ships without the OpenMP runtime (``libgomp.so.1``) that the LightGBM /
scikit-learn wheels link against — e.g. Vercel serverless functions. We vendor
the library in ``app/lib/`` and load it with ``RTLD_GLOBAL`` so its symbols are
visible to every extension module loaded afterwards. Harmless elsewhere.
"""

from __future__ import annotations

import ctypes
from pathlib import Path

_LIBGOMP = Path(__file__).parent / "lib" / "libgomp.so.1"
if _LIBGOMP.exists():
    try:
        ctypes.CDLL(str(_LIBGOMP), mode=ctypes.RTLD_GLOBAL)
    except OSError:  # pragma: no cover - platform-dependent
        pass
