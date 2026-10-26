#!/usr/bin/env python3
"""Evaluate the newly trained GPT-Tiny CABLE checkpoint at length 2,048."""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import torch


sys.path.insert(0, "src")
from data_loader import DataLoaderLite  # noqa: E402
from model_gpt import Model  # noqa: E402


@dataclass
class ModelConfig:
    pos_method: str = "cable"
    use_dape: bool = False
    block_size: int = 1024
    vocab_size: int = 50304
    n_layer: int = 6
    n_head: int = 8
    n_embd: int = 512


def main() -> None:
    checkpoint = Path(
        "artifacts/cable-checkpoints/"
        "tiny_cable_wikitext-103_1_131072_16_1024/model_914.pt"
    )
    if not checkpoint.is_file():
        raise SystemExit(f"missing newly trained checkpoint: {checkpoint}")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = Model(ModelConfig())
    state = torch.load(checkpoint, map_location="cpu")
    for key in [name for name in state if "cached_" in name]:
        del state[key]
    model.load_state_dict(state)
    model.eval().to(device)

    sequence_length = 2048
    blocks = 1000
    loader = DataLoaderLite(
        B=1, T=sequence_length, process_rank=0, num_processes=1,
        split="val", path="data/wikitext-103", master_process=True,
    )
    available = loader.num_total_tokens // sequence_length
    if available < blocks:
        raise SystemExit(f"only {available} complete validation blocks; expected at least {blocks}")
    total_loss = 0.0
    with torch.inference_mode():
        for _ in range(blocks):
            inputs, labels = loader.next_batch()
            inputs, labels = inputs.to(device), labels.to(device)
            context = torch.autocast(device_type="cuda", dtype=torch.bfloat16) if device.type == "cuda" else torch.no_grad()
            with context:
                _, loss = model(inputs, labels)
            total_loss += float(loss)
    value = math.exp(total_loss / blocks)
    if not math.isfinite(value) or value < 0.0:
        raise SystemExit(f"invalid perplexity: {value}")
    payload = {
        "metric_id": "cable_gpt_tiny_wikitext103_2048_ppl",
        "metric": "perplexity", "unit": "perplexity", "value": value,
        "evaluation_blocks": blocks, "sequence_length": sequence_length,
        "checkpoint": str(checkpoint),
    }
    output = Path("artifacts/cable-wikitext103-ppl2048.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
