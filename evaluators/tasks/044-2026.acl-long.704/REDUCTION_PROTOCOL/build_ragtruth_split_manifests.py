#!/usr/bin/env python3
"""Materialize the five paper-defined RAGTruth QA split assignments."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--response", type=Path, required=True)
    parser.add_argument("--source-info", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()

    responses_by_source: dict[str, list[dict]] = defaultdict(list)
    for row in read_jsonl(args.response):
        responses_by_source[str(row["source_id"])].append(row)

    filtered: list[dict] = []
    for source in read_jsonl(args.source_info):
        if source["task_type"] != "QA":
            continue
        for response in responses_by_source[str(source["source_id"])]:
            if response["model"] == "mistral-7B-instruct" and response["quality"] == "good":
                filtered.append(response)

    ids = [str(row["id"]) for row in filtered]
    if len(ids) != 939 or len(set(ids)) != 939:
        raise ValueError(f"expected 939 unique filtered IDs, got {len(ids)}/{len(set(ids))}")

    train_rows: list[dict] = []
    validation_rows: list[dict] = []
    test_rows: list[dict] = []
    n_test = math.ceil(len(ids) * 0.25)
    for seed in range(42, 47):
        permutation = np.random.RandomState(seed).permutation(len(ids))
        test_indices = permutation[:n_test]
        train_validation_indices = permutation[n_test:]
        train_indices = train_validation_indices[:-100]
        validation_indices = train_validation_indices[-100:]
        for split, indices, destination in (
            ("train", train_indices, train_rows),
            ("validation", validation_indices, validation_rows),
            ("test", test_indices, test_rows),
        ):
            destination.extend(
                {
                    "id": f"seed={seed}/split={split}/response_id={ids[int(index)]}",
                    "response_id": ids[int(index)],
                    "seed": seed,
                    "split": split,
                }
                for index in indices
            )

    outputs = {
        "ragtruth_qa_train_five_splits_seed42_46.jsonl": train_rows,
        "ragtruth_qa_validation_five_splits_seed42_46.jsonl": validation_rows,
        "ragtruth_qa_test_five_splits_seed42_46.jsonl": test_rows,
    }
    summary = {
        "dataset_revision": "c103204b9ce28d6bbad859304bf30de72b8ed8fe",
        "response_sha256": sha256(args.response),
        "source_info_sha256": sha256(args.source_info),
        "filtered_rows": len(ids),
        "filtered_order_sha256": hashlib.sha256(("\n".join(ids) + "\n").encode()).hexdigest(),
        "seeds": list(range(42, 47)),
        "test_size": 0.25,
        "validation_size": 100,
        "files": {},
    }
    for filename, rows in outputs.items():
        path = args.output_dir / filename
        write_jsonl(path, rows)
        summary["files"][filename] = {"rows": len(rows), "sha256": sha256(path)}
    summary_path = args.output_dir / "ragtruth_qa_split_manifest_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
