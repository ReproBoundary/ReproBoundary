#!/usr/bin/env python3
"""Verify immutable large-file hashes used by the FlatQuant protocol."""

from hashlib import sha256
from pathlib import Path
import json
import sys


EXPECTED = {
    "model/model-00001-of-00004.safetensors": "a1333e6293854747c481288ea83b348226af178dd565c49b6f9495ba1966aba7",
    "model/model-00002-of-00004.safetensors": "f5d25a2772cb825164a2a2c0fb6d51a87e282abf21e4dd75bc5cfb3cd0ea6185",
    "model/model-00003-of-00004.safetensors": "8efdec4c1bc12317ae1a38dc42b595ce777738a64deea3fcb8a0a91381bcdfd5",
    "model/model-00004-of-00004.safetensors": "1a72d403cdf0c1ec3cb7f289f17b394a01e64394c2e9b3c0f94dbce3faf879bd",
    "wikitext/wikitext-2-raw-v1/train-00000-of-00001.parquet": "e83889baabc497075506f91975be5fac0d45c5290b6b20582c8cd1e853d0c9f7",
    "wikitext/wikitext-2-raw-v1/test-00000-of-00001.parquet": "5f1bea067869d04849c0f975a2b29c4ff47d867f484f5010ea5e861eab246d91",
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
        checks.append({"path": relative, "expected_sha256": expected, "actual_sha256": actual})
        if actual != expected:
            raise SystemExit(f"SHA256 mismatch: {relative}")
    output = Path(sys.argv[2])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"checks": checks}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
