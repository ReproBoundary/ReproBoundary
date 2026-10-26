#!/usr/bin/env python3
"""Convert the audited EgoSchema TSV into the required frozen JSONL format."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    rows = []
    for line in args.source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ordinal, question_id = line.split("\t", 1)
        rows.append({"id": question_id, "ordinal": int(ordinal), "stratum": "Subset/test"})

    assert len(rows) == 500
    assert [row["ordinal"] for row in rows] == list(range(500))
    assert len({row["id"] for row in rows}) == 500

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
