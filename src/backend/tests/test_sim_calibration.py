"""B-4 regression: the simulator must draw a plausible mixed operational state.

Across seeds 1-5 the median port index at t0 lands in 40-75 (not pinned at the
100 cap like the old 4.6h demand gap produced) and berth utilisation stays
<= 90%. Slow: five full SimPy runs.
"""

from __future__ import annotations

import statistics

import pytest

from app.services.simulation import HISTORY_HOURS, WARMUP_HOURS, simulate

pytestmark = pytest.mark.slow

SEEDS = [1, 2, 3, 4, 5]


def test_sim_seeds_draw_a_plausible_mixed_state():
    indices: list[float] = []
    utils: list[float] = []
    for seed in SEEDS:
        r = simulate(seed=seed)
        port = [o for o in r.observations if o["zone_code"] == "Z-PORT" and o["hours_ago"] == 0]
        assert port, f"seed {seed}: no port observation at t0"
        indices.append(port[0]["index"])
        busy = [b["busy_hours"] for b in r.berth_stats.values()]
        utils.append(100.0 * sum(busy) / (len(busy) * (HISTORY_HOURS + WARMUP_HOURS)))

    median_idx = statistics.median(indices)
    assert 40 <= median_idx <= 75, f"median port index {median_idx} out of band: {indices}"
    assert max(utils) <= 90.0, f"berth utilisation out of band: {utils}"
