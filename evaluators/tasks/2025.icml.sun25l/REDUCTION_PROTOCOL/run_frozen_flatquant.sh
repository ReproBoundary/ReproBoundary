#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ASSET_DIR="${FLATQUANT_ASSET_DIR:-${ROOT_DIR}/.frozen_assets}"
ARTIFACT_DIR="${FLATQUANT_ARTIFACT_DIR:-${ROOT_DIR}/artifacts/qwen25_7b_w4a4kv4_wikitext2}"
: "${CUDA_VISIBLE_DEVICES:?scheduler must assign exactly one GPU via CUDA_VISIBLE_DEVICES}"

MODEL_DIR="${ASSET_DIR}/model"
TRAIN_PARQUET="${ASSET_DIR}/wikitext/wikitext-2-raw-v1/train-00000-of-00001.parquet"
TEST_PARQUET="${ASSET_DIR}/wikitext/wikitext-2-raw-v1/test-00000-of-00001.parquet"
mkdir -p "${ARTIFACT_DIR}"

python "${ROOT_DIR}/REDUCTION_PROTOCOL/verify_sources.py" \
  "${ASSET_DIR}" "${ARTIFACT_DIR}/SOURCE_HASH_VERIFICATION.json"

export HF_DATASETS_OFFLINE=1
export HF_HUB_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export PYTHONPATH="${ROOT_DIR}:${PYTHONPATH:-}"

cd "${ROOT_DIR}"
python main.py \
  --model "${MODEL_DIR}" \
  --wikitext_train_file "${TRAIN_PARQUET}" \
  --wikitext_test_file "${TEST_PARQUET}" \
  --cali_dataset wikitext2 \
  --seed 0 \
  --nsamples 128 \
  --cali_bsz 4 \
  --epochs 15 \
  --flat_lr 5e-3 \
  --w_bits 4 \
  --a_bits 4 \
  --k_bits 4 --k_asym --k_groupsize 128 \
  --v_bits 4 --v_asym --v_groupsize 128 \
  --lwc --lac --cali_trans --add_diag \
  --deactive_amp --direct_inv \
  --save_matrix \
  --output_dir "${ARTIFACT_DIR}/outputs" \
  --exp_name frozen_table8 \
  --eval_datasets wikitext2 \
  --metrics_output "${ARTIFACT_DIR}/metrics.json" \
  2>&1 | tee "${ARTIFACT_DIR}/run.log"

test -s "${ARTIFACT_DIR}/metrics.json"
python -c 'import json,math,sys; p=json.load(open(sys.argv[1])); c=p["configuration"]; assert c["w_bits"]==c["a_bits"]==c["k_bits"]==c["v_bits"]==4; assert c["epochs"]==15 and c["calibration_samples"]==128 and c["fp32_calibration"] and c["direct_inverse"]; assert p["calibration_artifact"]["exists"] and p["matrix_artifact"]["exists"]; assert list(p["perplexity"])==["wikitext2"]; assert math.isfinite(p["perplexity"]["wikitext2"]) and p["perplexity"]["wikitext2"]>0' "${ARTIFACT_DIR}/metrics.json"
