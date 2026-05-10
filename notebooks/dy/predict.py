"""Run inference on a cropped forehead or glabella image."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from PIL import Image

from dataset import get_transforms
from model import get_model
from recommendation import build_report
from task_config import CLASSIFICATION_TASKS, REGRESSION_TARGETS
from xai import save_gradcam_overlay


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True, help="Cropped forehead/glabella image.")
    parser.add_argument("--part", choices=["forehead", "glabella"], required=True)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--gradcam-dir", type=Path, default=None)
    parser.add_argument("--image-size", type=int, default=None)
    return parser.parse_args()


def _load_checkpoint(path: Path, device: torch.device) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing checkpoint: {path}")
    return torch.load(path, map_location=device)


def _build_model(checkpoint: dict[str, Any], device: torch.device) -> torch.nn.Module:
    config = checkpoint.get("config", {})
    model = get_model(
        weights="none",
        projection_dim=int(config.get("projection_dim", 512)),
        dropout_p=float(config.get("dropout_p", 0.30)),
        freeze_backbone=False,
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()
    return model


def _inverse_regression(
    reg_tensor: torch.Tensor,
    regression_stats: dict[str, dict[str, float]],
) -> dict[str, float]:
    values: dict[str, float] = {}
    for idx, target in enumerate(REGRESSION_TARGETS):
        stats = regression_stats.get(target, {"mean": 0.0, "std": 1.0})
        value = (float(reg_tensor[idx]) * float(stats.get("std", 1.0))) + float(
            stats.get("mean", 0.0)
        )
        values[target] = value
    return values


def predict(args: argparse.Namespace) -> dict[str, Any]:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = _load_checkpoint(args.checkpoint, device)
    model = _build_model(checkpoint, device)
    config = checkpoint.get("config", {})
    image_size = args.image_size or int(config.get("image_size", 224))

    original = Image.open(args.image).convert("RGB")
    transform = get_transforms(image_size=image_size, split="val")
    image_tensor = transform(original).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(image_tensor)

    predictions: dict[str, dict[str, int | float]] = {}
    for task in CLASSIFICATION_TASKS:
        if task.part_name != args.part:
            continue
        probs = F.softmax(outputs["cls"][task.name], dim=1)[0]
        grade = int(probs.argmax().item())
        predictions[task.name] = {
            "grade": grade,
            "confidence": float(probs[grade].item()),
        }

    regression = {}
    if args.part == "forehead":
        regression = _inverse_regression(
            outputs["reg"][0].detach().cpu(),
            checkpoint.get("regression_stats", {}),
        )

    report = build_report(predictions, regression)

    if args.gradcam_dir is not None:
        gradcam_paths: dict[str, str] = {}
        for task_name, pred in predictions.items():
            output_path = args.gradcam_dir / f"{args.image.stem}_{task_name}_gradcam.jpg"
            save_gradcam_overlay(
                model=model,
                image_tensor=image_tensor,
                original_image=original,
                output_path=output_path,
                task_name=task_name,
                class_idx=int(pred["grade"]),
            )
            gradcam_paths[task_name] = str(output_path)
        report["gradcam_paths"] = gradcam_paths

    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    return report


def main() -> None:
    report = predict(parse_args())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
