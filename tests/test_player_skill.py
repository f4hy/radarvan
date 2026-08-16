"""Tridiagonal Newton solve used by the Whole-History Rating fit.

``_solve_symmetric_tridiagonal`` replaced a dense ``np.linalg.solve`` over a
materialized n x n matrix, so what matters is that it still produces the same
answer - hence comparing against the dense solve rather than fixed expected
values.
"""

import numpy as np
import pytest

from radarvan.player_skill import _solve_symmetric_tridiagonal


def _dense(diag: np.ndarray, off: np.ndarray) -> np.ndarray:
    n = diag.size
    matrix = np.diag(diag)
    if n > 1:
        matrix = matrix + np.diag(off, 1) + np.diag(off, -1)
    return matrix


@pytest.mark.parametrize("n", [1, 2, 3, 5, 17, 120])
def test_matches_dense_solve(n: int) -> None:
    rng = np.random.default_rng(1234 + n)
    off = -rng.random(max(0, n - 1))
    # Diagonally dominant and positive definite, matching the Hessian shape the
    # fit actually produces (positive data + ridge terms on the diagonal).
    diag = rng.random(n) + 1.0
    if n > 1:
        diag[:-1] += np.abs(off)
        diag[1:] += np.abs(off)
    rhs = rng.standard_normal(n)

    got = _solve_symmetric_tridiagonal(diag, off, rhs)
    expected = np.linalg.solve(_dense(diag, off), rhs)

    assert np.allclose(got, expected, rtol=1e-10, atol=1e-12)


def test_zero_off_diagonal_is_elementwise_division() -> None:
    """With no prior coupling (all off-diagonals zero) the system is diagonal."""
    diag = np.array([2.0, 4.0, 5.0])
    rhs = np.array([1.0, 2.0, 10.0])
    got = _solve_symmetric_tridiagonal(diag, np.zeros(2), rhs)
    assert np.allclose(got, rhs / diag)
