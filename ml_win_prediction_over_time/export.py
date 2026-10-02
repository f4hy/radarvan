"""Export a trained win-prob-over-time model to ONNX for torch-free serving.

Mirrors ``ml/export.py``: the production app has no torch, so the deployable
artifact is an ONNX graph served with onnxruntime + numpy. The graph takes the
standardized feature sequence ``x`` (``[batch, time, len(stats.names)]``, exactly what
``features.match_to_sequence`` + ``FeatureStats`` produce) and outputs
``prob_team_a`` (``[batch, time]``) — the sigmoid is baked in.

Several runs (seeds trained on the same split) export as one graph averaging
their calibrated probabilities - the rolling evaluation scores a seed bag, so
that is what ships.

Usage::

    uv run --group ml python -m ml_win_prediction_over_time.export  # latest run
    uv run --group ml python -m ml_win_prediction_over_time.export <run_dir>...

Writes ``<run_dir>/model.onnx`` + ``<run_dir>/onnx_meta.json`` and copies the
serving bundle to the repo root: ``ml_winprob_over_time.onnx``, ``..._stats.json``,
``..._prior.json`` and the split's GBDT, ``..._gbdt.onnx`` (see ``gbdt.py``).
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

from .config import DATA_DIR
from .features import DELTA_LAGS, FeatureStats
from .gbdt import GBDT_FILE
from .predict import load_run

logger = structlog.get_logger(__name__)

OPSET = 17
# Deployable artifacts at the repo root (next to ml_ensemble/).
ROOT = Path(__file__).resolve().parents[1]
ROOT_MODEL = ROOT / "ml_winprob_over_time.onnx"
ROOT_STATS = ROOT / "ml_winprob_over_time_stats.json"
ROOT_PRIOR = ROOT / "ml_winprob_over_time_prior.json"
ROOT_GBDT = ROOT / "ml_winprob_over_time_gbdt.onnx"


class _ExportWrapper(nn.Module):
    """Runs every GRU with its own temperature and averages the probabilities.

    The temperatures travel with the graph because ``winprob_inference`` serves
    the ONNX file alone and has nowhere else to read them from.
    """

    def __init__(self, models: list[nn.Module], temperatures: list[float]):
        super().__init__()
        self.models = nn.ModuleList(models)
        self.register_buffer("temperatures", torch.tensor(temperatures))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        probs = [
            torch.sigmoid(m(x) / self.temperatures[i])
            for i, m in enumerate(self.models)
        ]
        return torch.stack(probs).mean(dim=0)  # [B, T]


def find_latest_run(data_dir: Path = DATA_DIR) -> Path:
    runs = [p.parent for p in data_dir.glob("*/runs/*/best.ckpt")]
    if not runs:
        raise SystemExit(
            f"no trained runs found under {data_dir} (expected */runs/*/best.ckpt)"
        )
    return max(runs, key=lambda p: p.stat().st_mtime)


def _verify_parity(wrapper: _ExportWrapper, onnx_path: Path, n_features: int) -> float:
    """Max abs diff between torch and onnxruntime on a random multi-row batch."""
    import onnxruntime as ort

    g = torch.Generator().manual_seed(0)
    x = torch.randn(5, 7, n_features, generator=g)
    with torch.no_grad():
        torch_prob = wrapper(x).numpy()
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    onnx_prob = sess.run(["prob_team_a"], {"x": x.numpy()})[0]
    return float(np.abs(torch_prob - onnx_prob).max())


def export(run_dirs: list[Path]) -> Path:
    loaded = [load_run(r) for r in run_dirs]
    stats = loaded[0].stats
    if any(r.stats.names != stats.names or r.stats.mean != stats.mean for r in loaded):
        raise SystemExit("runs were trained on different splits; cannot bag them")
    temperatures = [r.temperature for r in loaded]
    wrapper = _ExportWrapper([r.module.model for r in loaded], temperatures).eval()
    run_dir = run_dirs[0]
    out_path = run_dir / "model.onnx"
    n_features = len(stats.names)
    example = torch.zeros((1, 4, n_features), dtype=torch.float32)

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

    parity = _verify_parity(wrapper, out_path, n_features)
    meta = {
        "opset": OPSET,
        "inputs": ["x"],
        "outputs": ["prob_team_a"],
        "features": stats.names,
        "runs": [str(r) for r in run_dirs],
        "note": (
            "x is the standardized feature sequence [batch, time, n_features] from "
            "features.match_to_sequence + FeatureStats (see "
            "ml_winprob_over_time_stats.json). prob_team_a[b, t] is P(side a wins) "
            "given events up to window t, for the model's own (hashed) side a."
        ),
        "temperatures": temperatures,
        "max_abs_parity_error": parity,
    }
    (run_dir / "onnx_meta.json").write_text(json.dumps(meta, indent=2))
    logger.info(
        "exported", path=str(out_path), n_models=len(run_dirs), parity_error=parity
    )
    return out_path


def deploy_to_root(run_dir: Path, model_path: Path) -> None:
    """Copy the serving bundle to the repo root, GBDT included and checked."""
    split_dir = run_dir.parent.parent
    gbdt_src = split_dir / GBDT_FILE
    if not gbdt_src.exists():
        raise SystemExit(
            f"no {gbdt_src}; run `python -m ml_win_prediction_over_time.gbdt "
            f"{split_dir}` first"
        )
    meta = json.loads((split_dir / "gbdt_meta.json").read_text())
    names = FeatureStats.load(run_dir / "feature_stats.json").names
    if meta["features"] != names or meta["delta_lags"] != list(DELTA_LAGS):
        raise SystemExit(
            "gbdt was fit on different inputs than the GRU and serving use"
        )
    shutil.copy(model_path, ROOT_MODEL)
    shutil.copy(run_dir / "feature_stats.json", ROOT_STATS)
    shutil.copy(run_dir / "pregame_prior.json", ROOT_PRIOR)
    shutil.copy(gbdt_src, ROOT_GBDT)
    logger.info("deployed to root", model=str(ROOT_MODEL), gbdt=str(ROOT_GBDT))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "run_dirs",
        type=Path,
        nargs="*",
        help="run bundles to bag into one graph (default: most recently trained)",
    )
    parser.add_argument(
        "--no-deploy",
        action="store_true",
        help="don't copy the artifacts to the repo root",
    )
    args = parser.parse_args()
    run_dirs = args.run_dirs or [find_latest_run()]
    logger.info("exporting runs", run_dirs=[str(r) for r in run_dirs])
    model_path = export(run_dirs)
    if not args.no_deploy:
        deploy_to_root(run_dirs[0], model_path)


if __name__ == "__main__":
    main()
