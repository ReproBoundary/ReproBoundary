#!/usr/bin/env python3
"""Validate three complete M3CoT prediction files and aggregate official metrics."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np


SEEDS = (323, 500, 900)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--selected-ids", type=Path, required=True)
    parser.add_argument("--official-evaluator", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, default=2318)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_official_evaluator(path: Path):
    spec = importlib.util.spec_from_file_location("sinktrack_official_eval", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load evaluator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_prediction_file(path: Path, expected_ids: list[str]) -> None:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise RuntimeError(f"{path}:{line_number}: malformed JSON") from error
    ids = [str(row.get("id")) for row in rows]
    if ids != expected_ids:
        raise RuntimeError(f"{path}: IDs or order differ from the frozen test manifest")
    if any(not str(row.get("pred", "")).strip() for row in rows):
        raise RuntimeError(f"{path}: empty prediction found")


def main() -> None:
    args = parse_args()
    expected_ids = [line.strip() for line in args.selected_ids.read_text().splitlines() if line.strip()]
    if len(expected_ids) != args.expected_count or len(set(expected_ids)) != args.expected_count:
        raise RuntimeError("frozen selected-ID manifest has an invalid count or duplicate IDs")

    official = load_official_evaluator(args.official_evaluator)
    per_seed = []
    for seed in SEEDS:
        path = args.input_dir / f"sinktrack_{seed}.jsonl"
        validate_prediction_file(path, expected_ids)
        accuracy, macro_f1 = official.process_single_file(str(path))
        per_seed.append(
            {"seed": seed, "accuracy_percent": accuracy * 100.0, "macro_f1_percent": macro_f1 * 100.0}
        )

    accuracies = np.asarray([item["accuracy_percent"] for item in per_seed], dtype=float)
    macro_f1s = np.asarray([item["macro_f1_percent"] for item in per_seed], dtype=float)
    result = {
        "schema_version": "sinktrack-m3cot-evaluation-v1",
        "input_count_per_seed": args.expected_count,
        "seeds": list(SEEDS),
        "per_seed": per_seed,
        "accuracy_percent_mean": float(np.mean(accuracies)),
        "accuracy_percent_variance": float(np.var(accuracies)),
        "macro_f1_percent_mean": float(np.mean(macro_f1s)),
        "macro_f1_percent_variance": float(np.var(macro_f1s)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
