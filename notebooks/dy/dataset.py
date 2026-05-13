"""PyTorch dataset utilities for forehead/glabella multitask learning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import torch
from PIL import Image, ImageOps
from torch.utils.data import Dataset
from torchvision import transforms

from task_config import (
    CLASSIFICATION_TASKS,
    REGRESSION_TARGETS,
    ClassificationTask,
    map_grade,
)


class ResizeAndPad:
    """Resize while preserving aspect ratio, then pad to a square canvas."""

    def __init__(self, image_size: int, fill: tuple[int, int, int] = (124, 116, 104)):
        self.image_size = image_size
        self.fill = fill
        self.resample = Image.Resampling.BILINEAR

    def __call__(self, img: Image.Image) -> Image.Image:
        width, height = img.size
        scale = self.image_size / max(width, height)
        resized_width = max(1, int(round(width * scale)))
        resized_height = max(1, int(round(height * scale)))
        resized = img.resize((resized_width, resized_height), self.resample)
        pad_w = self.image_size - resized_width
        pad_h = self.image_size - resized_height
        padding = (
            pad_w // 2,
            pad_h // 2,
            pad_w - pad_w // 2,
            pad_h - pad_h // 2,
        )
        return ImageOps.expand(resized, border=padding, fill=self.fill)


def get_transforms(
    image_size: int = 224,
    split: str = "train",
    flip_prob: float = 0.25,
    jitter_brightness: float = 0.18,
    jitter_contrast: float = 0.18,
    jitter_saturation: float = 0.08,
    affine_prob: float = 0.35,
    affine_degrees: float = 4.0,
    affine_translate: float = 0.015,
    affine_scale_min: float = 0.98,
    affine_scale_max: float = 1.02,
    blur_prob: float = 0.12,
    erasing_prob: float = 0.10,
) -> transforms.Compose:
    normalize = transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    )
    resize_and_pad = ResizeAndPad(image_size)
    fill = resize_and_pad.fill

    if split == "train":
        return transforms.Compose(
            [
                resize_and_pad,
                transforms.RandomHorizontalFlip(p=flip_prob),
                transforms.RandomApply(
                    [
                        transforms.RandomAffine(
                            degrees=affine_degrees,
                            translate=(affine_translate, affine_translate),
                            scale=(affine_scale_min, affine_scale_max),
                            fill=fill,
                        )
                    ],
                    p=affine_prob,
                ),
                transforms.ColorJitter(
                    brightness=jitter_brightness,
                    contrast=jitter_contrast,
                    saturation=jitter_saturation,
                ),
                transforms.RandomApply(
                    [transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 0.8))],
                    p=blur_prob,
                ),
                transforms.ToTensor(),
                normalize,
                transforms.RandomErasing(
                    p=erasing_prob,
                    scale=(0.01, 0.06),
                    ratio=(0.4, 2.5),
                    value="random",
                ),
            ]
        )

    return transforms.Compose([resize_and_pad, transforms.ToTensor(), normalize])


def load_regression_stats(path: Path | str | None) -> dict[str, dict[str, float]] | None:
    if path is None:
        return None
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("targets", payload)


class ForeheadGlabellaDataset(Dataset):
    """CSV-backed dataset with masked classification and regression targets."""

    def __init__(
        self,
        csv_path: Path | str,
        transform: Any | None = None,
        regression_stats: dict[str, dict[str, float]] | None = None,
        return_metadata: bool = False,
        tasks: tuple[ClassificationTask, ...] = CLASSIFICATION_TASKS,
        grade_scheme: str = "original",
    ):
        self.csv_path = Path(csv_path)
        self.transform = transform
        self.regression_stats = regression_stats
        self.return_metadata = return_metadata
        self.tasks = tasks
        self.grade_scheme = grade_scheme

        df = pd.read_csv(self.csv_path)
        if "image_path" not in df.columns:
            raise ValueError(f"Missing image_path column in {self.csv_path}")
        self.df = df.reset_index(drop=True)

    def __len__(self) -> int:
        return len(self.df)

    def _classification_targets(self, row: pd.Series) -> torch.Tensor:
        values: list[int] = []
        for task in self.tasks:
            raw_value = row.get(task.column)
            if pd.isna(raw_value) or raw_value == "":
                values.append(-100)
            else:
                value = map_grade(int(raw_value), self.grade_scheme)
                if value < 0 or value >= task.num_classes:
                    raise ValueError(
                        f"{task.column} must be in 0..{task.num_classes - 1}: {value}"
                    )
                values.append(value)
        return torch.tensor(values, dtype=torch.long)

    def _regression_targets(self, row: pd.Series) -> tuple[torch.Tensor, torch.Tensor]:
        values: list[float] = []
        mask: list[bool] = []
        for target in REGRESSION_TARGETS:
            raw_value = row.get(target)
            if pd.isna(raw_value) or raw_value == "":
                values.append(0.0)
                mask.append(False)
                continue

            value = float(raw_value)
            if self.regression_stats and target in self.regression_stats:
                stats = self.regression_stats[target]
                mean = float(stats.get("mean", 0.0))
                std = max(float(stats.get("std", 1.0)), 1e-6)
                value = (value - mean) / std
            values.append(value)
            mask.append(True)
        return (
            torch.tensor(values, dtype=torch.float32),
            torch.tensor(mask, dtype=torch.bool),
        )

    def __getitem__(self, idx: int) -> dict[str, Any]:
        row = self.df.iloc[idx]
        image = Image.open(row["image_path"]).convert("RGB")
        if self.transform is not None:
            image = self.transform(image)

        reg_targets, reg_mask = self._regression_targets(row)
        sample: dict[str, Any] = {
            "image": image,
            "cls_targets": self._classification_targets(row),
            "reg_targets": reg_targets,
            "reg_mask": reg_mask,
        }
        if self.return_metadata:
            sample["metadata"] = {
                "image_path": row.get("image_path", ""),
                "part_name": row.get("part_name", ""),
                "id": str(row.get("id", "")),
            }
        return sample
