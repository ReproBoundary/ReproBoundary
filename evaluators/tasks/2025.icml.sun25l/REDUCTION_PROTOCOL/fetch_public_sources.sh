#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ASSET_DIR="${FLATQUANT_ASSET_DIR:-${ROOT_DIR}/.frozen_assets}"
MODEL_DIR="${ASSET_DIR}/model"
WIKITEXT_DIR="${ASSET_DIR}/wikitext"
FHT_DIR="${ROOT_DIR}/third-party/fast-hadamard-transform"
mkdir -p "${MODEL_DIR}" "${WIKITEXT_DIR}"

# HF_ENDPOINT may point to an anonymous mirror. Immutable revisions and
# SHA256 checks below determine artifact identity independently of transport.
huggingface-cli download Qwen/Qwen2.5-7B-Instruct \
  --revision a09a35458c702b33eeacc393d103063234e8bc28 \
  --local-dir "${MODEL_DIR}"
huggingface-cli download Salesforce/wikitext \
  wikitext-2-raw-v1/train-00000-of-00001.parquet \
  wikitext-2-raw-v1/test-00000-of-00001.parquet \
  --repo-type dataset \
  --revision b08601e04326c79dfdd32d625aee71d232d685c3 \
  --local-dir "${WIKITEXT_DIR}"

if [[ ! -d "${FHT_DIR}/.git" ]]; then
  rmdir "${FHT_DIR}" 2>/dev/null || true
  git clone --filter=blob:none --no-checkout \
    https://github.com/Dao-AILab/fast-hadamard-transform.git "${FHT_DIR}"
fi
git -C "${FHT_DIR}" fetch --depth 1 origin d1a56eee9d502e67faacf61b7b947180d66b32a0
git -C "${FHT_DIR}" checkout --detach d1a56eee9d502e67faacf61b7b947180d66b32a0

python "${ROOT_DIR}/REDUCTION_PROTOCOL/verify_sources.py" \
  "${ASSET_DIR}" "${ROOT_DIR}/REDUCTION_PROTOCOL/SOURCE_HASH_VERIFICATION.json"
test "$(git -C "${FHT_DIR}" rev-parse HEAD)" = "d1a56eee9d502e67faacf61b7b947180d66b32a0"
