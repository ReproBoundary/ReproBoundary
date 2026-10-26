#!/usr/bin/env python3
"""Materialize the exact frozen M2PO training subset and AIME-2024 evaluation set."""

import argparse
import hashlib
import json
from pathlib import Path

from datasets import Dataset, concatenate_datasets, load_dataset


TRAIN_DATASET = "agentica-org/DeepScaleR-Preview-Dataset"
TRAIN_REVISION = "b6ae8c60f5c1f2b594e2140b91c49c9ad0949e29"
AIME_DATASET = "HuggingFaceH4/aime_2024"
AIME_REVISION = "2fe88a2f1091d5048c0f36abc874fb997b3dd99a"
SEED = 42
TRAIN_COUNT = 256
AIME_COUNT = 30


def prompt(problem: str) -> str:
    return (
        f"Please solve the following math problem: {problem}. The assistant first thinks "
        "about the reasoning process step by step and then provides the user with the answer. "
        "Return the final answer in \\boxed{} tags, for example \\boxed{1}. Let's solve this "
        "step by step. "
    )


def identity(row: dict) -> tuple[str, str]:
    canonical = json.dumps(
        {key: row[key] for key in ("problem", "answer", "solution")},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"deepscaler-train:{row['_source_index']:08d}:{digest[:16]}", digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).with_name("deepscaler_train_256_seed42.jsonl"),
    )
    args = parser.parse_args()

    expected = [json.loads(line) for line in args.manifest.read_text(encoding="utf-8").splitlines() if line]
    if len(expected) != TRAIN_COUNT or len({row["id"] for row in expected}) != TRAIN_COUNT:
        raise RuntimeError("frozen training manifest must contain 256 unique IDs")

    train = load_dataset(TRAIN_DATASET, revision=TRAIN_REVISION, split="train")
    train = train.add_column("_source_index", list(range(len(train))))
    train = train.shuffle(seed=SEED).select(range(TRAIN_COUNT))
    actual = []
    processed_train = []
    for index, row in enumerate(train):
        row_id, digest = identity(row)
        actual.append(
            {
                "content_sha256": digest,
                "id": row_id,
                "source_index": row["_source_index"],
                "stratum": "train",
            }
        )
        processed_train.append(
            {
                "data_source": "dapo_math",
                "prompt": [{"role": "user", "content": prompt(row["problem"])}],
                "ability": "math",
                "reward_model": {"style": "rule", "ground_truth": row["answer"]},
                "extra_info": {
                    "split": "train",
                    "index": index,
                    "source_index": row["_source_index"],
                    "frozen_id": row_id,
                },
            }
        )
    if actual != expected:
        raise RuntimeError("downloaded DeepScaleR revision does not reproduce the frozen manifest")

    aime = load_dataset(AIME_DATASET, revision=AIME_REVISION, split="train")
    if len(aime) != AIME_COUNT:
        raise RuntimeError(f"expected {AIME_COUNT} AIME-2024 rows, found {len(aime)}")
    processed_aime = Dataset.from_list(
        [
            {
                "data_source": AIME_DATASET + "_x4",
                "prompt": [{"role": "user", "content": prompt(row["problem"])}],
                "ability": "math",
                "reward_model": {"style": "rule", "ground_truth": row["answer"]},
                "extra_info": {"split": "train", "index": index},
            }
            for index, row in enumerate(aime)
        ]
    )
    processed_aime = concatenate_datasets([processed_aime] * 4)

    train_path = args.output_root / "deepscaler_preview" / "train_256_seed42.parquet"
    aime_path = args.output_root / "aime2024x4" / "test.parquet"
    train_path.parent.mkdir(parents=True, exist_ok=True)
    aime_path.parent.mkdir(parents=True, exist_ok=True)
    Dataset.from_list(processed_train).to_parquet(str(train_path))
    processed_aime.to_parquet(str(aime_path))
    print(
        json.dumps(
            {
                "train_rows": len(processed_train),
                "aime_questions": AIME_COUNT,
                "aime_rows_after_x4": len(processed_aime),
                "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
                "train_path": str(train_path),
                "aime_path": str(aime_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
