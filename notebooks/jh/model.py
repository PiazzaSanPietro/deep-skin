"""ResNet-50 backbone cheek classifier."""

from pathlib import Path

import torch
import torch.nn as nn
from torchvision import models


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCAL_RESNET50_PATH = (
    PROJECT_ROOT / "checkpoints" / "pretrained" / "resnet50-0676ba61.pth"
)


class CheekClassifier(nn.Module):
    """ResNet-50 backbone with a configurable classifier head."""

    def __init__(
        self,
        num_classes: int = 6,
        pretrained: bool = True,
        freeze_backbone: bool = False,
        dropout_p: float = 0.5,
    ):
        super().__init__()
        backbone = models.resnet50(weights=None)
        if pretrained:
            if not LOCAL_RESNET50_PATH.exists():
                raise FileNotFoundError(
                    f"Missing pretrained ResNet-50 weights: {LOCAL_RESNET50_PATH}"
                )
            state_dict = torch.load(LOCAL_RESNET50_PATH, map_location="cpu")
            backbone.load_state_dict(state_dict)

        in_features = backbone.fc.in_features
        # 2-layer head: 2048 → 512 → num_classes
        # BatchNorm으로 안정적인 학습, Dropout으로 과적합 방지
        backbone.fc = nn.Sequential(
            nn.Linear(in_features, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_p),
            nn.Linear(512, num_classes),
        )
        self.backbone = backbone

        if freeze_backbone:
            self.freeze_backbone()

    def freeze_backbone(self) -> None:
        """Freeze every backbone parameter except the classifier head."""
        for name, param in self.backbone.named_parameters():
            param.requires_grad = name.startswith("fc.")

    def unfreeze_backbone(self) -> None:
        """Enable gradients for the whole model."""
        for param in self.backbone.parameters():
            param.requires_grad = True

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.backbone(x)


def get_model(
    num_classes: int = 6,
    pretrained: bool = True,
    freeze_backbone: bool = False,
    dropout_p: float = 0.5,
) -> CheekClassifier:
    return CheekClassifier(
        num_classes=num_classes,
        pretrained=pretrained,
        freeze_backbone=freeze_backbone,
        dropout_p=dropout_p,
    )
