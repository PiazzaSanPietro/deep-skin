"""Train cheek classification models with checkpoint save/resume support.

Usage examples:
    python notebooks/jh/train.py --target pore
    python notebooks/jh/train.py --target pigmentation --freeze-backbone
    python notebooks/jh/train.py --target pore --resume latest
"""

import argparse
import csv
from datetime import datetime
import json
import logging
import random
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import f1_score
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.data import DataLoader, WeightedRandomSampler


PROJECT_ROOT = Path(__file__).resolve().parents[2]

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dataset import CheekDataset, get_transforms
from model import get_model


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DEFAULT_CHECKPOINT_ROOT = PROJECT_ROOT / "checkpoints" / "trained"


class FocalLoss(nn.Module):
    """Multi-class focal loss with optional per-class weighting."""

    def __init__(self, weight: torch.Tensor | None = None, gamma: float = 2.0):
        super().__init__()
        self.weight = weight
        self.gamma = gamma

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        log_probs = F.log_softmax(logits, dim=1)
        probs = log_probs.exp()

        log_pt = log_probs.gather(1, targets.unsqueeze(1)).squeeze(1)
        pt = probs.gather(1, targets.unsqueeze(1)).squeeze(1)
        loss = -((1 - pt) ** self.gamma) * log_pt

        if self.weight is not None:
            loss = loss * self.weight[targets]

        return loss.mean()


def parse_args() -> argparse.Namespace:
    # Two-pass: first extract --config, then apply it as defaults before full parse.
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", type=Path, default=None)
    pre_args, _ = pre.parse_known_args()

    config_defaults: dict = {}
    if pre_args.config is not None:
        with open(pre_args.config, encoding="utf-8") as f:
            config_defaults = json.load(f)

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=None, help="JSON config file. CLI args override it.")
    parser.add_argument(
        "--target",
        choices=["pore", "pigmentation"],
        default=None,
        help="Classification target.",
    )
    parser.add_argument(
        "--train-csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "cheek_train_metadata.csv",
        help="Training metadata CSV path.",
    )
    parser.add_argument(
        "--val-csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "cheek_val_metadata.csv",
        help="Validation metadata CSV path.",
    )
    parser.add_argument("--epochs", type=int, default=60, help="Total epochs to run.")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size.")
    parser.add_argument("--image-size", type=int, default=224, help="Input image size.")
    parser.add_argument("--learning-rate", type=float, default=1e-4, help="Learning rate.")
    parser.add_argument("--weight-decay", type=float, default=1e-3, help="AdamW weight decay.")
    parser.add_argument("--dropout-p", type=float, default=0.3, help="Dropout probability in classifier head.")
    parser.add_argument("--label-smoothing", type=float, default=0.05, help="Label smoothing for CrossEntropyLoss.")
    parser.add_argument(
        "--loss",
        choices=["ce", "weighted_ce", "focal"],
        default="weighted_ce",
        help="Training loss function.",
    )
    parser.add_argument(
        "--focal-gamma",
        type=float,
        default=2.0,
        help="Gamma value for focal loss.",
    )
    parser.add_argument("--num-workers", type=int, default=0, help="DataLoader workers.")
    parser.add_argument("--num-classes", type=int, default=6, help="Number of classes.")
    parser.add_argument("--seed", type=int, default=20260507, help="Random seed.")
    parser.add_argument(
        "--scheduler-factor",
        type=float,
        default=0.5,
        help="ReduceLROnPlateau factor.",
    )
    parser.add_argument(
        "--scheduler-patience",
        type=int,
        default=7,
        help="ReduceLROnPlateau patience in epochs.",
    )
    parser.add_argument(
        "--scheduler-min-lr",
        type=float,
        default=1e-6,
        help="Minimum learning rate for ReduceLROnPlateau.",
    )
    parser.add_argument(
        "--early-stopping-patience",
        type=int,
        default=12,
        help="Stop if macro_f1 does not improve for this many epochs. Set <=0 to disable.",
    )
    parser.add_argument(
        "--early-stopping-min-delta",
        type=float,
        default=1e-4,
        help="Minimum macro_f1 improvement to reset early stopping.",
    )
    parser.add_argument("--flip-prob", type=float, default=0.5, help="Horizontal flip probability.")
    parser.add_argument(
        "--jitter-brightness",
        type=float,
        default=0.2,
        help="ColorJitter brightness value.",
    )
    parser.add_argument(
        "--jitter-contrast",
        type=float,
        default=0.2,
        help="ColorJitter contrast value.",
    )
    parser.add_argument(
        "--jitter-saturation",
        type=float,
        default=0.1,
        help="ColorJitter saturation value.",
    )
    parser.add_argument(
        "--affine-prob",
        type=float,
        default=0.5,
        help="Probability of applying RandomAffine.",
    )
    parser.add_argument(
        "--affine-degrees",
        type=float,
        default=5.0,
        help="RandomAffine degree range.",
    )
    parser.add_argument(
        "--affine-translate",
        type=float,
        default=0.02,
        help="RandomAffine translate ratio.",
    )
    parser.add_argument(
        "--affine-scale-min",
        type=float,
        default=0.98,
        help="RandomAffine minimum scale.",
    )
    parser.add_argument(
        "--affine-scale-max",
        type=float,
        default=1.02,
        help="RandomAffine maximum scale.",
    )
    parser.add_argument("--blur-prob", type=float, default=0.2, help="GaussianBlur apply probability.")
    parser.add_argument("--erasing-prob", type=float, default=0.25, help="RandomErasing apply probability.")
    parser.add_argument(
        "--oversample",
        action="store_true",
        help="Use WeightedRandomSampler to balance class frequencies in each training batch.",
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        default=None,
        help="Run directory for latest/best checkpoints. If omitted, a run directory is created automatically.",
    )
    parser.add_argument(
        "--run-name",
        type=str,
        default="",
        help="Optional run name used when checkpoint-dir is not provided.",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default="",
        help="Resume from checkpoint path or keyword: latest / best.",
    )
    parser.add_argument(
        "--freeze-backbone",
        action="store_true",
        help="Train only the classifier head.",
    )
    parser.add_argument(
        "--no-pretrained",
        action="store_true",
        help="Disable external pretrained ResNet-50 weights.",
    )
    if config_defaults:
        parser.set_defaults(**config_defaults)
    args = parser.parse_args()
    if args.target is None:
        parser.error("--target is required (set via CLI or --config file)")
    return args


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def load_csv(csv_path: Path, target: str) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing metadata CSV: {csv_path}")
    label_col = "pore_label" if target == "pore" else "pigmentation_label"
    return pd.read_csv(csv_path, usecols=["angle", label_col])


def log_dataset_summary(name: str, df: pd.DataFrame, target: str) -> None:
    label_col = "pore_label" if target == "pore" else "pigmentation_label"
    angle_counts = dict(sorted(Counter(df["angle"].astype(int)).items()))
    label_counts = dict(sorted(Counter(df[label_col].astype(int)).items()))
    logger.info("[%s] samples=%d", name, len(df))
    logger.info("[%s] angle distribution=%s", name, angle_counts)
    logger.info("[%s] %s distribution=%s", name, label_col, label_counts)


def build_dataloaders(args: argparse.Namespace, target: str) -> tuple[DataLoader, DataLoader]:
    train_tf = get_transforms(
        image_size=args.image_size,
        split="train",
        flip_prob=args.flip_prob,
        jitter_brightness=args.jitter_brightness,
        jitter_contrast=args.jitter_contrast,
        jitter_saturation=args.jitter_saturation,
        affine_prob=args.affine_prob,
        affine_degrees=args.affine_degrees,
        affine_translate=args.affine_translate,
        affine_scale_min=args.affine_scale_min,
        affine_scale_max=args.affine_scale_max,
        blur_prob=args.blur_prob,
        erasing_prob=args.erasing_prob,
    )
    val_tf = get_transforms(args.image_size, "val")
    train_ds = CheekDataset(args.train_csv, target=target, transform=train_tf)
    val_ds = CheekDataset(args.val_csv, target=target, transform=val_tf)

    if getattr(args, "oversample", False):
        label_col = "pore_label" if target == "pore" else "pigmentation_label"
        labels = train_ds.df[label_col].to_numpy()
        counts = np.bincount(labels, minlength=args.num_classes).astype(float)
        class_w = 1.0 / np.where(counts > 0, counts, 1.0)
        sample_weights = torch.tensor([class_w[lbl] for lbl in labels], dtype=torch.double)
        sampler = WeightedRandomSampler(
            weights=sample_weights,
            num_samples=len(sample_weights),
            replacement=True,
        )
        train_loader = DataLoader(
            train_ds,
            batch_size=args.batch_size,
            sampler=sampler,
            num_workers=args.num_workers,
        )
    else:
        train_loader = DataLoader(
            train_ds,
            batch_size=args.batch_size,
            shuffle=True,
            num_workers=args.num_workers,
        )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
    )
    return train_loader, val_loader


def compute_class_weights(
    df: pd.DataFrame,
    target: str,
    num_classes: int,
    device: str,
) -> torch.Tensor:
    label_col = "pore_label" if target == "pore" else "pigmentation_label"
    counts = df[label_col].value_counts().reindex(range(num_classes), fill_value=0).sort_index()

    weights = []
    total = int(counts.sum())
    for count in counts.tolist():
        if count <= 0:
            weights.append(0.0)
        else:
            weights.append(total / (num_classes * count))

    weights_tensor = torch.tensor(weights, dtype=torch.float32, device=device)
    positive = weights_tensor > 0
    if positive.any():
        weights_tensor[positive] = weights_tensor[positive] / weights_tensor[positive].mean()
    return weights_tensor


def build_criterion(
    args: argparse.Namespace,
    train_df: pd.DataFrame,
    device: str,
) -> tuple[nn.Module, torch.Tensor | None]:
    class_weights = None
    if args.loss in {"weighted_ce", "focal"}:
        class_weights = compute_class_weights(
            df=train_df,
            target=args.target,
            num_classes=args.num_classes,
            device=device,
        )

    if args.loss == "ce":
        criterion = nn.CrossEntropyLoss(label_smoothing=args.label_smoothing)
    elif args.loss == "weighted_ce":
        criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=args.label_smoothing)
    else:
        criterion = FocalLoss(weight=class_weights, gamma=args.focal_gamma)

    return criterion, class_weights


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: str,
) -> tuple[float, float]:
    model.train()
    total_loss = 0.0
    total_correct = 0
    total_samples = 0

    for images, labels in loader:
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * images.size(0)
        preds = outputs.argmax(dim=1)
        total_correct += (preds == labels).sum().item()
        total_samples += images.size(0)

    return total_loss / total_samples, total_correct / total_samples


def validate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: str,
) -> dict:
    model.eval()
    total_loss = 0.0
    total_correct = 0
    total_samples = 0
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)
            loss = criterion(outputs, labels)

            total_loss += loss.item() * images.size(0)
            preds = outputs.argmax(dim=1)
            total_correct += (preds == labels).sum().item()
            total_samples += images.size(0)

            all_preds.extend(preds.cpu().tolist())
            all_labels.extend(labels.cpu().tolist())

    return {
        "val_loss": total_loss / total_samples,
        "val_acc": total_correct / total_samples,
        "macro_f1": f1_score(all_labels, all_preds, average="macro", zero_division=0),
    }


def checkpoint_paths(checkpoint_dir: Path, target: str) -> tuple[Path, Path]:
    latest_path = checkpoint_dir / f"{target}_latest.pth"
    best_path = checkpoint_dir / f"{target}_best.pth"
    return latest_path, best_path


def history_path(checkpoint_dir: Path, target: str) -> Path:
    return checkpoint_dir / f"{target}_history.csv"


def find_latest_run_dir(parent_dir: Path, target: str, which: str) -> Path:
    if not parent_dir.exists():
        raise FileNotFoundError(f"Run directory root not found: {parent_dir}")

    expected_name = f"{target}_{which}.pth"
    candidates = [
        child for child in parent_dir.iterdir()
        if child.is_dir() and (child / expected_name).exists()
    ]
    if not candidates:
        raise FileNotFoundError(
            f"No run directory with {expected_name} found under: {parent_dir}"
        )
    return max(candidates, key=lambda path: path.stat().st_mtime)


def resolve_checkpoint_dir(args: argparse.Namespace) -> Path:
    if args.checkpoint_dir is not None:
        checkpoint_dir = args.checkpoint_dir
        if args.resume in {"latest", "best"} and not (checkpoint_dir / f"{args.target}_{args.resume}.pth").exists():
            try:
                return find_latest_run_dir(checkpoint_dir, args.target, args.resume)
            except FileNotFoundError:
                return checkpoint_dir
        return checkpoint_dir

    target_root = DEFAULT_CHECKPOINT_ROOT / args.target
    if args.resume == "latest":
        return find_latest_run_dir(target_root, args.target, "latest")
    if args.resume == "best":
        return find_latest_run_dir(target_root, args.target, "best")
    if args.resume:
        return Path(args.resume).resolve().parent

    run_name = args.run_name or datetime.now().strftime("%Y%m%d_%H%M%S")
    return target_root / run_name


def resolve_resume_path(resume: str, checkpoint_dir: Path, target: str) -> Path:
    latest_path, best_path = checkpoint_paths(checkpoint_dir, target)
    if resume == "latest":
        return latest_path
    if resume == "best":
        return best_path
    return Path(resume)


def save_checkpoint(
    path: Path,
    epoch: int,
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    scheduler: ReduceLROnPlateau,
    best_metric: float,
    best_epoch: int,
    epochs_without_improve: int,
    args: argparse.Namespace,
    metrics: dict,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict(),
        "best_macro_f1": best_metric,
        "best_epoch": best_epoch,
        "epochs_without_improve": epochs_without_improve,
        "metrics": metrics,
        "config": {
            "target": args.target,
            "train_csv": str(args.train_csv),
            "val_csv": str(args.val_csv),
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "image_size": args.image_size,
            "learning_rate": args.learning_rate,
            "weight_decay": args.weight_decay,
            "loss": args.loss,
            "focal_gamma": args.focal_gamma,
            "num_workers": args.num_workers,
            "num_classes": args.num_classes,
            "seed": args.seed,
            "freeze_backbone": args.freeze_backbone,
            "pretrained": not args.no_pretrained,
            "scheduler_factor": args.scheduler_factor,
            "scheduler_patience": args.scheduler_patience,
            "scheduler_min_lr": args.scheduler_min_lr,
            "early_stopping_patience": args.early_stopping_patience,
            "early_stopping_min_delta": args.early_stopping_min_delta,
            "flip_prob": args.flip_prob,
            "jitter_brightness": args.jitter_brightness,
            "jitter_contrast": args.jitter_contrast,
            "jitter_saturation": args.jitter_saturation,
            "affine_prob": args.affine_prob,
            "affine_degrees": args.affine_degrees,
            "affine_translate": args.affine_translate,
            "affine_scale_min": args.affine_scale_min,
            "affine_scale_max": args.affine_scale_max,
        },
    }
    torch.save(payload, path)


def append_history(
    path: Path,
    epoch: int,
    metrics: dict,
    best_metric: float,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "epoch",
        "train_loss",
        "train_acc",
        "val_loss",
        "val_acc",
        "macro_f1",
        "best_macro_f1",
        "lr",
    ]
    row = {
        "epoch": epoch + 1,
        "train_loss": metrics["train_loss"],
        "train_acc": metrics["train_acc"],
        "val_loss": metrics["val_loss"],
        "val_acc": metrics["val_acc"],
        "macro_f1": metrics["macro_f1"],
        "best_macro_f1": best_metric,
        "lr": metrics["lr"],
    }
    write_header = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def save_history_plot(history_csv: Path, target: str) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    df = pd.read_csv(history_csv)
    output_path = history_csv.parent / f"{target}_history.png"
    if df.empty:
        return output_path

    fig, axes = plt.subplots(3, 1, figsize=(10, 12), sharex=True)

    axes[0].plot(df["epoch"], df["train_loss"], label="train_loss", marker="o")
    axes[0].plot(df["epoch"], df["val_loss"], label="val_loss", marker="o")
    axes[0].set_ylabel("Loss")
    axes[0].set_title(f"{target} training curves")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    axes[1].plot(df["epoch"], df["train_acc"], label="train_acc", marker="o")
    axes[1].plot(df["epoch"], df["val_acc"], label="val_acc", marker="o")
    axes[1].plot(df["epoch"], df["macro_f1"], label="macro_f1", marker="o")
    axes[1].plot(df["epoch"], df["best_macro_f1"], label="best_macro_f1", linestyle="--")
    axes[1].set_ylabel("Score")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    axes[2].plot(df["epoch"], df["lr"], label="lr", marker="o")
    axes[2].set_xlabel("Epoch")
    axes[2].set_ylabel("Learning Rate")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()

    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def maybe_resume(
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    scheduler: ReduceLROnPlateau,
    resume: str,
    checkpoint_dir: Path,
    target: str,
) -> tuple[int, float, int, int]:
    if not resume:
        return 0, float("-inf"), -1, 0

    resume_path = resolve_resume_path(resume, checkpoint_dir, target)
    if not resume_path.exists():
        raise FileNotFoundError(f"Resume checkpoint not found: {resume_path}")

    checkpoint = torch.load(resume_path, map_location="cpu")
    model.load_state_dict(checkpoint["model_state_dict"])

    optimizer_state = checkpoint.get("optimizer_state_dict")
    if optimizer_state:
        try:
            optimizer.load_state_dict(optimizer_state)
        except ValueError as exc:
            logger.warning("optimizer state load skipped: %s", exc)

    scheduler_state = checkpoint.get("scheduler_state_dict")
    if scheduler_state:
        try:
            scheduler.load_state_dict(scheduler_state)
        except ValueError as exc:
            logger.warning("scheduler state load skipped: %s", exc)

    start_epoch = int(checkpoint.get("epoch", -1)) + 1
    best_metric = float(checkpoint.get("best_macro_f1", float("-inf")))
    best_epoch = int(checkpoint.get("best_epoch", -1))
    epochs_without_improve = int(checkpoint.get("epochs_without_improve", 0))
    logger.info(
        "Resumed from %s at epoch %d (best_macro_f1=%.4f, best_epoch=%d, bad_epochs=%d)",
        resume_path,
        start_epoch,
        best_metric,
        best_epoch + 1 if best_epoch >= 0 else 0,
        epochs_without_improve,
    )
    return start_epoch, best_metric, best_epoch, epochs_without_improve


def train(args: argparse.Namespace) -> None:
    set_seed(args.seed)
    args.checkpoint_dir = resolve_checkpoint_dir(args)
    args.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    train_df = load_csv(args.train_csv, args.target)
    val_df = load_csv(args.val_csv, args.target)
    log_dataset_summary("train", train_df, args.target)
    log_dataset_summary("val", val_df, args.target)

    train_loader, val_loader = build_dataloaders(args, args.target)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("device=%s", device)

    model = get_model(
        num_classes=args.num_classes,
        pretrained=not args.no_pretrained,
        freeze_backbone=args.freeze_backbone,
        dropout_p=args.dropout_p,
    ).to(device)

    trainable_params = [param for param in model.parameters() if param.requires_grad]
    optimizer = torch.optim.AdamW(
        trainable_params,
        lr=args.learning_rate,
        weight_decay=args.weight_decay,
    )
    scheduler = ReduceLROnPlateau(
        optimizer,
        mode="max",
        factor=args.scheduler_factor,
        patience=args.scheduler_patience,
        min_lr=args.scheduler_min_lr,
    )
    criterion, class_weights = build_criterion(args=args, train_df=train_df, device=device)

    latest_path, best_path = checkpoint_paths(args.checkpoint_dir, args.target)
    train_history_path = history_path(args.checkpoint_dir, args.target)
    start_epoch, best_metric, best_epoch, epochs_without_improve = maybe_resume(
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        resume=args.resume,
        checkpoint_dir=args.checkpoint_dir,
        target=args.target,
    )

    logger.info("freeze_backbone=%s", args.freeze_backbone)
    logger.info("dropout_p=%.2f", args.dropout_p)
    logger.info("optimizer=AdamW lr=%.2e weight_decay=%.2e", args.learning_rate, args.weight_decay)
    logger.info("loss=%s label_smoothing=%.2f", args.loss, args.label_smoothing)
    if args.loss == "focal":
        logger.info("focal_gamma=%.2f", args.focal_gamma)
    if class_weights is not None:
        logger.info("class_weights=%s", [round(float(w), 4) for w in class_weights.cpu().tolist()])
    logger.info(
        "scheduler=ReduceLROnPlateau factor=%.2f patience=%d min_lr=%.2e",
        args.scheduler_factor,
        args.scheduler_patience,
        args.scheduler_min_lr,
    )
    logger.info(
        "early_stopping_patience=%d min_delta=%.4g",
        args.early_stopping_patience,
        args.early_stopping_min_delta,
    )
    logger.info("latest checkpoint=%s", latest_path)
    logger.info("best checkpoint=%s", best_path)

    for epoch in range(start_epoch, args.epochs):
        train_loss, train_acc = train_one_epoch(
            model=model,
            loader=train_loader,
            optimizer=optimizer,
            criterion=criterion,
            device=device,
        )
        val_metrics = validate(
            model=model,
            loader=val_loader,
            criterion=criterion,
            device=device,
        )
        metrics = {
            "train_loss": train_loss,
            "train_acc": train_acc,
            **val_metrics,
            "lr": optimizer.param_groups[0]["lr"],
        }

        improved = metrics["macro_f1"] > (best_metric + args.early_stopping_min_delta)
        if improved:
            best_metric = metrics["macro_f1"]
            best_epoch = epoch
            epochs_without_improve = 0
        else:
            epochs_without_improve += 1

        scheduler.step(metrics["macro_f1"])
        metrics["lr"] = optimizer.param_groups[0]["lr"]

        logger.info(
            "epoch %d/%d train_loss=%.4f train_acc=%.4f val_loss=%.4f val_acc=%.4f macro_f1=%.4f lr=%.2e bad_epochs=%d",
            epoch + 1,
            args.epochs,
            metrics["train_loss"],
            metrics["train_acc"],
            metrics["val_loss"],
            metrics["val_acc"],
            metrics["macro_f1"],
            metrics["lr"],
            epochs_without_improve,
        )

        save_checkpoint(
            path=latest_path,
            epoch=epoch,
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
            best_metric=best_metric,
            best_epoch=best_epoch,
            epochs_without_improve=epochs_without_improve,
            args=args,
            metrics=metrics,
        )

        if improved:
            save_checkpoint(
                path=best_path,
                epoch=epoch,
                model=model,
                optimizer=optimizer,
                scheduler=scheduler,
                best_metric=best_metric,
                best_epoch=best_epoch,
                epochs_without_improve=epochs_without_improve,
                args=args,
                metrics=metrics,
            )
            logger.info("best checkpoint updated (macro_f1=%.4f)", best_metric)

        append_history(
            path=train_history_path,
            epoch=epoch,
            metrics=metrics,
            best_metric=best_metric,
        )
        plot_path = save_history_plot(train_history_path, args.target)
        logger.info("saved history plot=%s", plot_path)

        if args.early_stopping_patience > 0 and epochs_without_improve >= args.early_stopping_patience:
            logger.info(
                "early stopping triggered at epoch %d (best_epoch=%d, best_macro_f1=%.4f)",
                epoch + 1,
                best_epoch + 1 if best_epoch >= 0 else 0,
                best_metric,
            )
            break

    summary = {
        "target": args.target,
        "best_macro_f1": best_metric,
        "best_epoch": best_epoch + 1 if best_epoch >= 0 else 0,
        "freeze_backbone": args.freeze_backbone,
        "latest_checkpoint": str(latest_path),
        "best_checkpoint": str(best_path),
        "history_path": str(train_history_path),
        "loss": args.loss,
    }
    logger.info("training summary=%s", json.dumps(summary, ensure_ascii=True))


def main() -> None:
    args = parse_args()
    train(args)


if __name__ == "__main__":
    main()
