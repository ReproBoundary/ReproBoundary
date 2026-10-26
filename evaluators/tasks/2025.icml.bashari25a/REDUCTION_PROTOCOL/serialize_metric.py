#!/usr/bin/env python3
"""Serialize the frozen Table 6 metric from the repository's raw result table."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results_pickle", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()

    results = pd.read_pickle(args.results_pickle)
    selected = results[results["level"].astype(float) == 0.01]
    standard = selected[selected["Type"] == "Naive"]["Power"].astype(float)
    label_trim = selected[selected["Type"] == "LT"]["Power"].astype(float)
    if len(standard) != 100 or len(label_trim) != 100:
        raise ValueError("expected exactly 100 Standard and 100 Label-Trim rows")
    standard_mean = float(standard.mean())
    relative_power = float(round(float(label_trim.mean()) / standard_mean, 3))
    relative_se = float(round(float(label_trim.std(ddof=1)) / math.sqrt(100) / standard_mean, 4))
    payload = {
        "metric_id": "cifar10_texture_react_label_trim_relative_power",
        "relative_power": relative_power,
        "standard_error": relative_se,
        "target_type_i_error": 0.01,
        "contamination_rate": 0.03,
        "labeling_budget": 50,
        "random_split_count": 100,
        "raw_results_sha256": sha256(args.results_pickle),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
