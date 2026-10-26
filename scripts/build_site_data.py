#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "task_pool" / "TASK_INVENTORY_47.csv"
OUTPUT = ROOT / "website" / "data" / "tasks.json"

DOMAIN_LABELS = {
    "agents_tool_use": "Agents and tool use",
    "computer_vision": "Computer vision",
    "evaluation_benchmark": "Evaluation and benchmarks",
    "generative_models": "Generative models",
    "graph_learning": "Graph learning",
    "information_retrieval": "Information retrieval",
    "knowledge_reasoning": "Knowledge and reasoning",
    "llm_foundation_models": "LLM foundations",
    "multimodal_learning": "Multimodal learning",
    "optimization_theory": "Optimization theory",
    "other_nlp": "Other NLP",
    "reinforcement_learning": "Reinforcement learning",
    "safety_alignment": "Safety and alignment",
    "scientific_ml": "Scientific machine learning",
    "time_series": "Time-series analysis",
}


def scale_fields(scale_class: str) -> tuple[str, str]:
    if scale_class == "full_scale":
        return "paper-scale", "Paper-scale"
    return "resource-bounded", "Resource-bounded"


def hardware_label(row: dict[str, str]) -> str:
    gpu_count = int(row["gpu_count"])
    if gpu_count == 0:
        return f'{row["cpu_cores"]} CPU cores'
    return f'{gpu_count} x H100-class GPU'


def reference_display(row: dict[str, str]) -> str:
    unit = row["metric_unit"].strip().lower()
    suffix = "%" if unit == "percent" else ""
    return f'{row["reference_value"]}{suffix}'


def main() -> None:
    with SOURCE.open(encoding="utf-8-sig", newline="") as handle:
        source_rows = list(csv.DictReader(handle))

    domain_counts = Counter(row["screening_domain"] for row in source_rows)
    tasks = []
    for row in source_rows:
        scale_key, scale_label = scale_fields(row["scale_class"])
        tasks.append(
            {
                "project_id": row["project_id"],
                "paper_title": row["paper_title"],
                "domain_key": row["screening_domain"],
                "domain_label": DOMAIN_LABELS[row["screening_domain"]],
                "target_task": row["target_task"],
                "target_metric": row["target_metric"],
                "reference_display": reference_display(row),
                "scale_key": scale_key,
                "scale_label": scale_label,
                "evaluation_dataset": row["evaluation_dataset"],
                "wall_time_hours": row["wall_time_hours"],
                "hardware_label": hardware_label(row),
                "repository_url": row["repository_url"],
            }
        )

    domains = [
        {"key": key, "label": DOMAIN_LABELS[key], "count": count}
        for key, count in sorted(
            domain_counts.items(), key=lambda item: (-item[1], DOMAIN_LABELS[item[0]])
        )
    ]
    payload = {
        "schema_version": "1.0",
        "summary": {
            "task_count": len(tasks),
            "domain_count": len(domains),
            "domains": domains,
        },
        "tasks": tasks,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
