#!/usr/bin/env python3
"""Materialize the frozen EgoSchema subset from five revision-bound archives.

The caller supplies the frozen binding JSON, not ad-hoc URLs. Only MP4 files
whose stem occurs in the frozen manifest are retained. An archive is removed
only after its SHA256 and all retained files have been verified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tarfile
import urllib.request
import zipfile
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def wanted_ids(path: Path) -> set[str]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = {row["id"] for row in rows}
    if len(rows) != 500 or len(ids) != 500:
        raise RuntimeError("the frozen manifest must contain 500 unique IDs")
    return ids


def safe_name(member_name: str) -> str | None:
    path = Path(member_name)
    if path.is_absolute() or ".." in path.parts or path.suffix.lower() != ".mp4":
        return None
    return path.name


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bindings", type=Path, required=True)
    args = parser.parse_args()
    binding = json.loads(args.bindings.read_text(encoding="utf-8"))
    if binding.get("revision") != "58350524ea7eb29c47000121f4f4b65eb6b4acb9":
        raise RuntimeError("unexpected EgoSchema dataset revision")
    archives = binding.get("archives", [])
    if len(archives) != 5:
        raise RuntimeError("exactly five bound EgoSchema archives are required")

    ids = wanted_ids(args.manifest)
    args.output.mkdir(parents=True, exist_ok=True)
    staging = args.output / ".staging"
    staging.mkdir(exist_ok=True)
    archive_records = []

    for index, archive_binding in enumerate(archives, 1):
        url = archive_binding["url"]
        archive = staging / f"archive-{index}"
        with urllib.request.urlopen(url) as response, archive.open("wb") as target:
            shutil.copyfileobj(response, target)
        archive_hash = sha256(archive)
        if archive_hash != archive_binding["sha256"]:
            raise RuntimeError(
                f"archive SHA256 mismatch for {archive_binding['filename']}: "
                f"expected {archive_binding['sha256']}, got {archive_hash}"
            )
        retained = []
        if zipfile.is_zipfile(archive):
            with zipfile.ZipFile(archive) as source:
                for member in source.infolist():
                    name = safe_name(member.filename)
                    if name is None or Path(name).stem not in ids:
                        continue
                    destination = args.output / name
                    with source.open(member) as src, destination.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
                    retained.append({"id": destination.stem, "sha256": sha256(destination)})
        elif tarfile.is_tarfile(archive):
            with tarfile.open(archive) as source:
                for member in source.getmembers():
                    name = safe_name(member.name)
                    if name is None or Path(name).stem not in ids or not member.isfile():
                        continue
                    destination = args.output / name
                    extracted = source.extractfile(member)
                    if extracted is None:
                        raise RuntimeError(f"cannot extract {member.name}")
                    with extracted, destination.open("wb") as dst:
                        shutil.copyfileobj(extracted, dst)
                    retained.append({"id": destination.stem, "sha256": sha256(destination)})
        else:
            raise RuntimeError(f"unsupported archive format: {url}")
        archive.unlink()
        archive_records.append(
            {
                "filename": archive_binding["filename"],
                "url": url,
                "revision": binding["revision"],
                "sha256": archive_hash,
                "retained": retained,
            }
        )

    found = {path.stem for path in args.output.glob("*.mp4")}
    if found != ids:
        raise RuntimeError(f"video set mismatch: missing={sorted(ids-found)[:10]} extra={sorted(found-ids)[:10]}")
    record = {
        "schema_version": "1.0",
        "manifest_sha256": sha256(args.manifest),
        "video_count": 500,
        "archives": archive_records,
        "videos": [{"id": path.stem, "sha256": sha256(path)} for path in sorted(args.output.glob("*.mp4"))],
    }
    (args.output.parent / "materialization.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
