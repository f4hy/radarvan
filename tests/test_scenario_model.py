"""Equal-skill scenario model: served tables match the training design, and the
symmetry the product promises (team swap, slot order, mirror match) holds."""

import numpy as np
import pytest

from ml.scenario import EffectTables, Layout, contributions, design_row, stack
from radarvan import scenario_inference
from radarvan.api_types import ScenarioPick as P


def _random_tables(seed: int = 0) -> tuple[Layout, np.ndarray, EffectTables]:
    layout = Layout(n_map=3, players=("p1", "p2"))
    beta = np.random.default_rng(seed).normal(size=layout.width)
    off = layout.offsets()
    beta[off["player"]] = 0
    beta[off["intercept"]] = 0
    return layout, beta, stack([EffectTables.from_beta(layout, beta)])


@pytest.mark.parametrize("n", [1, 2, 3, 4])
def test_served_tables_reproduce_the_training_logit(n: int) -> None:
    layout, beta, tables = _random_tables()
    rng = np.random.default_rng(n)
    for _ in range(25):
        a, b = rng.integers(0, 12, n), rng.integers(0, 12, n)
        m = rng.normal(size=3)
        served = contributions(tables, a[None], b[None], m).total[0, 0]
        assert design_row(layout, a, b, m) @ beta == pytest.approx(served, abs=1e-9)


def test_tables_are_symmetric_and_skew() -> None:
    _, _, tables = _random_tables()
    syn, cnt = tables.synergy[0], tables.counter[0]
    np.testing.assert_allclose(syn, syn.T)
    np.testing.assert_allclose(cnt, -cnt.T)


needs_model = pytest.mark.skipif(
    not scenario_inference.model_available(), reason="no scenario artifact"
)


@needs_model
def test_swapping_teams_gives_the_complement() -> None:
    a, b = [P.LASER, P.GLA, P.NUKE], [P.CHINA, P.TOXIN, P.STEALTH]
    ab = scenario_inference.predict(a, b, "defcon6", {}).prob_team_a.value
    ba = scenario_inference.predict(b, a, "defcon6", {}).prob_team_a.value
    assert ab + ba == pytest.approx(1.0)


@needs_model
def test_slot_order_within_a_team_is_irrelevant() -> None:
    first = scenario_inference.predict([P.LASER, P.GLA], [P.CHINA, P.TOXIN], None, {})
    second = scenario_inference.predict([P.GLA, P.LASER], [P.TOXIN, P.CHINA], None, {})
    assert first.prob_team_a.value == pytest.approx(second.prob_team_a.value)


@needs_model
def test_a_mirror_match_is_even_on_any_map() -> None:
    team = [P.AIR, P.DEMO, P.TANK]
    pred = scenario_inference.predict(team, list(reversed(team)), "green pastures", {})
    assert pred.prob_team_a.value == pytest.approx(0.5)


@needs_model
def test_random_faction_slots_average_over_their_generals() -> None:
    random = scenario_inference.predict([P.RANDOM_USA], [P.CHINA], None, {})
    fixed = [
        scenario_inference.predict([g], [P.CHINA], None, {}).prob_team_a.value
        for g in (P.USA, P.AIR, P.LASER, P.SUPER)
    ]
    assert random.combinations == 4
    assert random.prob_team_a.value == pytest.approx(np.mean(fixed))
