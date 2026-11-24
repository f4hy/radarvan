"""Ramer-Douglas-Peucker with a vertical error and a point budget.

Vendored from plotsimplify's NumPy backend, cut down to the vertical metric
over gap-free data.
"""

import heapq

import numpy as np


def _farthest(x: np.ndarray, y: np.ndarray, s: int, e: int) -> tuple[float, int]:
    dx = x[e] - x[s]
    dy = y[e] - y[s]
    d = np.abs(dy * (x[s + 1 : e] - x[s]) - dx * (y[s + 1 : e] - y[s]))
    i = int(np.argmax(d))
    return float(d[i]) / dx, s + 1 + i


def simplify(
    x: np.ndarray, y: np.ndarray, tolerance: float, max_points: int
) -> list[int]:
    """Sorted indices to keep so every dropped point lies within `tolerance`
    (in y units) of the line through the kept ones, splitting the worst segment
    first and stopping early at `max_points`. `x` must be strictly increasing."""
    n = len(x)
    if n <= 2:
        return list(range(n))
    keep = [0, n - 1]
    d, k = _farthest(x, y, 0, n - 1)
    heap = [(-d, 0, n - 1, k)]
    while heap and -heap[0][0] > tolerance and len(keep) < max_points:
        _, s, e, k = heapq.heappop(heap)
        keep.append(k)
        if k - s >= 2:
            d, m = _farthest(x, y, s, k)
            heapq.heappush(heap, (-d, s, k, m))
        if e - k >= 2:
            d, m = _farthest(x, y, k, e)
            heapq.heappush(heap, (-d, k, e, m))
    return sorted(keep)
