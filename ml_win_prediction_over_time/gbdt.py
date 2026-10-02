"""The gradient-boosted half of the served model, and its ONNX export.

Trees on the current standardized row plus its change over the last one and two
minutes (``features.with_deltas``). On its own it ties the GRU; averaged with it
the rolling evaluation improves by ~0.02 log-loss, because the GRU is better in
the opening minutes (it passes the prior through smoothly) and the trees are
better mid-game. ``winprob_inference`` serves the average.

Usage::

    .venv-ml/bin/python -m ml_win_prediction_over_time.gbdt <split_dir>

Writes ``<split_dir>/gbdt.onnx``; ``export`` deploys it next to the GRU.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import structlog
from sklearn.ensemble import HistGradientBoostingClassifier

from radarvan.logging_config import configure_logging

from .config import GBDT_OUTPUT
from .features import DELTA_LAGS, FeatureStats, SeqMatch, with_deltas

logger = structlog.get_logger(__name__)

GBDT_FILE = "gbdt.onnx"


def fit_gbdt(
    train: list[SeqMatch], stats: FeatureStats, seed: int = 0
) -> HistGradientBoostingClassifier:
    x = np.concatenate([with_deltas(stats.apply(s.x)) for s in train])
    y = np.concatenate([np.full(s.length, s.label) for s in train])
    # Heavily regularised: ~1k games, and every row of a game shares one label.
    return HistGradientBoostingClassifier(
        learning_rate=0.05,
        max_iter=300,
        max_leaf_nodes=15,
        min_samples_leaf=200,
        l2_regularization=1.0,
        early_stopping=False,
        random_state=seed,
    ).fit(x, y)


def export_gbdt(
    clf: HistGradientBoostingClassifier, path: Path, check: np.ndarray
) -> float:
    """Write the ONNX graph; return the max abs gap to sklearn on ``check`` rows."""
    import onnxruntime as ort
    from skl2onnx import to_onnx
    from skl2onnx.common import tree_ensemble
    from skl2onnx.common.data_types import FloatTensorType

    # skl2onnx 1.20 passes a Python bool for leaves' missing-value flag, which
    # onnx >= 1.20 rejects in an ints attribute ("Expected an int, got a boolean").
    add_node = tree_ensemble.add_node

    def _int_missing(*args, nodes_missing_value_tracks_true=0, **kwargs):  # type: ignore[no-untyped-def]
        return add_node(
            *args,
            nodes_missing_value_tracks_true=int(nodes_missing_value_tracks_true),
            **kwargs,
        )

    tree_ensemble.add_node = _int_missing
    try:
        onx = to_onnx(
            clf,
            initial_types=[("x", FloatTensorType([None, check.shape[1]]))],
            options={id(clf): {"zipmap": False}},
            target_opset={"": 17, "ai.onnx.ml": 3},
        )
    finally:
        tree_ensemble.add_node = add_node
    path.write_bytes(onx.SerializeToString())
    sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    onnx_p = sess.run([GBDT_OUTPUT], {"x": check})[0][:, 1]
    return float(np.abs(onnx_p - clf.predict_proba(check)[:, 1]).max())


def train_and_export(split_dir: Path, seed: int = 0) -> Path:
    from .dataset import encode_all  # torch; keeps fit_gbdt importable without it

    stats = FeatureStats.load(split_dir / "feature_stats.json")
    train = encode_all(split_dir / "train.jsonl.gz")
    clf = fit_gbdt(train, stats, seed)
    check = np.concatenate([with_deltas(stats.apply(s.x)) for s in train[-50:]])
    out = split_dir / GBDT_FILE
    parity = export_gbdt(clf, out, check)
    (split_dir / "gbdt_meta.json").write_text(
        json.dumps(
            {"features": stats.names, "delta_lags": list(DELTA_LAGS), "parity": parity},
            indent=2,
        )
    )
    logger.info("exported gbdt", path=str(out), n_train=len(train), parity_error=parity)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split_dir", type=Path)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    configure_logging(dev=True)
    train_and_export(args.split_dir, args.seed)


if __name__ == "__main__":
    main()
