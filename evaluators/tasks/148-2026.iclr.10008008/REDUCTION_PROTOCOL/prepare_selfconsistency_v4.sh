#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts/selfconsistency-public code/datasets
python3 -m pip install --disable-pip-version-check gdown==5.2.0
if ! find artifacts/selfconsistency-public -type f -print -quit | grep -q .; then
  gdown --folder 'https://drive.google.com/drive/folders/1RaOKbWABerHfea_sJZGIbXSy0FcOzK0O' \
    -O artifacts/selfconsistency-public
fi
python3 REDUCTION_PROTOCOL/materialize_ba2motifs_v4.py \
  artifacts/selfconsistency-public code/datasets/ba_2motifs \
  artifacts/ba2motifs-input-manifest.json
