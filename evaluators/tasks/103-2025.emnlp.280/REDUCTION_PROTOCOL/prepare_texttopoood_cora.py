#!/usr/bin/env python3
"""Download and materialize the official TextTopoOOD Cora input only."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath


GOOGLE_DRIVE_FILE_ID = "1cZDOK12AVhT2MnrE6ZeLWJZLlAp81bey"
REQUIRED_FILE = "geometric_data_processed.pt"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_member(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe archive member: {name}")
    return path


def extract_cora(archive: Path, destination: Path) -> list[Path]:
    with zipfile.ZipFile(archive) as handle:
        members = [info for info in handle.infolist() if not info.is_dir()]
        required = [
            info for info in members
            if safe_member(info.filename).parts[-2:] == ("cora", REQUIRED_FILE)
        ]
        if len(required) != 1:
            raise ValueError(
                f"expected one */cora/{REQUIRED_FILE}, found {len(required)}"
            )
        cora_prefix = safe_member(required[0].filename).parent
        selected = []
        for info in members:
            member = safe_member(info.filename)
            if member.parent != cora_prefix:
                continue
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError(f"symlink is forbidden in dataset archive: {info.filename}")
            target = destination / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            with handle.open(info) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            selected.append(target)
    if not (destination / REQUIRED_FILE).is_file():
        raise ValueError(f"archive did not materialize {destination / REQUIRED_FILE}")
    return sorted(selected)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("datasets/cora"))
    parser.add_argument("--cache", type=Path, default=Path(".v4_cache/datasets.zip"))
    parser.add_argument(
        "--receipt", type=Path,
        default=Path("artifacts/texttopoood-cora-input.json"),
    )
    parser.add_argument("--keep-archive", action="store_true")
    args = parser.parse_args()

    try:
        import gdown  # type: ignore
    except ImportError as error:
        raise SystemExit("gdown 5.2.0 is required for the official dataset download") from error

    args.cache.parent.mkdir(parents=True, exist_ok=True)
    archive_downloaded = False
    if not (args.output / REQUIRED_FILE).is_file():
        if not args.cache.is_file():
            downloaded = gdown.download(
                id=GOOGLE_DRIVE_FILE_ID,
                output=str(args.cache),
                quiet=False,
            )
            if not downloaded or not args.cache.is_file():
                raise SystemExit("official TextTopoOOD dataset download failed")
            archive_downloaded = True
        archive_hash = sha256(args.cache)
        files = extract_cora(args.cache, args.output)
    else:
        archive_hash = sha256(args.cache) if args.cache.is_file() else None
        files = sorted(path for path in args.output.iterdir() if path.is_file())

    receipt = {
        "source": "TextTopoOOD official datasets.zip",
        "google_drive_file_id": GOOGLE_DRIVE_FILE_ID,
        "archive_sha256": archive_hash,
        "archive_downloaded_this_run": archive_downloaded,
        "output": str(args.output),
        "files": [
            {"path": str(path), "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in files
        ],
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    if not args.keep_archive and args.cache.is_file():
        args.cache.unlink()
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
