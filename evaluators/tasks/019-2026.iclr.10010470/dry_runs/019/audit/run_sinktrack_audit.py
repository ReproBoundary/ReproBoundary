#!/usr/bin/env python3
"""Auditable SinkTrack runner preserving the official Qwen2.5-VL method."""

import argparse
import copy
import hashlib
import json
import os
import random
import resource
import time
from pathlib import Path

import numpy as np
import torch
from qwen_vl_utils import process_vision_info
from transformers import AutoProcessor

from sinktrack import Qwen2_5_VLForConditionalGenerationWithInjection


PROMPT_TEMPLATE = "Question: {}\n"
COT_PROMPT = "Let's think step by step!"
OUTPUT_FORMAT = """
Output Format:
You must first give your reasoning step, then give your final answer using the **EXACT format** below:
**Answer: [Your Final Option]**

For example:
[Here is your reasoning text].
**Answer: B**"""


def fix_seeds(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--dataset-file", type=Path, required=True)
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument("--output-file", type=Path, required=True)
    parser.add_argument("--metadata-file", type=Path, required=True)
    parser.add_argument("--seed", type=int, choices=(323, 500, 900), required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--max-new-tokens", type=int, default=2048)
    parser.add_argument("--injection-layer", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    fix_seeds(args.seed)

    with args.dataset_file.open(encoding="utf-8") as handle:
        dataset = [json.loads(line) for line in handle if line.strip()]
    if args.limit is not None:
        dataset = dataset[: args.limit]
    if len(dataset) != args.expected_count:
        raise RuntimeError(f"expected {args.expected_count} inputs, got {len(dataset)}")
    input_ids = [str(row["id"]) for row in dataset]
    if len(set(input_ids)) != len(input_ids):
        raise RuntimeError("input IDs are not unique")

    model = Qwen2_5_VLForConditionalGenerationWithInjection.from_pretrained(
        str(args.model_path),
        torch_dtype="auto",
        device_map="cuda:0",
        attn_implementation="eager",
    )
    model.eval()
    processor = AutoProcessor.from_pretrained(str(args.model_path), use_fast=False)
    torch.cuda.reset_peak_memory_stats()

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    generated_token_counts = []
    output_ids = []
    with args.output_file.open("w", encoding="utf-8") as output:
        for row in dataset:
            prompt = PROMPT_TEMPLATE.format(row["question"])
            for option, choice in zip("ABCDEF", row["choices"]):
                prompt += f"{option}. {choice}\n"
            prompt += "\n" + COT_PROMPT + "\n" + OUTPUT_FORMAT

            image_path = (args.image_root / row["image"]).resolve()
            if not image_path.is_file():
                raise FileNotFoundError(f"image for {row['id']} not found: {image_path}")
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": str(image_path)},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]
            text = processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            image_inputs, video_inputs = process_vision_info(messages)
            inputs = processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            ).to("cuda")
            with torch.inference_mode():
                generated_ids = model.generate(
                    **inputs,
                    max_new_tokens=args.max_new_tokens,
                    do_sample=True,
                    injection_layer_idx=args.injection_layer,
                )
            trimmed = generated_ids[:, inputs.input_ids.shape[1] :]
            prediction = processor.batch_decode(
                trimmed,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )[0]

            result = copy.deepcopy(row)
            result["pred"] = prediction
            output.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
            output.flush()
            output_ids.append(str(row["id"]))
            generated_token_counts.append(int(trimmed.shape[1]))

    elapsed = time.monotonic() - started
    if output_ids != input_ids or len(output_ids) != args.expected_count:
        raise RuntimeError("output IDs/count do not exactly match frozen inputs")
    metadata = {
        "method": "SinkTrack",
        "model_path": str(args.model_path.resolve()),
        "dataset_file": str(args.dataset_file.resolve()),
        "dataset_sha256": sha256_file(args.dataset_file),
        "seed": args.seed,
        "injection_layer": args.injection_layer,
        "max_new_tokens": args.max_new_tokens,
        "input_count": len(input_ids),
        "output_count": len(output_ids),
        "output_sha256": sha256_file(args.output_file),
        "elapsed_seconds": elapsed,
        "seconds_per_sample": elapsed / len(output_ids),
        "generated_tokens_total": sum(generated_token_counts),
        "generated_tokens_per_sample": generated_token_counts,
        "gpu_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
        "gpu_peak_reserved_bytes": torch.cuda.max_memory_reserved(),
        "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "transformers_version": __import__("transformers").__version__,
        "torch_version": torch.__version__,
    }
    args.metadata_file.parent.mkdir(parents=True, exist_ok=True)
    args.metadata_file.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
