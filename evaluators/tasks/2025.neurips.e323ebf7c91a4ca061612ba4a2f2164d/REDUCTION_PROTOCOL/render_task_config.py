#!/usr/bin/env python3
"""Render the frozen ARC-Easy task with one explicit local parquet path."""

from pathlib import Path
import sys


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: render_task_config.py TEMPLATE PARQUET OUTPUT")
    template = Path(sys.argv[1]).read_text(encoding="utf-8")
    parquet = str(Path(sys.argv[2]).resolve())
    if '"' in parquet or "\n" in parquet:
        raise SystemExit("unsupported parquet path")
    rendered = template.replace("__ARC_EASY_TEST_PARQUET__", parquet)
    if "__ARC_EASY_TEST_PARQUET__" in rendered:
        raise SystemExit("task template placeholder was not replaced")
    output = Path(sys.argv[3])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
