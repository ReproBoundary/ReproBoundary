#!/usr/bin/env python3
"""Materialize CIFAR-10 and remove the repository's machine-specific data root."""

import hashlib
import json
from pathlib import Path

from torchvision.datasets import CIFAR10


config = Path("utils/conf.py")
original = "return '/common_datasets2/CV/'"
replacement = "return './data/'"
source = config.read_text(encoding="utf-8")
if original in source:
    source = source.replace(original, replacement, 1)
    config.write_text(source, encoding="utf-8")
elif replacement not in source:
    raise SystemExit("IDER dataset root is neither the pinned path nor the frozen local path")

root = Path("data/CIFAR10")
train = CIFAR10(root, train=True, download=True)
test = CIFAR10(root, train=False, download=True)
if len(train) != 50000 or len(test) != 10000:
    raise SystemExit(f"unexpected CIFAR-10 counts: train={len(train)}, test={len(test)}")
artifact = Path("artifacts/cifar10-input.json")
artifact.parent.mkdir(parents=True, exist_ok=True)
artifact.write_text(json.dumps({
    "train_images": len(train),
    "test_images": len(test),
    "repository_dataset_root": "./data/",
    "patched_config": str(config),
    "patched_config_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
}, indent=2) + "\n")
