#!/usr/bin/env python3
"""Extract the public MMSP bundle and enforce the four-CPU protocol cap."""

import hashlib
import json
import shutil
import sys
from pathlib import Path


archive, destination, manifest = map(Path, sys.argv[1:4])
if not archive.is_file():
    raise SystemExit(f"missing MMSP archive: {archive}")
destination.mkdir(parents=True, exist_ok=True)
if not any(destination.iterdir()):
    shutil.unpack_archive(str(archive), str(destination))

utils = Path("utils.py")
text = utils.read_text(encoding="utf-8")
if "torch.set_num_threads(16)" in text:
    text = text.replace("torch.set_num_threads(16)", "torch.set_num_threads(4)", 1)
    utils.write_text(text, encoding="utf-8")
if "torch.set_num_threads(4)" not in text:
    raise SystemExit("could not enforce the frozen four-CPU limit")

files = sorted(path for path in destination.rglob("*") if path.is_file())
if not files:
    raise SystemExit("MMSP archive extracted no files")
payload = {
    "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    "file_count": len(files),
    "top_level_entries": sorted({path.relative_to(destination).parts[0] for path in files}),
    "plants": 10,
    "cpu_threads": 4,
}
manifest.parent.mkdir(parents=True, exist_ok=True)
manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2))
