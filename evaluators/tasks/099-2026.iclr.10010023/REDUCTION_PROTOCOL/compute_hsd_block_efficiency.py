#!/usr/bin/env python3
"""Extract HSD block efficiency using the repository's published aggregation."""
import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--counts", type=Path, required=True)
    parser.add_argument("--gamma", type=int, default=10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    counts = json.loads(args.counts.read_text())
    if len(counts["draft_eval"]) != 1319 or len(counts["sample_length"]) != 1319:
        raise ValueError("expected exactly 1319 GSM8K test result records")
    accepted_lengths = []
    for drafts, lengths in zip(counts["draft_eval"], counts["sample_length"]):
        if len(drafts) != len(lengths):
            raise ValueError("draft_eval/sample_length shape mismatch")
        accepted_lengths.extend(length for draft, length in zip(drafts, lengths) if draft == args.gamma)
    if not accepted_lengths:
        raise ValueError("no full-gamma verification blocks found")
    result = {
        "metric": "Block Efficiency",
        "unit": "tokens/step",
        "gamma": args.gamma,
        "sample_count": 1319,
        "eligible_blocks": len(accepted_lengths),
        "value": sum(accepted_lengths) / len(accepted_lengths),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
