#!/usr/bin/env python3
"""Create the frozen one-GPU DOPRI5 FID-50K entrypoint."""

from pathlib import Path


source = Path("CIFAR/compute_fid_multi_gpu.py")
destination = Path("artifacts/compute_fid_dopri5_v4.py")
text = source.read_text(encoding="utf-8")
replacements = {
    "integration_method='euler' # euler or dopri5": (
        "integration_method='dopri5' # frozen v4 solver"
    ),
    "path_pattern='./results/*/*400000.pt'": (
        "path_pattern='./results/AlignFlow_v4/AlignFlow_cifar10_weights_step_100000.pt'"
    ),
    "result_csv_path='./fid_result_1000.csv'": (
        "result_csv_path='./artifacts/alignflow-cifar10-fid50k.csv'"
    ),
    "fid_device_id=0": "fid_device_id=0\ntorch.manual_seed(0)\ntorch.cuda.manual_seed_all(0)",
}
for old, new in replacements.items():
    if text.count(old) != 1:
        raise SystemExit(f"expected exactly one occurrence of {old!r}")
    text = text.replace(old, new)
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(text, encoding="utf-8")
