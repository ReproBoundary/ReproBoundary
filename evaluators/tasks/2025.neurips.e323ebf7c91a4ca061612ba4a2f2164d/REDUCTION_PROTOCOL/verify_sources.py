#!/usr/bin/env python3
"""Verify the immutable large-file hashes used by the frozen protocol."""

from hashlib import sha256
from pathlib import Path
import json
import sys


EXPECTED = {
    "model/model-00001-of-000002.safetensors": "8b27be8d43b81d0cd19b3113ef88caf1a61c2fc602de77e3cce97aedcec184b4",
    "model/model-00002-of-000002.safetensors": "1780a9502f56f592cb4d6262c8c76ca8ad36a86b0257e052c672d87f49707e80",
    "wikitext/wikitext-2-raw-v1/train-00000-of-00001.parquet": "e83889baabc497075506f91975be5fac0d45c5290b6b20582c8cd1e853d0c9f7",
    "wikitext/wikitext-2-raw-v1/test-00000-of-00001.parquet": "5f1bea067869d04849c0f975a2b29c4ff47d867f484f5010ea5e861eab246d91",
    "ai2_arc/ARC-Easy/test-00000-of-00001.parquet": "4160597d618ae851c7eb04e281574f3f654776216ac6b6641588d64527b47177",
}


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: verify_sources.py ASSET_ROOT OUTPUT_JSON")
    root = Path(sys.argv[1])
    checks = []
    for relative, expected in EXPECTED.items():
        path = root / relative
        actual = digest(path)
        checks.append(
            {"path": relative, "expected_sha256": expected, "actual_sha256": actual}
        )
        if actual != expected:
            raise SystemExit(f"SHA256 mismatch: {relative}")
    output = Path(sys.argv[2])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"checks": checks}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
