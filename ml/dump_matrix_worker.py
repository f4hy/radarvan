"""Dump the UNK/UNK faction matrix for a single (model.onnx, vocab.json) pair.

Deliberately independent of ``radarvan.ml_inference``: that module serves the
*production* N-model ensemble (``ML_ENSEMBLE_DIR``, one fixed set of
replicates), whereas ``ml.bootstrap_matrix`` needs to evaluate one
freshly-trained candidate model at a time while building up a *new* ensemble -
a different concern that would silently break if it piggybacked on
production's model-loading env vars (see the git history of this file: it
used to set ``ML_MODEL_PATH``/``ML_VOCAB_PATH``, which stopped meaning
anything the moment ``ml_inference`` became ensemble-only).

A standalone process on purpose, in a fresh subprocess per replicate: cheap
(the model is ~6.9K params) and avoids any risk of stale process-level caches
leaking a previous replicate's session into the next one's evaluation.

Usage::

    uv run python -m ml.dump_matrix_worker <model.onnx> <vocab.json> <out.json>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort

from ml.features import EncodedPlayer, Vocab, faction_of
from radarvan.api_types import General

_RECOGNIZED_GENERALS = [g for g in General if g.value >= 0]
_UNKNOWN_MAP_PLACEHOLDER = "Unknown Map"


def _feed(vocab: Vocab, gen1: General, gen2: General) -> dict[str, np.ndarray]:
    """Single-player-per-side feed for one (gen1, gen2) draw, UNK player/map."""

    def side(gen: General) -> EncodedPlayer:
        return EncodedPlayer(
            player=0,  # UNK
            general=vocab.general_idx(int(gen)),
            faction=vocab.faction_idx(faction_of(int(gen))),
            start_pos=0,  # UNK
        )

    a, b = side(gen1), side(gen2)
    ones = np.ones((1, 1), dtype=np.float32)
    return {
        "a_player": np.array([[a.player]], dtype=np.int64),
        "a_general": np.array([[a.general]], dtype=np.int64),
        "a_faction": np.array([[a.faction]], dtype=np.int64),
        "a_start": np.array([[a.start_pos]], dtype=np.int64),
        "a_mask": ones,
        "b_player": np.array([[b.player]], dtype=np.int64),
        "b_general": np.array([[b.general]], dtype=np.int64),
        "b_faction": np.array([[b.faction]], dtype=np.int64),
        "b_start": np.array([[b.start_pos]], dtype=np.int64),
        "b_mask": ones,
        "fmt": np.array([0], dtype=np.int64),  # UNK format
        "map": np.array([vocab.map_idx(_UNKNOWN_MAP_PLACEHOLDER)], dtype=np.int64),
    }


def dump_matrix(model_path: Path, vocab_path: Path) -> list[dict[str, float]]:
    vocab = Vocab.load(vocab_path)
    sess = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    return [
        {
            "general_a": gen1.value,
            "general_b": gen2.value,
            "prob_a_wins": float(
                sess.run(["prob_team_a"], _feed(vocab, gen1, gen2))[0][0]
            ),
        }
        for gen1 in _RECOGNIZED_GENERALS
        for gen2 in _RECOGNIZED_GENERALS
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("vocab", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    args.out.write_text(json.dumps(dump_matrix(args.model, args.vocab)))


if __name__ == "__main__":
    main()
