#!/usr/bin/env python3
"""Extract the frozen Cora Feature-0.90 TNT-OOD AUROC from a completed run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", type=Path, default=Path("tntood/results"))
    parser.add_argument(
        "--output", type=Path,
        default=Path("artifacts/texttopoood-cora-feature-0p90-auroc.json"),
    )
    args = parser.parse_args()

    candidates = sorted(
        args.results_root.glob("cora_TNTOOD_feature_run0_seed42_*/results.json"),
        key=lambda path: path.stat().st_mtime_ns,
    )
    if not candidates:
        raise SystemExit("no seed-42 Cora TNT-OOD feature result was produced")
    source = candidates[-1]
    result = json.loads(source.read_text(encoding="utf-8"))
    if result.get("status") != "Completed":
        raise SystemExit(f"latest result did not complete: {source}")
    config = result.get("config", {})
    expected = {
        "datasets": ["cora"], "shift_type": ["feature"], "runs": 1,
        "random_seed": 42, "num_layers": 2, "learning_rate": 0.0001,
        "dropout": 0.3, "use_tntood": True,
    }
    mismatches = {
        key: {"expected": value, "actual": config.get(key)}
        for key, value in expected.items() if config.get(key) != value
    }
    noise = config.get("feature_shift", {}).get("noise_level")
    if noise != 0.9:
        mismatches["feature_shift.noise_level"] = {"expected": 0.9, "actual": noise}
    if mismatches:
        raise SystemExit(f"result does not match frozen configuration: {mismatches}")
    try:
        value = float(
            result["ood_evaluations"]["feature"]["tntood"]["datasets"][0]["auroc"]
        ) * 100.0
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise SystemExit(f"missing official TNT-OOD AUROC in {source}") from error
    payload = {
        "metric_id": "texttopoood_cora_feature_0p90_tnt_auroc",
        "metric": "AUROC",
        "unit": "percent",
        "value": value,
        "id_test_nodes": 1000,
        "ood_target_nodes": 2708,
        "total_scored_nodes": 3708,
        "seed": 42,
        "source": str(source),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
