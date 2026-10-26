#!/usr/bin/env bash
set -euo pipefail

: "${MODEL_PATH:?set MODEL_PATH to the pinned liuhaotian/llava-v1.5-7b snapshot}"
: "${COCO_VAL2014:?set COCO_VAL2014 to the COCO val2014 image directory}"
: "${OUTPUT_DIR:?set OUTPUT_DIR to the retained prediction directory}"

mkdir -p "$OUTPUT_DIR"
for split in adversarial popular random; do
  python3 experiments/eval/model_generate.py \
    --model-path "$MODEL_PATH" \
    --question-file "experiments/data/POPE/coco/coco_pope_${split}.json" \
    --image-folder "$COCO_VAL2014" \
    --answers-file "$OUTPUT_DIR/coco_${split}_seed55.jsonl" \
    --conv-mode vicuna_v1 \
    --seed 55 \
    --return_logits \
    --image_resample \
    --map_constructor sum_scale \
    --heatmap iterative \
    --iterative_search token_mask \
    --iterative_regularization \
    --exit_threshold 0.4 \
    --normalize_mask norm_enhance \
    --enhance_coe 15 \
    --kernel_size 5 \
    --exit_criteria sum_attention
done
