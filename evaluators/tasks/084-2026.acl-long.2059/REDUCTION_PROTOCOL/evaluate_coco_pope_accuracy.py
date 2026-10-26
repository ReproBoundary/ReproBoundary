#!/usr/bin/env python3
"""Deterministically reproduce the official COCO-POPE accuracy aggregation."""
import argparse
import json
from pathlib import Path


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pred-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    per_split = {}
    for split in ("adversarial", "popular", "random"):
        truth = read_jsonl(Path(f"experiments/data/POPE/coco/coco_pope_{split}.json"))
        pred = read_jsonl(args.pred_dir / f"coco_{split}_seed55.jsonl")
        if len(truth) != 3000 or len(pred) != 3000:
            raise ValueError(f"{split}: expected exactly 3000 truth and prediction rows")
        truth_ids = [row["question_id"] for row in truth]
        pred_ids = [row["question_id"] for row in pred]
        if truth_ids != pred_ids or len(set(truth_ids)) != 3000:
            raise ValueError(f"{split}: question_id order/coverage mismatch")
        correct = 0
        for gold, generated in zip(truth, pred):
            logits = generated["logits_score"]
            answer = "yes" if logits[0] > logits[1] else "no"
            correct += answer == gold["label"].lower().strip()
        per_split[split] = 100.0 * correct / 3000
    result = {
        "metric": "COCO-POPE macro accuracy",
        "unit": "percent",
        "sample_count": 9000,
        "per_split_accuracy": per_split,
        "value": sum(per_split.values()) / 3.0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
