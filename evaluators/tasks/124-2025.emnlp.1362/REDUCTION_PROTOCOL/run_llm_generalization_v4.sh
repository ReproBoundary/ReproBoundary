#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts logs
python3 REDUCTION_PROTOCOL/prepare_llm_generalization_v4.py 2>&1 | tee logs/prepare.log
cd option_length
export work_dir="$(pwd)"
sentinel=$(mktemp .frozen-v4-start.XXXXXX)
bash scripts/run.sh \
  --model_name Qwen2.5-1.5B --model_path Qwen/Qwen2.5-1.5B \
  --task_name mmlu_rewrite_wrong1_generative --config_name frozen-v4 \
  --batch_size 4 --num_fewshot 5
mapfile -t fresh_results < <(
  find results/Qwen2.5-1.5B/mmlu_rewrite_wrong1_generative \
    -type f -name 'results_*.json' -newer "$sentinel" -print
)
if [[ ${#fresh_results[@]} -ne 1 ]]; then
  printf 'expected exactly one newly generated result, found %d\n' "${#fresh_results[@]}" >&2
  exit 1
fi
result=${fresh_results[0]}
python3 ../REDUCTION_PROTOCOL/extract_llm_generalization_metric.py "$result" ../METRICS.json
