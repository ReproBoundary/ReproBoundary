#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ASSET_DIR="${LINEARPATCH_ASSET_DIR:-${ROOT_DIR}/.frozen_assets}"
mkdir -p "${ASSET_DIR}/model" "${ASSET_DIR}/wikitext" "${ASSET_DIR}/ai2_arc"

# HF_ENDPOINT may be set to an anonymous mirror. Immutable revisions and
# SHA256 checks make the transport endpoint irrelevant to artifact identity.
huggingface-cli download deepseek-ai/DeepSeek-R1-Distill-Qwen-7B \
  --revision 916b56a44061fd5cd7d6a8fb632557ed4f724f60 \
  --local-dir "${ASSET_DIR}/model"
huggingface-cli download Salesforce/wikitext \
  wikitext-2-raw-v1/train-00000-of-00001.parquet \
  wikitext-2-raw-v1/test-00000-of-00001.parquet \
  --repo-type dataset \
  --revision b08601e04326c79dfdd32d625aee71d232d685c3 \
  --local-dir "${ASSET_DIR}/wikitext"
huggingface-cli download allenai/ai2_arc \
  ARC-Easy/test-00000-of-00001.parquet \
  --repo-type dataset \
  --revision 210d026faf9955653af8916fad021475a3f00453 \
  --local-dir "${ASSET_DIR}/ai2_arc"

python "${ROOT_DIR}/REDUCTION_PROTOCOL/verify_sources.py" \
  "${ASSET_DIR}" "${ASSET_DIR}/SOURCE_HASH_VERIFICATION.json"
