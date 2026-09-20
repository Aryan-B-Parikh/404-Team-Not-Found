"""Capability routers — one per engine, mounted behind the FastAPI gateway."""

from . import ais, anomalies, bob, catalog, forecast, optimise, overview, plan, quality, routing, scenarios

ALL_ROUTERS = [
    overview.router,
    forecast.router,
    anomalies.router,     # W2 (moved out of catalog in Phase 0)
    optimise.router,      # W3
    scenarios.router,     # W3 (absorbed the scenario endpoint)
    routing.router,       # W3
    plan.router,          # W3
    catalog.router,       # W1
    quality.router,       # W1 (new: /api/quality, /api/weather)
    ais.router,           # AIS data management: generate + status
    bob.router,
]
