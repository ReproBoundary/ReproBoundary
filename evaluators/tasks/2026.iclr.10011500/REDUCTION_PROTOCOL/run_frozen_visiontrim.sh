#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
data_root="${SCIENCEQA_ROOT:-$project_root/data/scienceqa}"
model_root="${LLAVA_MODEL_ROOT:-$project_root/checkpoints/llava-v1.5-7b}"
output_root="$project_root/artifacts/visiontrim_sqa_64"

test -f "$data_root/pid_splits.json"
test -f "$data_root/problems.json"
test -d "$data_root/images/test"
test -f "$model_root/config.json"
mkdir -p "$output_root"

python3 scripts/convert_sqa_to_llava.py convert_to_llava \
  --base_dir "$data_root" \
  --split test \
  --prompt_format CQM-A

python3 -W ignore -m llava.eval.model_vqa_science \
  --model-path "$model_root" \
  --question-file "$data_root/llava_test_CQM-A.json" \
  --image-folder "$data_root/images/test" \
  --answers-file "$output_root/predictions.jsonl" \
  --single-pred-prompt \
  --temperature 0 \
  --method visiontrim \
  --DVTS_token_num 48 \
  --TGVC_token_num 16 \
  --dataset-name sqa \
  --conv-mode vicuna_v1

python3 llava/eval/eval_science_qa.py \
  --base-dir "$data_root" \
  --split test \
  --result-file "$output_root/predictions.jsonl" \
  --output-file "$output_root/evaluation_details.json" \
  --output-result "$output_root/metrics.json"
