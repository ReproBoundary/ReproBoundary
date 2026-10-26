#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python -m pip install -r "${ROOT_DIR}/REDUCTION_PROTOCOL/requirements-frozen.txt"
python -m pip install --no-build-isolation \
  "${ROOT_DIR}/third-party/fast-hadamard-transform"

# Do not run `pip install .` in the FlatQuant root. That setup.py builds
# deployment-only CUTLASS kernels and omits H100's sm90 from its arch list;
# the selected fake-quantized paper-table path imports Python from ROOT_DIR.
