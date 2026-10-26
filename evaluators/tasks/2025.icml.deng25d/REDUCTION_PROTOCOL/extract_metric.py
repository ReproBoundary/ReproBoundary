#!/usr/bin/env python3
"""Serialize the frozen StaB-ddG overall RMSE without exposing a reference value."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import sys
from pathlib import Path

import pandas as pd


EXPECTED_COUNT = 1491
METRIC_ID = "skempi2_released_test_stabddg_overall_rmse"
PROJECT_ID = "2025.icml.deng25d"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--target-manifest",
        default="REDUCTION_PROTOCOL/skempi_test_ids.jsonl",
    )
    args = parser.parse_args()

    predictions = Path(args.predictions)
    manifest = Path(args.target_manifest)
    output = Path(args.output)
    df = pd.read_csv(predictions)
    required = {"#Pdb", "Mutation", "ddG", "ddG_pred"}
    if not required.issubset(df.columns):
        raise SystemExit(f"missing columns: {sorted(required - set(df.columns))}")
    if len(df) != EXPECTED_COUNT:
        raise SystemExit(f"expected {EXPECTED_COUNT} predictions, got {len(df)}")
    if df[list(required)].isnull().any().any():
        raise SystemExit("target predictions or labels contain missing values")
    if not all(math.isfinite(float(x)) for x in df["ddG_pred"]):
        raise SystemExit("predictions contain non-finite values")

    expected = sorted(json.loads(line)["id"] for line in manifest.read_text().splitlines() if line)
    actual = []
    for _, row in df.iterrows():
        mutations = ast.literal_eval(row["Mutation"])
        if not isinstance(mutations, list) or not all(isinstance(x, str) for x in mutations):
            raise SystemExit("invalid mutation encoding")
        actual.append(f"{row['#Pdb']}|{','.join(mutations)}")
    if sorted(actual) != expected or len(set(actual)) != EXPECTED_COUNT:
        raise SystemExit("prediction rows do not match the frozen target identity manifest")

    # This is the point-estimate definition in the official baselines/eval_utils.py.
    rmse = math.sqrt(((df["ddG"] - df["ddG_pred"]) ** 2).mean())
    payload = {
        "schema_version": "4.0",
        "project_id": PROJECT_ID,
        "target_metric_id": METRIC_ID,
        "target_metric_obtained": True,
        "sample_count": EXPECTED_COUNT,
        "overall_rmse": rmse,
        "unit": "kcal/mol",
        "predictions_sha256": sha256(predictions),
        "target_manifest_sha256": sha256(manifest),
        "evaluator_source": "baselines/eval_utils.py:83",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    main()
