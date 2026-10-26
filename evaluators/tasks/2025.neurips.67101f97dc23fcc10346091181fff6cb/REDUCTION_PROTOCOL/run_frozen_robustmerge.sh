#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
lora_root="${ROBUSTMERGE_LORA_ROOT:?set ROBUSTMERGE_LORA_ROOT to the eight-adapter directory}"
model_root="${LLAVA_MODEL_ROOT:?set LLAVA_MODEL_ROOT to pinned liuhaotian/llava-v1.5-7b}"
datasets_root="${SCIENCEQA_DATASETS_ROOT:?set SCIENCEQA_DATASETS_ROOT to the directory containing ScienceQA/}"
question_file="${MM_MERGEBENCH_SCIENCEQA_TEST:?set MM_MERGEBENCH_SCIENCEQA_TEST to Seen_data/ScienceQA/test.json}"
output_root="$project_root/artifacts/robustmerge_scienceqa"
merged_model="$output_root/llava-lora-robustmerge"

mkdir -p "$output_root"
python3 "$project_root/REDUCTION_PROTOCOL/preflight.py" \
  --lora-root "$lora_root" \
  --model-root "$model_root" \
  --datasets-root "$datasets_root" \
  --question-file "$question_file" \
  > "$output_root/preflight.json"

python3 "$project_root/scripts/merge/merge_lora_weights.py" \
  --model-path "$lora_root" \
  --model-base "$model_root" \
  --save-model-path "$merged_model" \
  --model-name llava-lora

python3 -W ignore -m llava.eval.model_vqa_science \
  --model-path "$merged_model" \
  --model-base "$model_root" \
  --question-file "$question_file" \
  --image-folder "$datasets_root" \
  --answers-file "$output_root/predictions.jsonl" \
  --num-chunks 1 \
  --chunk-idx 0 \
  --temperature 0 \
  --conv-mode vicuna_v1

python3 "$project_root/llava/eval/eval_science_qa.py" \
  --base-dir "$datasets_root/ScienceQA" \
  --split test \
  --result-file "$output_root/predictions.jsonl" \
  --output-file "$output_root/evaluation_details.json" \
  --output-result "$output_root/metrics.json"
