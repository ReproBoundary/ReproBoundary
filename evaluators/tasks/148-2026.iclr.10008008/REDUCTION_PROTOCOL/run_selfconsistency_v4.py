#!/usr/bin/env python3
"""Run one frozen base or SC stage using the released training implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("base", "sc"), required=True)
    args = parser.parse_args()

    root = Path.cwd()
    code = root / "code"
    if not (code / "main.py").is_file():
        raise SystemExit("run from the project root containing code/main.py")
    processed = code / "datasets/ba_2motifs/processed/data.pt"
    if not processed.is_file():
        raise SystemExit(f"missing released processed dataset: {processed}")

    sys.path.insert(0, str(code))
    os.chdir(code)
    import hydra  # type: ignore
    from omegaconf import OmegaConf  # type: ignore
    import main as released  # type: ignore

    method = "att" if args.stage == "base" else "att_sc"
    with hydra.initialize_config_dir(config_dir=str(code / "configs"), version_base="1.3"):
        cfg = hydra.compose(
            config_name="global", overrides=["dataset=ba_2motifs", f"method={method}"]
        )
    OmegaConf.set_struct(cfg, False)
    cfg.calculate_all_metrics = False
    cfg.method.ba_2motifs.epochs = 30
    cfg.device_id = 0
    cfg.save_dir = "./outputs"

    dataset = released.get_dataset(
        dataset_dir=cfg.dataset.dataset_root,
        dataset_name=cfg.dataset.dataset_name,
        data_split_ratio=cfg.dataset.data_split_ratio,
    )
    split_counts = {name: len(rows) for name, rows in dataset.items()}
    expected = {"all": 1000, "train": 800, "valid": 100, "test": 100}
    if split_counts != expected:
        raise SystemExit(f"unexpected BA-2MOTIFS split: {split_counts}")

    released.set_seed(0)
    metrics = released.run(cfg, cur_round=0, total_round=1, dataset=dataset)
    checkpoint = code / f"outputs/checkpoints/{method}_ba_2motifs_0.pth"
    if not checkpoint.is_file():
        raise SystemExit(f"training did not create checkpoint: {checkpoint}")

    artifact_dir = root / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "stage": args.stage,
        "method": method,
        "epochs": 30,
        "seed": 0,
        "split_seed": 2025,
        "split_counts": split_counts,
        "checkpoint": str(checkpoint.relative_to(root)),
        "checkpoint_sha256": digest(checkpoint),
        "test_accuracy": float(metrics["acc"]) * 100.0,
        "test_explanation_auc": float(metrics["roc_auc"]) * 100.0,
    }
    if args.stage == "sc":
        payload.update({
            "metric_id": "selfconsistency_gat_sc_ba2motifs_auc",
            "metric": "explanation AUC",
            "unit": "percent",
            "value": float(metrics["roc_auc"]) * 100.0,
            "target_graphs": 100,
            "base_checkpoint": "code/outputs/checkpoints/att_ba_2motifs_0.pth",
        })
        destination = artifact_dir / "selfconsistency-ba2motifs-auc.json"
    else:
        destination = artifact_dir / "selfconsistency-base-train.json"
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
