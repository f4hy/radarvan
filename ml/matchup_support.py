"""How many real games actually back each general-vs-general cell of the faction
matrix (``GET /api/predict/faction_matrix``, ``ml.bootstrap_matrix``).

The matrix is a 12x12 grid of *model* outputs, but the model can (and does)
extrapolate for pairings it saw only a handful of times - the embedding/matchup
term still produces a confident-looking number even at n=1. This script counts
direct observations per ordered (general_a, general_b) pair from a split's
train data, so a cell's model output can be read alongside how much real
evidence backed it.

Counts every opposing-player pair within a match (not just 1v1), both
directions - a team_a=X vs team_b=Y match adds one observation to (X, Y) and
one to (Y, X), matching how the matrix itself is oriented (each cell is a
directional "X vs Y" read, and either team's general can appear on either
side of the matrix).

Usage::

    uv run python -m ml.matchup_support ml/data/split-YYYYMMDD-temporal/train.jsonl.gz

Writes ``matchup_support.json`` next to the input file: per-cell counts plus a
summary (min/median/max, and the sparsest cells) for eyeballing which parts of
the matrix are backed by real data vs. mostly extrapolation.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

import structlog

from radarvan.api_types import General

from .features import resolved_real_players
from .snapshot import load_snapshot

logger = structlog.get_logger(__name__)


def count_matchup_support(matches_path: Path) -> Counter[tuple[int, int]]:
    counts: Counter[tuple[int, int]] = Counter()
    for match in load_snapshot(matches_path):
        teams: dict[int, list[int]] = {}
        for _, p in resolved_real_players(match):
            if int(p.general) < 0:  # UNRECOGNIZED
                continue
            teams.setdefault(p.team, []).append(int(p.general))
        if len(teams) != 2:
            continue
        (_, gens_a), (_, gens_b) = sorted(teams.items())
        for ga in gens_a:
            for gb in gens_b:
                counts[(ga, gb)] += 1
                counts[(gb, ga)] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matches", type=Path, help="train.jsonl.gz (or any snapshot)")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    counts = count_matchup_support(args.matches)
    generals = [g for g in General if g.value >= 0]
    cells = [
        {"general_a": ga.value, "general_b": gb.value, "n": counts.get((ga.value, gb.value), 0)}
        for ga in generals
        for gb in generals
    ]
    ns = [c["n"] for c in cells]
    sparsest = sorted(cells, key=lambda c: c["n"])[:10]

    out = {
        "source": str(args.matches),
        "cells": cells,
        "summary": {
            "min": min(ns),
            "median": statistics.median(ns),
            "max": max(ns),
            "n_cells_under_5": sum(1 for n in ns if n < 5),
            "n_cells_zero": sum(1 for n in ns if n == 0),
        },
        "sparsest": sparsest,
    }
    out_path = args.out or args.matches.parent / "matchup_support.json"
    out_path.write_text(json.dumps(out, indent=2))
    logger.info("wrote matchup support", path=str(out_path), **out["summary"])
    for c in sparsest:
        logger.info(
            "sparse cell",
            general_a=General(c["general_a"]).name,
            general_b=General(c["general_b"]).name,
            n=c["n"],
        )


if __name__ == "__main__":
    main()
