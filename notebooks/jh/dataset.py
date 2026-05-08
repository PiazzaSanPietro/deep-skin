"""Cheek crop image dataset for PyTorch."""

import pandas as pd
import torch
from PIL import Image, ImageOps
from torch.utils.data import Dataset
from torchvision import transforms


class ResizeAndPad:
    """Resize while keeping aspect ratio, then pad to a square canvas."""

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
            pad_w - (pad_w // 2),
            pad_h - (pad_h // 2),
        )
        return ImageOps.expand(resized, border=padding, fill=self.fill)


class CheekDataset(Dataset):
    """CSV-based cheek classification dataset."""

    _LABEL_COL = {"pore": "pore_label", "pigmentation": "pigmentation_label"}

    def __init__(self, csv_path, target: str = "pore", transform=None):
        assert target in self._LABEL_COL, "target must be 'pore' or 'pigmentation'"
        self.label_col = self._LABEL_COL[target]
        self.transform = transform

        df = pd.read_csv(csv_path, usecols=["image_path", self.label_col])
        df = df.dropna(subset=[self.label_col, "image_path"])
        df[self.label_col] = df[self.label_col].astype(int)

        invalid = ~df[self.label_col].between(0, 5)
        if invalid.any():
            raise ValueError(
                f"label values must be in 0..5: {df.loc[invalid, self.label_col].unique()}"
            )

        self.df = df.reset_index(drop=True)

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        row = self.df.iloc[idx]
        img = Image.open(row["image_path"]).convert("RGB")
        if self.transform:
            img = self.transform(img)
        label = torch.tensor(int(row[self.label_col]), dtype=torch.long)
        return img, label


def get_transforms(
    image_size: int = 224,
    split: str = "train",
    flip_prob: float = 0.5,
    jitter_brightness: float = 0.2,
    jitter_contrast: float = 0.2,
    jitter_saturation: float = 0.1,
    affine_prob: float = 0.5,
    affine_degrees: float = 5.0,
    affine_translate: float = 0.02,
    affine_scale_min: float = 0.98,
    affine_scale_max: float = 1.02,
    blur_prob: float = 0.2,
    erasing_prob: float = 0.25,
) -> transforms.Compose:
    """Return transforms for the given split."""
    normalize = transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    )
    resize_and_pad = ResizeAndPad(image_size)
    fill = resize_and_pad.fill
    if split == "train":
        augmentations = [
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
            # 카메라 블러 시뮬레이션 — 다양한 촬영 장비 대응
            transforms.RandomApply(
                [transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 1.0))],
                p=blur_prob,
            ),
            transforms.ToTensor(),
            normalize,
            # 피부 일부 가림 시뮬레이션 — 그림자/손가락 등 실제 촬영 노이즈
            transforms.RandomErasing(
                p=erasing_prob,
                scale=(0.02, 0.10),
                ratio=(0.3, 3.3),
                value="random",
            ),
        ]
        return transforms.Compose([
            *augmentations,
        ])
    return transforms.Compose([
        resize_and_pad,
        transforms.ToTensor(),
        normalize,
    ])
