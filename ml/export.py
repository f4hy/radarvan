"""Export a trained model to ONNX for portable, torch-free CPU inference.

ONNX Runtime is a small, fast CPU dependency that needs no torch at serving time
(the production app has no torch), so the exported ``model.onnx`` is the most
deployment-light artifact. The calibration temperature is baked in — the model's
single output is the calibrated ``prob_team_a``.

Usage::

    uv run python -m ml.export                 # most recently trained run
    uv run python -m ml.export <run_dir>       # a specific run bundle

Writes ``<run_dir>/model.onnx`` + ``<run_dir>/onnx_meta.json`` (input spec).
Encode inputs with the run's ``vocab.json`` exactly as ``ml.features`` does.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import structlog
import torch
from torch import nn

from .config import DATA_DIR
from .dataset import Batch
from .predict import load_bundle

logger = structlog.get_logger(__name__)

# Order matters: these are the positional ONNX graph inputs.
_TEAM_A = ["a_player", "a_general", "a_faction", "a_start", "a_mask"]
_TEAM_B = ["b_player", "b_general", "b_faction", "b_start", "b_mask"]
INPUT_NAMES = _TEAM_A + _TEAM_B + ["map", "fmt"]
OUTPUT_NAMES = ["prob_team_a", "raw_logit"]
OPSET = 17


class _ExportWrapper(nn.Module):
    """Flattens Batch into explicit tensor args and returns calibrated outputs."""

    def __init__(self, model: nn.Module):
        super().__init__()
        self.model = model

    def forward(
        self,
        a_player: torch.Tensor,
        a_general: torch.Tensor,
        a_faction: torch.Tensor,
        a_start: torch.Tensor,
        a_mask: torch.Tensor,
        b_player: torch.Tensor,
        b_general: torch.Tensor,
        b_faction: torch.Tensor,
        b_start: torch.Tensor,
        b_mask: torch.Tensor,
        map_: torch.Tensor,
        fmt: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        b = a_player.shape[0]
        unused = torch.zeros(b)  # label/duration are not model inputs
        batch = Batch(
            a_player=a_player, a_general=a_general, a_faction=a_faction,
            a_start=a_start, a_mask=a_mask,
            b_player=b_player, b_general=b_general, b_faction=b_faction,
            b_start=b_start, b_mask=b_mask,
            map=map_, fmt=fmt, label=unused, duration=unused,
        )
        terms = self.model.explain(batch)
        prob, raw = terms["prob_team_a"], terms["raw_logit"]
        # When starting position is disabled (the default) the model ignores
        # a_start/b_start, so ONNX would prune them as dead inputs. Add a zero
        # contribution to keep all 12 inputs live, so the ONNX interface always
        # matches what ml.dataset.collate produces, in every config.
        if self.model.start_emb is None:
            keep = 0.0 * (a_start.sum() + b_start.sum()).to(raw.dtype)
            prob, raw = prob + keep, raw + keep
        return prob, raw


def find_latest_run(data_dir: Path = DATA_DIR) -> Path:
    """Most recently modified run bundle (dir containing best.ckpt) under data_dir."""
    runs = [p.parent for p in data_dir.glob("*/runs/*/best.ckpt")]
    if not runs:
        raise SystemExit(
            f"no trained runs found under {data_dir} (expected */runs/*/best.ckpt)"
        )
    return max(runs, key=lambda p: p.stat().st_mtime)


def _example_inputs() -> tuple[torch.Tensor, ...]:
    """A tiny valid batch (B=1, 2v2). Index 0 == UNK is always in range."""
    ids = torch.zeros((1, 2), dtype=torch.long)
    mask = torch.ones((1, 2), dtype=torch.float32)
    scalar = torch.zeros(1, dtype=torch.long)
    return (
        ids, ids, ids, ids, mask,  # team a
        ids, ids, ids, ids, mask,  # team b
        scalar, scalar,            # map, fmt
    )


def _dynamic_axes() -> dict[str, dict[int, str]]:
    axes: dict[str, dict[int, str]] = {n: {0: "batch"} for n in INPUT_NAMES}
    for n in _TEAM_A:
        axes[n][1] = "team_a"
    for n in _TEAM_B:
        axes[n][1] = "team_b"
    for n in OUTPUT_NAMES:
        axes[n] = {0: "batch"}
    return axes


def export(run_dir: Path) -> Path:
    module, _vocab, _cfg = load_bundle(run_dir)  # temperature baked in
    wrapper = _ExportWrapper(module.model).eval()
    out_path = run_dir / "model.onnx"
    args = _example_inputs()

    torch.onnx.export(
        wrapper,
        args,
        str(out_path),
        input_names=INPUT_NAMES,
        output_names=OUTPUT_NAMES,
        dynamic_axes=_dynamic_axes(),
        opset_version=OPSET,
    )

    parity = _verify_parity(wrapper, out_path)
    meta = {
        "opset": OPSET,
        "inputs": INPUT_NAMES,
        "outputs": OUTPUT_NAMES,
        "int64_inputs": [
            n for n in INPUT_NAMES if n not in ("a_mask", "b_mask")
        ],
        "float32_inputs": ["a_mask", "b_mask"],
        "note": (
            "Encode with the sibling vocab.json (see ml.features). Calibration "
            "temperature is baked in; prob_team_a is the calibrated probability "
            "that the lower-team-id side wins. Pad both teams to equal length and "
            "set mask=0 for padding."
        ),
        "max_abs_parity_error": parity,
    }
    (run_dir / "onnx_meta.json").write_text(json.dumps(meta, indent=2))
    logger.info("exported", path=str(out_path), parity_error=parity)
    return out_path


def _verify_parity(wrapper: nn.Module, onnx_path: Path) -> float:
    """Max abs diff between torch and onnxruntime on a random multi-row batch."""
    import onnxruntime as ort

    g = torch.Generator().manual_seed(0)
    b, ta, tb = 5, 3, 2

    def rand_ids(t: int) -> torch.Tensor:
        return torch.randint(0, 4, (b, t), generator=g)

    inputs = {
        "a_player": rand_ids(ta), "a_general": rand_ids(ta),
        "a_faction": rand_ids(ta), "a_start": rand_ids(ta),
        "a_mask": torch.ones((b, ta)),
        "b_player": rand_ids(tb), "b_general": rand_ids(tb),
        "b_faction": rand_ids(tb), "b_start": rand_ids(tb),
        "b_mask": torch.ones((b, tb)),
        "map": torch.zeros(b, dtype=torch.long),
        "fmt": torch.zeros(b, dtype=torch.long),
    }
    with torch.no_grad():
        torch_prob = wrapper(*[inputs[n] for n in INPUT_NAMES])[0].numpy()

    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    feed = {n: v.numpy() for n, v in inputs.items()}
    onnx_prob = sess.run(["prob_team_a"], feed)[0]
    return float(np.abs(torch_prob - onnx_prob).max())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "run_dir",
        type=Path,
        nargs="?",
        default=None,
        help="run bundle to export (default: most recently trained)",
    )
    args = parser.parse_args()
    run_dir = args.run_dir or find_latest_run()
    logger.info("exporting run", run_dir=str(run_dir))
    export(run_dir)


if __name__ == "__main__":
    main()
