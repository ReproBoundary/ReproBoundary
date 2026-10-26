#!/usr/bin/env python3
"""Run the complete frozen GeoBench-2D FreeFine pipeline on one GPU."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import cv2
import numpy as np
import torch
from diffusers import DDIMScheduler

from src.demo.model import FreeFinePipeline
from src.utils.attention import (
    Attention_Modulator,
    register_attention_control,
    register_attention_control_4bggen,
)
from src.utils.vis_utils import (
    read_and_resize_img,
    read_and_resize_mask,
    read_and_resize_mask_with_dilation,
)


def save_rgb(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR)):
        raise RuntimeError(f"failed to save {path}")


def save_mask(path: Path, mask: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), mask):
        raise RuntimeError(f"failed to save {path}")


def coarse_edit(source: np.ndarray, source_mask: np.ndarray, edit_param, background: np.ndarray):
    if source_mask.ndim == 3:
        source_mask = source_mask[:, :, 0]
    dx, dy, _dz, _rx, _ry, rz, sx, sy, _sz = edit_param
    height, width = source_mask.shape[:2]
    ys, xs = np.where(source_mask)
    if not len(ys) or not len(xs):
        raise ValueError("empty source mask")
    top, bottom, left, right = np.min(ys), np.max(ys), np.min(xs), np.max(xs)
    center_x, center_y = (right + left) / 2, (top + bottom) / 2
    if left + dx < 0 or right + dx > width or top + dy < 0 or bottom + dy > height:
        raise ValueError("transformed object is outside image boundary")
    matrix = cv2.getRotationMatrix2D((center_x, center_y), -rz, 1)
    matrix[0, 2] += dx + (1 - sx) * center_x
    matrix[1, 2] += dy + (1 - sy) * center_y
    matrix[0, 0] *= sx
    matrix[1, 1] *= sy
    transformed_image = cv2.warpAffine(source, matrix, (width, height))
    transformed_mask = cv2.warpAffine(
        source_mask.astype(np.uint8), matrix, (width, height), flags=cv2.INTER_NEAREST
    ).astype(bool)
    coarse = np.where(transformed_mask[:, :, None], transformed_image, background)
    return coarse, transformed_mask.astype(np.uint8) * 255


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--stage", choices=("backgrounds", "edits", "all"), required=True)
    args = parser.parse_args()

    annotation_path = args.data_root / "annotation_2d.json"
    annotations = json.loads(annotation_path.read_text(encoding="utf-8"))
    source_count = len(annotations)
    instance_count = sum(len(row["instances"]) for row in annotations.values())
    edit_count = sum(
        len(instance)
        for row in annotations.values()
        for instance in row["instances"].values()
    )
    if (source_count, instance_count, edit_count) != (609, 668, 5677):
        raise ValueError(
            f"GeoBench-2D cardinality mismatch: {(source_count, instance_count, edit_count)}"
        )

    model = FreeFinePipeline.from_pretrained(
        str(args.model), torch_dtype=torch.float16, variant="fp16", local_files_only=True
    ).to("cuda:0")
    model.scheduler = DDIMScheduler.from_config(model.scheduler.config)
    model._progress_bar_config = {"disable": True}
    model.enable_attention_slicing()

    output_root = args.data_root / "Geo-Bench-2D"
    background_root = output_root / "inp_img_blended"
    coarse_root = output_root / "coarse_input_frozen"
    refined_root = output_root / "Gen_results_FreeFine_2d"
    rng = random.Random(args.seed)
    results: dict[str, dict] = {}

    for source_id in sorted(annotations, key=lambda value: int(value)):
        source_record = annotations[source_id]
        results[source_id] = {"instances": {}}
        for instance_id in sorted(source_record["instances"], key=lambda value: int(value)):
            edits = source_record["instances"][instance_id]
            first = edits[sorted(edits, key=lambda value: int(value))[0]]
            source = read_and_resize_img(str(args.data_root / first["ori_img_path"]))
            source_mask = read_and_resize_mask(str(args.data_root / first["ori_mask_path"]))
            dilated_mask = read_and_resize_mask_with_dilation(
                str(args.data_root / first["ori_mask_path"]), dilation_factor=30, forbit_area=None
            )

            background_path = background_root / source_id / instance_id / "inp_img.png"
            if args.stage in ("backgrounds", "all"):
                controller = Attention_Modulator(start_layer=10)
                model.controller = controller
                register_attention_control_4bggen(model, controller)
                model.modify_unet_forward()
                background = model.FreeFine_background_generation(
                    ori_img=source,
                    ori_mask=dilated_mask,
                    guidance_text="empty scene",
                    guidance_scale=7.5,
                    eta=1.0,
                    end_scale=0.5,
                    end_step=35,
                    num_step=50,
                    start_step=1,
                    seed=rng.randrange(10**16),
                    return_intermediates=False,
                    local_text_edit=True,
                    local_perturbation=True,
                )
                blurred = cv2.GaussianBlur(dilated_mask, (21, 21), 0) / 255
                blend_mask = 1 - (1 - dilated_mask) * (1 - blurred)
                background = (source * (1 - blend_mask) + background * blend_mask).astype(
                    background.dtype
                )
                save_rgb(background_path, background)
            else:
                if not background_path.is_file():
                    raise FileNotFoundError(background_path)
                background = read_and_resize_img(str(background_path))

            if args.stage == "backgrounds":
                continue

            results[source_id]["instances"][instance_id] = {}
            for edit_id in sorted(edits, key=lambda value: int(value)):
                case = dict(edits[edit_id])
                coarse, target_mask = coarse_edit(
                    source, source_mask, case["edit_param"], background
                )
                coarse_path = coarse_root / source_id / instance_id / f"{edit_id}.png"
                save_rgb(coarse_path, coarse)

                controller = Attention_Modulator(start_layer=10)
                model.controller = controller
                register_attention_control(model, controller)
                model.modify_unet_forward()
                refined = model.FreeFine_generation(
                    ori_img=source,
                    ori_mask=source_mask,
                    coarse_input=coarse,
                    target_mask=target_mask,
                    guidance_text="",
                    guidance_scale=7.5,
                    eta=1.0,
                    end_scale=0.0,
                    end_step=50,
                    num_step=50,
                    start_step=35,
                    seed=args.seed,
                    draw_mask=None,
                    return_intermediates=False,
                    use_auto_draw=True,
                    reduce_inp_artifacts=True,
                    cons_area=target_mask,
                )
                refined_path = refined_root / source_id / instance_id / f"{edit_id}.png"
                save_rgb(refined_path, refined)
                case["coarse_input_path"] = str(coarse_path.relative_to(args.data_root))
                case["gen_img_path"] = str(refined_path.relative_to(args.data_root))
                results[source_id]["instances"][instance_id][edit_id] = case

    result_path = args.data_root / "generated_results_2d_freefine.json"
    if args.stage in ("edits", "all"):
        result_path.write_text(json.dumps(results, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"stage": args.stage, "source_images": source_count, "instances": instance_count, "edits": edit_count, "result": str(result_path) if args.stage != "backgrounds" else None}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
