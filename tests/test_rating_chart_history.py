from datetime import UTC, date, datetime, timedelta

import numpy as np

from radarvan.player_rating import NamedRating
from radarvan.queries.players import _CHART_EPS, chart_history


def _history(mus: list[float], games_per_day: int) -> list[NamedRating]:
    start = datetime(2025, 1, 1, 2, tzinfo=UTC)
    out = []
    for i, mu in enumerate(mus):
        day, k = divmod(i, games_per_day)
        at = start + timedelta(days=day, minutes=25 * k)
        out.append(
            NamedRating(
                name="p",
                mu=mu,
                sigma=3.0,
                at_date=date(2025, 1, 1) + timedelta(day),
                at=at,
            )
        )
    return out


def test_keeps_every_days_last_game_and_stays_within_eps() -> None:
    rng = np.random.default_rng(0)
    mus = (25 + np.cumsum(rng.normal(0, 0.8, 600))).tolist()
    entries = _history(mus, games_per_day=6)
    kept = chart_history(entries)

    assert len(kept) < len(entries)
    last_of_day = {e.at_date: e for e in entries}.values()
    assert all(e in kept for e in last_of_day)

    x = np.array([e.at.timestamp() for e in entries])
    xk = np.array([e.at.timestamp() for e in kept])
    for sign in (-1, 1):
        y = np.array([e.mu + sign * e.sigma for e in entries])
        yk = np.array([e.mu + sign * e.sigma for e in kept])
        assert np.max(np.abs(np.interp(x, xk, yk) - y)) <= _CHART_EPS


def test_flat_night_collapses_to_its_ends() -> None:
    entries = _history([30.0] * 6, games_per_day=6)
    assert chart_history(entries) == [entries[0], entries[-1]]


def test_empty() -> None:
    assert chart_history([]) == []
