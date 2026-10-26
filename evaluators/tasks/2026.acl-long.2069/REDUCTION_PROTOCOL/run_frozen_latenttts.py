#!/usr/bin/env python3
"""Frozen LatentTTS COCONUT Coverage@4 evaluation.

This wrapper only binds the paper implementation to the preregistered seed,
checkpoint, full GSM8K test file, and metric-serialization contract.  The
sampling and scoring implementation remains in ``src.infer_gpt2``.
"""

from __future__ import annotations

import contextlib
import io
import json
import re
from pathlib import Path

from src.infer_gpt2 import main
from src.utils import set_seed


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "frozen_seed0"
LOG_PATH = OUTPUT_DIR / "inference_stdout.log"
METRICS_PATH = OUTPUT_DIR / "metrics.json"


def run() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    set_seed(0)

    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        main(
            model_type="coconut",
            model_dtype="bf16",
            data_path=str(PROJECT_ROOT / "data" / "gsm_test.json"),
            n_samples=4,
            batch_size=64,
            latent_length=6,
            max_new_tokens=512,
            do_sample=True,
            sampling_by="dropout",
            dropout_p=0.2,
            noise_std=None,
        )

    stdout = captured.getvalue()
    print(stdout, end="")
    LOG_PATH.write_text(stdout, encoding="utf-8")
    match = re.search(r"^Pass@4:\s*([0-9]+(?:\.[0-9]+)?)\s*$", stdout, re.MULTILINE)
    if match is None:
        raise RuntimeError("Frozen evaluator did not emit Pass@4")

    value = float(match.group(1))
    METRICS_PATH.write_text(
        json.dumps(
            {
                "metric_id": "gsm8k_test_coconut_mc_dropout_coverage_at_4",
                "coverage_at_4_percent": value,
                "sample_count": 1319,
                "trajectory_count_per_sample": 4,
                "seed": 0,
                "data_sha256": "46ce5b0c44fde0bfc8cf1e7492aa640b96111d9dcb80a54340d9911141a9caa9",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    run()
