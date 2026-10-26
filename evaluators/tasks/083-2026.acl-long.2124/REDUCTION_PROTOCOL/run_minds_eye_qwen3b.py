#!/usr/bin/env python3
"""Run all Mind's Eye mental-composition items with the released evaluator."""

import csv
import importlib.util
import json
import sys
from pathlib import Path


root = Path.cwd()
source = root / "evaluation/evaluation_pipeline.py"
patched = root / "evaluation/evaluation_pipeline_v4.py"
text = source.read_text(encoding="utf-8")
needle = "            break\n"
if text.count(needle) != 1:
    raise SystemExit("expected exactly one one-item debug break in evaluation_pipeline.py")
patched.write_text(text.replace(needle, "", 1), encoding="utf-8")
sys.path[:0] = [str(root), str(root / "evaluation")]
spec = importlib.util.spec_from_file_location("evaluation_pipeline_v4", patched)
if spec is None or spec.loader is None:
    raise SystemExit("could not load patched evaluation module")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.JSON_LIST = {"mental_composition": module.JSON_LIST["mental_composition"]}
model, processor = module.load_model_and_processor("qwen3b", module.DEVICE)
scores = []
try:
    for repetition in range(3):
        module.evaluate_model("qwen3b", model, processor, repetition, save_results=True)
        path = root / f"model_evaluation/qwen3b/step_{repetition + 1}/qwen3b_phi3_judged_all_tasks.csv"
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) != 100:
            raise SystemExit(f"repetition {repetition + 1}: expected 100 rows, found {len(rows)}")
        scores.append(sum(float(row["judge_score"]) for row in rows) / len(rows) * 100.0)
finally:
    module.unload_model_and_clear_cache(model, processor)
output = {"metric": "accuracy", "unit": "percent", "repetitions": scores, "value": sum(scores) / len(scores)}
destination = root / "artifacts/minds-eye-accuracy.json"
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

