#!/usr/bin/env python3
"""Materialize the preregistered NuminaMath rows without changing their order."""

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_MANIFEST_SHA256 = "89660340c007590d26dd3f259fc75f2f4331b42fc30842f54f3c9f1890290dc8"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if hashlib.sha256(args.manifest.read_bytes()).hexdigest() != EXPECTED_MANIFEST_SHA256:
        raise SystemExit("selected-ID manifest SHA256 mismatch")
    source = [json.loads(line) for line in args.source.read_text().splitlines() if line.strip()]
    selections = [json.loads(line) for line in args.manifest.read_text().splitlines() if line.strip()]
    if len(selections) != 500:
        raise SystemExit("selected-ID manifest must contain exactly 500 rows")
    rows = []
    for selected in selections:
        index = selected.get("source_row")
        if not isinstance(index, int) or not 0 <= index < len(source):
            raise SystemExit(f"invalid source_row: {index!r}")
        rows.append(source[index])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


if __name__ == "__main__":
    main()
