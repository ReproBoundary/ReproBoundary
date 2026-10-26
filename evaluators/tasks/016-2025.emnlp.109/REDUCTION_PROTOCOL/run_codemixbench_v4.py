#!/usr/bin/env python3
"""Run the frozen one-shot CM-MMLU zh-en evaluation locally."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import urllib.request
from pathlib import Path


DATA_URL = (
    "https://huggingface.co/datasets/CodeMixBench/CodeMixBench/resolve/"
    "b1b6974fd8a5c614d28944021449f5bfad43b70c/MMLU/mmlu_chieng.csv"
)
DATA_SHA256 = "abadeb2c575fc3e14c439702604fd0ebcaa3f878ca6eb64893f8a701706db0eb"
MODEL = "mistralai/Mistral-7B-v0.1"
DEMONSTRATION_SEED = 20260903
DEMONSTRATION_MAP_SHA256 = "26b6ce909a431e8bd87a0beace8249f6f5af9238c58eaef50b8f364bf19af79c"
SYSTEM = (
    "You are a system possessing knowledge in all subjects. You are skilled at selecting "
    "the correct answer based on multiple choice questions. Do not include explanation in your answer."
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def demonstration_mapping(rows: list[dict[str, str]]) -> list[int]:
    rng = random.Random(DEMONSTRATION_SEED)
    eligible = [index for index, row in enumerate(rows) if len(row["sentence"]) <= 600]
    mapping = []
    for target_index in range(len(rows)):
        while True:
            demonstration_index = rng.choice(eligible)
            if demonstration_index != target_index:
                mapping.append(demonstration_index)
                break
    return mapping


def prepare() -> tuple[Path, list[dict[str, str]], list[int]]:
    path = Path("data/mmlu_chieng.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file() or sha256(path) != DATA_SHA256:
        urllib.request.urlretrieve(DATA_URL, path)
    actual = sha256(path)
    if actual != DATA_SHA256:
        raise SystemExit(f"CM-MMLU SHA256 mismatch: {actual}")
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1133 or [row["index"] for row in rows] != [str(i) for i in range(1133)]:
        raise SystemExit("CM-MMLU target must contain canonical indices 0..1132")
    mapping = demonstration_mapping(rows)
    mapping_payload = "".join(
        json.dumps(
            {"target_index": target_index, "demonstration_index": demonstration_index},
            separators=(",", ":"),
        ) + "\n"
        for target_index, demonstration_index in enumerate(mapping)
    )
    mapping_hash = hashlib.sha256(mapping_payload.encode("utf-8")).hexdigest()
    if mapping_hash != DEMONSTRATION_MAP_SHA256:
        raise SystemExit(f"one-shot demonstration map SHA256 mismatch: {mapping_hash}")
    artifact = Path("artifacts/codemixbench-input.json")
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps({
        "path": str(path), "sha256": actual, "rows": len(rows),
        "demonstration_seed": DEMONSTRATION_SEED,
        "demonstration_map_sha256": mapping_hash,
    }, indent=2) + "\n")
    Path("artifacts/codemixbench-one-shot-map.jsonl").write_text(
        mapping_payload, encoding="utf-8"
    )
    return path, rows, mapping


def prompt(rows: list[dict[str, str]], mapping: list[int], index: int) -> str:
    demo = rows[mapping[index]]
    target = rows[index]
    return (
        f"{SYSTEM}\n\n{demo['sentence']}\n\nAnswer: {demo['answer']}\n\n"
        f"{target['sentence']}\n\nAnswer:"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()
    _, rows, mapping = prepare()
    if args.prepare_only:
        return

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.manual_seed(20260903)
    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, torch_dtype=torch.bfloat16, device_map="auto"
    )
    outputs: list[dict[str, object]] = []
    for start in range(0, len(rows), args.batch_size):
        batch_rows = rows[start : start + args.batch_size]
        encoded = tokenizer(
            [prompt(rows, mapping, start + offset) for offset in range(len(batch_rows))],
            return_tensors="pt",
            padding=True,
        ).to(model.device)
        with torch.inference_mode():
            generated = model.generate(
                **encoded,
                do_sample=False,
                max_new_tokens=4,
                pad_token_id=tokenizer.pad_token_id,
            )
        suffix = generated[:, encoded["input_ids"].shape[1] :]
        texts = tokenizer.batch_decode(suffix, skip_special_tokens=True)
        for row, text in zip(batch_rows, texts):
            match = re.search(r"\b([ABCD])\b", text.upper())
            prediction = match.group(1) if match else None
            outputs.append({
                "id": row["id"], "index": int(row["index"]), "raw_output": text,
                "prediction": prediction, "label": row["answer"],
                "correct": prediction == row["answer"],
            })

    Path("PREDICTIONS.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in outputs), encoding="utf-8"
    )
    value = 100.0 * sum(bool(row["correct"]) for row in outputs) / len(outputs)
    Path("METRICS.json").write_text(json.dumps({
        "metric": "accuracy", "unit": "percent", "value": value,
        "correct": sum(bool(row["correct"]) for row in outputs), "total": len(outputs),
        "model": MODEL, "shots": 1, "decoding": "greedy",
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
