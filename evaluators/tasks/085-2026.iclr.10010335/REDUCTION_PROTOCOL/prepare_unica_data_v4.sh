#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts data_v4
python3 -m pip install --disable-pip-version-check gdown==5.2.0
if [ ! -f artifacts/mmsp-public-release.zip ]; then
  gdown --fuzzy 'https://drive.google.com/file/d/166YnyeFcVYKXNL8MyU2cp6jd9cAnSaIH/view' \
    -O artifacts/mmsp-public-release.zip
fi
python3 REDUCTION_PROTOCOL/prepare_unica_data_v4.py \
  artifacts/mmsp-public-release.zip data_v4 artifacts/mmsp-input-manifest.json
