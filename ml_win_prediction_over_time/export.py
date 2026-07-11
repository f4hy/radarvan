"""Export a trained win-prob-over-time model to ONNX for torch-free serving.

Mirrors ``ml/export.py``: the production app has no torch, so the deployable
artifact is an ONNX graph served with onnxruntime + numpy. The graph takes the
standardized feature sequence ``x`` (``[batch, time, N_FEATURES]``, exactly what
``features.match_to_sequence`` + ``FeatureStats`` produce) and outputs
``prob_team_a`` (``[batch, time]``) — the sigmoid is baked in.

Usage::

    uv run --group ml python -m ml_win_prediction_over_time.export            # latest run
    uv run --group ml python -m ml_win_prediction_over_time.export <run_dir>  # specific run

Writes ``<run_dir>/model.onnx`` + ``<run_dir>/onnx_meta.json`` and copies the
deployable pair to the repo root (``ml_winprob_over_time.onnx`` +
``ml_winprob_over_time_stats.json``), the way ``ml_model.onnx`` is deployed.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
import structlog
import torch
from torch import nn

from .config import N_FEATURES, DATA_DIR
from .predict import load_run

logger = structlog.get_logger(__name__)

OPSET = 17
# Deployable artifacts at the repo root (next to ml_model.onnx).
ROOT = Path(__file__).resolve().parents[1]
ROOT_MODEL = ROOT / "ml_winprob_over_time.onnx"
ROOT_STATS = ROOT / "ml_winprob_over_time_stats.json"


class _ExportWrapper(nn.Module):
    """Runs the GRU and bakes the sigmoid in, so the graph outputs a probability."""

    def __init__(self, model: nn.Module):
        super().__init__()
        self.model = model

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.sigmoid(self.model(x))  # [B, T]


def find_latest_run(data_dir: Path = DATA_DIR) -> Path:
    runs = [p.parent for p in data_dir.glob("*/runs/*/best.ckpt")]
    if not runs:
        raise SystemExit(
            f"no trained runs found under {data_dir} (expected */runs/*/best.ckpt)"
        )
    return max(runs, key=lambda p: p.stat().st_mtime)


def _verify_parity(wrapper: _ExportWrapper, onnx_path: Path) -> float:
    """Max abs diff between torch and onnxruntime on a random multi-row batch."""
    import onnxruntime as ort

    g = torch.Generator().manual_seed(0)
    x = torch.randn(5, 7, N_FEATURES, generator=g)
    with torch.no_grad():
        torch_prob = wrapper(x).numpy()
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    onnx_prob = sess.run(["prob_team_a"], {"x": x.numpy()})[0]
    return float(np.abs(torch_prob - onnx_prob).max())


def export(run_dir: Path) -> Path:
    module, _stats = load_run(run_dir)
    wrapper = _ExportWrapper(module.model).eval()
    out_path = run_dir / "model.onnx"
    example = torch.zeros((1, 4, N_FEATURES), dtype=torch.float32)

    torch.onnx.export(
        wrapper,
        (example,),
        str(out_path),
        input_names=["x"],
        output_names=["prob_team_a"],
        dynamic_axes={
            "x": {0: "batch", 1: "time"},
            "prob_team_a": {0: "batch", 1: "time"},
        },
        opset_version=OPSET,
    )

    parity = _verify_parity(wrapper, out_path)
    meta = {
        "opset": OPSET,
        "inputs": ["x"],
        "outputs": ["prob_team_a"],
        "n_features": N_FEATURES,
        "note": (
            "x is the standardized feature sequence [batch, time, n_features] from "
            "features.match_to_sequence + FeatureStats (see "
            "ml_winprob_over_time_stats.json). prob_team_a[b, t] is P(team_a wins) "
            "given events up to window t; team_a is the lower team id."
        ),
        "max_abs_parity_error": parity,
    }
    (run_dir / "onnx_meta.json").write_text(json.dumps(meta, indent=2))
    logger.info("exported", path=str(out_path), parity_error=parity)
    return out_path


def deploy_to_root(run_dir: Path, model_path: Path) -> None:
    shutil.copy(model_path, ROOT_MODEL)
    shutil.copy(run_dir / "feature_stats.json", ROOT_STATS)
    logger.info("deployed to root", model=str(ROOT_MODEL), stats=str(ROOT_STATS))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "run_dir",
        type=Path,
        nargs="?",
        default=None,
        help="run bundle to export (default: most recently trained)",
    )
    parser.add_argument(
        "--no-deploy",
        action="store_true",
        help="don't copy the artifacts to the repo root",
    )
    args = parser.parse_args()
    run_dir = args.run_dir or find_latest_run()
    logger.info("exporting run", run_dir=str(run_dir))
    model_path = export(run_dir)
    if not args.no_deploy:
        deploy_to_root(run_dir, model_path)


if __name__ == "__main__":
    main()
