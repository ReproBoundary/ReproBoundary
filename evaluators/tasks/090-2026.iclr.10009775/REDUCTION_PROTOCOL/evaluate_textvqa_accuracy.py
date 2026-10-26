#!/usr/bin/env python3
"""Machine-readable equivalent of src/evaluate/benchmarks/metrics/eval_textvqa.py."""
import argparse
import json
import string
from pathlib import Path


def normalize(text: str) -> str:
    text = text.lower().translate(str.maketrans("", "", string.punctuation))
    return " ".join(text.strip().split())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = json.loads(args.predictions.read_text())
    if len(rows) != 5000 or len({str(row["index"]) for row in rows}) != 5000:
        raise ValueError("expected exactly 5000 unique TextVQA validation question IDs")
    correct = sum(
        any(normalize(row["predicted"]) == normalize(answer) for answer in row["GT"])
        for row in rows
    )
    result = {
        "metric": "TextVQA exact-match-any-answer accuracy",
        "unit": "percent",
        "sample_count": 5000,
        "correct": correct,
        "value": 100.0 * correct / 5000,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
