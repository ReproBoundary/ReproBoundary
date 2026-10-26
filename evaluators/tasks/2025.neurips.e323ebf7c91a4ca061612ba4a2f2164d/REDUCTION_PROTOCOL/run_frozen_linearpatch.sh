#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ASSET_DIR="${LINEARPATCH_ASSET_DIR:-${ROOT_DIR}/.frozen_assets}"
ARTIFACT_DIR="${LINEARPATCH_ARTIFACT_DIR:-${ROOT_DIR}/artifacts/linearpatch_qwen7b_arc_easy}"
: "${CUDA_VISIBLE_DEVICES:?scheduler must assign exactly one GPU via CUDA_VISIBLE_DEVICES}"

MODEL_DIR="${ASSET_DIR}/model"
WIKITEXT_TRAIN_PARQUET="${ASSET_DIR}/wikitext/wikitext-2-raw-v1/train-00000-of-00001.parquet"
WIKITEXT_TEST_PARQUET="${ASSET_DIR}/wikitext/wikitext-2-raw-v1/test-00000-of-00001.parquet"
ARC_EASY_TEST_PARQUET="${ASSET_DIR}/ai2_arc/ARC-Easy/test-00000-of-00001.parquet"
TASK_DIR="${ARTIFACT_DIR}/task_config"

mkdir -p "${ARTIFACT_DIR}" "${TASK_DIR}"
python "${ROOT_DIR}/REDUCTION_PROTOCOL/verify_sources.py" \
  "${ASSET_DIR}" "${ARTIFACT_DIR}/SOURCE_HASH_VERIFICATION.json"
python "${ROOT_DIR}/REDUCTION_PROTOCOL/render_task_config.py" \
  "${ROOT_DIR}/REDUCTION_PROTOCOL/arc_easy_frozen.yaml.template" \
  "${ARC_EASY_TEST_PARQUET}" \
  "${TASK_DIR}/arc_easy_frozen.yaml"

export WIKITEXT_REVISION="b08601e04326c79dfdd32d625aee71d232d685c3"
export WIKITEXT_TRAIN_PARQUET
export WIKITEXT_TEST_PARQUET
export HF_DATASETS_OFFLINE=1
export HF_HUB_OFFLINE=1
export TOKENIZERS_PARALLELISM=false

cd "${ROOT_DIR}"
python main_distill.py \
  --model "${MODEL_DIR}" \
  --calib_dataset wikitext2 \
  --total_num_prune 7 \
  --training_seqlen 2048 \
  --train_size 128 \
  --val_size 1 \
  --batch_size 1 \
  --epochs 1 \
  --num_workers 1 \
  --weight_lr 1e-4 \
  --save_prune_dir "${ARTIFACT_DIR}/pruned" \
  --cache_dir "${ARTIFACT_DIR}/cache" \
  --insert_type rotate \
  --distill_type train_free \
  --seed 2 \
  --expected_start_layer 13 \
  --expected_end_layer 20 \
  --eval_batch_size 16 \
  --eval_tasks arc_easy_frozen \
  --eval_task_path "${TASK_DIR}" \
  --metrics_output "${ARTIFACT_DIR}/metrics.json" \
  2>&1 | tee "${ARTIFACT_DIR}/run.log"

test -s "${ARTIFACT_DIR}/metrics.json"
python -c 'import json,sys; p=json.load(open(sys.argv[1])); assert p["selected_start_layer"] == 13; assert p["selected_end_layer"] == 20; assert p["target_metric"]["task"] == "arc_easy_frozen"; assert 0.0 <= p["target_metric"]["value"] <= 100.0' "${ARTIFACT_DIR}/metrics.json"
