import numpy as np

from radarvan.line_simplify import simplify


def _max_vertical_error(x, y, keep) -> float:
    return float(np.max(np.abs(y - np.interp(x, x[keep], y[keep]))))


def test_every_dropped_point_within_tolerance() -> None:
    rng = np.random.default_rng(0)
    x = np.arange(2000, dtype=np.float64)
    y = np.cumsum(rng.normal(0, 10, 2000))

    keep = simplify(x, y, tolerance=5.0, max_points=10_000)

    assert keep[0] == 0 and keep[-1] == len(x) - 1
    assert keep == sorted(set(keep))
    assert _max_vertical_error(x, y, keep) <= 5.0
    assert len(keep) < len(x)


def test_budget_stops_early_but_keeps_the_peak() -> None:
    x = np.arange(100, dtype=np.float64)
    y = np.zeros(100)
    y[37] = 1000.0
    y[60:] = np.arange(40) % 2 * 10.0

    keep = simplify(x, y, tolerance=0.0, max_points=5)

    assert len(keep) == 5
    assert 37 in keep


def test_short_inputs_kept_whole() -> None:
    assert simplify(np.array([0.0, 1.0]), np.array([3.0, 4.0]), 0.0, 10) == [0, 1]
    assert simplify(np.array([]), np.array([]), 0.0, 10) == []
