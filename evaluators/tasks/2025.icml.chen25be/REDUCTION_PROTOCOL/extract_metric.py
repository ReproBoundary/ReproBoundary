#!/usr/bin/env python3
"""Serialize the official VisionTS metrics.npy result without recomputation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    values = np.load(args.metrics)
    if values.shape != (7,):
        raise SystemExit(f"expected 7 official metrics, found shape {values.shape}")
    predictions = np.load(args.predictions, mmap_mode="r")
    labels = np.load(args.labels, mmap_mode="r")
    expected_shape = (2785, 96, 7)
    if predictions.shape != expected_shape or labels.shape != expected_shape:
        raise SystemExit(
            f"expected prediction and label shapes {expected_shape}, "
            f"found {predictions.shape} and {labels.shape}"
        )
    result = {
        "project_id": "2025.icml.chen25be",
        "metric": "MSE",
        "value": float(values[1]),
        "mae": float(values[0]),
        "test_window_count": 2785,
        "prediction_length": 96,
        "variable_count": 7,
        "predictions_sha256": sha256(args.predictions),
        "labels_sha256": sha256(args.labels),
        "official_metrics_sha256": sha256(args.metrics)
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
