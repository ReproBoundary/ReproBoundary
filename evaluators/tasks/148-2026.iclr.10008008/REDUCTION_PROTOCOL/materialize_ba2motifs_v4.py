#!/usr/bin/env python3
"""Materialize the released BA-2MOTIFS directory and record its provenance."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def unpack_archives(root: Path) -> None:
    for archive in sorted(root.rglob("*")):
        if not archive.is_file() or archive.suffix.lower() not in {
            ".zip", ".tar", ".gz", ".tgz",
        }:
            continue
        destination = archive.parent / f"{archive.name}.unpacked"
        destination.mkdir(exist_ok=True)
        try:
            shutil.unpack_archive(str(archive), str(destination))
        except (shutil.ReadError, ValueError):
            continue


def locate_dataset(root: Path) -> Path:
    candidates = []
    for raw_file in root.rglob("ba_2motifs.pkl"):
        if raw_file.parent.name != "raw":
            continue
        dataset = raw_file.parent.parent
        if (dataset / "processed/data.pt").is_file():
            candidates.append(dataset)
    if len(candidates) != 1:
        raise SystemExit(
            "expected exactly one BA-2MOTIFS release containing raw/ba_2motifs.pkl "
            f"and processed/data.pt, found {len(candidates)}"
        )
    return candidates[0]


def main() -> None:
    source, destination, manifest = map(Path, sys.argv[1:4])
    if not source.is_dir():
        raise SystemExit(f"missing downloaded dataset directory: {source}")
    unpack_archives(source)
    dataset = locate_dataset(source)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(dataset, destination)
    files = sorted(path for path in destination.rglob("*") if path.is_file())
    payload = {
        "dataset": "BA-2MOTIFS",
        "source": "SelfConsistencyXGNN public Google Drive release",
        "split_seed": 2025,
        "expected_graphs": 1000,
        "expected_test_graphs": 100,
        "files": {
            str(path.relative_to(destination)): digest(path)
            for path in files
        },
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
