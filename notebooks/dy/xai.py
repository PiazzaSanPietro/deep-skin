"""Grad-CAM helpers for the ResNet-50 multitask model."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import torch
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".cache" / "matplotlib"))


class GradCAM:
    def __init__(self, model: torch.nn.Module, target_layer: torch.nn.Module):
        self.model = model
        self.target_layer = target_layer
        self.activations: torch.Tensor | None = None
        self.gradients: torch.Tensor | None = None
        self.forward_handle = target_layer.register_forward_hook(self._save_activation)
        self.backward_handle = target_layer.register_full_backward_hook(self._save_gradient)

    def _save_activation(self, _module, _inputs, output) -> None:
        self.activations = output.detach()

    def _save_gradient(self, _module, _grad_input, grad_output) -> None:
        self.gradients = grad_output[0].detach()

    def close(self) -> None:
        self.forward_handle.remove()
        self.backward_handle.remove()

    def __call__(
        self,
        image_tensor: torch.Tensor,
        task_name: str | None = None,
        class_idx: int | None = None,
        regression_idx: int | None = None,
    ) -> np.ndarray:
        self.model.zero_grad(set_to_none=True)
        outputs = self.model(image_tensor)
        if task_name is not None:
            logits = outputs["cls"][task_name]
            if class_idx is None:
                class_idx = int(logits.argmax(dim=1).item())
            target_score = logits[:, class_idx].sum()
        elif regression_idx is not None:
            target_score = outputs["reg"][:, regression_idx].sum()
        else:
            raise ValueError("Either task_name or regression_idx is required.")

        target_score.backward()
        if self.activations is None or self.gradients is None:
            raise RuntimeError("Grad-CAM hooks did not capture activations/gradients.")

        weights = self.gradients.mean(dim=(2, 3), keepdim=True)
        cam = torch.relu((weights * self.activations).sum(dim=1, keepdim=True))
        cam = cam.squeeze().detach().cpu().numpy()
        cam = cam - cam.min()
        max_value = cam.max()
        if max_value > 0:
            cam = cam / max_value
        return cam


def _heatmap_to_rgba(heatmap: np.ndarray) -> Image.Image:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.cm as cm

    colored = cm.get_cmap("jet")(heatmap)
    colored[..., 3] = np.clip(heatmap * 0.55, 0.0, 0.55)
    return Image.fromarray((colored * 255).astype(np.uint8), mode="RGBA")


def save_gradcam_overlay(
    model: torch.nn.Module,
    image_tensor: torch.Tensor,
    original_image: Image.Image,
    output_path: Path,
    task_name: str | None = None,
    class_idx: int | None = None,
    regression_idx: int | None = None,
) -> Path:
    was_training = model.training
    model.eval()
    gradcam = GradCAM(model, model.backbone.layer4[-1])
    try:
        heatmap = gradcam(
            image_tensor=image_tensor,
            task_name=task_name,
            class_idx=class_idx,
            regression_idx=regression_idx,
        )
    finally:
        gradcam.close()
        model.train(was_training)

    base = original_image.convert("RGBA")
    heatmap_image = Image.fromarray((heatmap * 255).astype(np.uint8), mode="L")
    heatmap_image = heatmap_image.resize(base.size, Image.Resampling.BILINEAR)
    overlay = Image.alpha_composite(base, _heatmap_to_rgba(np.asarray(heatmap_image) / 255.0))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    overlay.convert("RGB").save(output_path, quality=95)
    return output_path
