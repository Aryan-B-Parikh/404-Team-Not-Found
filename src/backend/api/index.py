"""Vercel serverless entrypoint — mounts the FastAPI gateway as an ASGI handler.

``@vercel/python`` picks up the ``app`` ASGI callable from this module. The
PostgreSQL connection comes from the platform env vars (Supabase pooler); the
database is seeded already, so the startup bootstrap is a no-op on warm data.

Vercel's Python runtime ships without ``libgomp.so.1`` (OpenMP), which the
LightGBM / scikit-learn wheels link against — we vendor it in ``app/lib/`` and
the app package preloads it at import time (see ``app/__init__.py``).
"""
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")  # serverless: single-vCPU friendly

from app.main import app  # noqa: E402,F401  (ASGI callable)
