"""Create presentation-ready plots and summaries for DY experiments."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_ROOT = PROJECT_ROOT / "checkpoints" / "trained" / "dy_forehead_glabella"
ASSET_DIR = PROJECT_ROOT / "results" / "dy_forehead_glabella" / "presentation_assets"


def _safe_output_path(output_name: str) -> Path:
    output_path = ASSET_DIR / output_name
    if not output_path.exists():
        return output_path
    try:
        with open(output_path, "ab"):
            pass
        return output_path
    except PermissionError:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return output_path.with_name(f"{output_path.stem}_{stamp}{output_path.suffix}")


def _load_histories() -> dict[str, pd.DataFrame]:
    runs = {
        "baseline_original": CHECKPOINT_ROOT / "dy_resnet50_cuda_full" / "history.csv",
        "regularized_original": CHECKPOINT_ROOT / "dy_resnet50_regularized_v2" / "history.csv",
        "integrated_3grade": CHECKPOINT_ROOT / "dy_resnet50_3grade_v1" / "history.csv",
        "integrated_3grade_ordinal": CHECKPOINT_ROOT / "dy_resnet50_3grade_ordinal_v1" / "history.csv",
    }
    histories = {name: pd.read_csv(path) for name, path in runs.items() if path.exists()}
    for pattern in ("dy_resnet50_3grade*/history.csv", "dy_dinov3*/history.csv"):
        for path in CHECKPOINT_ROOT.glob(pattern):
            histories.setdefault(path.parent.name, pd.read_csv(path))
    return histories


def _best_row(history: pd.DataFrame) -> pd.Series:
    return history.loc[history["val_mean_macro_f1"].idxmax()]


def save_3grade_curves(
    history: pd.DataFrame,
    output_name: str = "07_3grade_training_curves.png",
    title: str = "3-grade integrated ResNet-50 training curve",
) -> Path:
    output_path = _safe_output_path(output_name)
    best = _best_row(history)

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    axes[0].plot(history["epoch"], history["train_loss"], label="train loss", color="#2f6f9f", linewidth=2)
    axes[0].plot(history["epoch"], history["val_loss"], label="val loss", color="#b44c3f", linewidth=2)
    axes[0].set_ylabel("Loss")
    axes[0].grid(alpha=0.25)
    axes[0].legend(frameon=False)

    axes[1].plot(
        history["epoch"],
        history["train_mean_macro_f1"],
        label="train macro F1",
        color="#3b8f5a",
        linewidth=2,
    )
    axes[1].plot(
        history["epoch"],
        history["val_mean_macro_f1"],
        label="val macro F1",
        color="#7f5aa2",
        linewidth=2,
    )
    axes[1].scatter([best["epoch"]], [best["val_mean_macro_f1"]], s=90, color="#111111", zorder=4)
    axes[1].annotate(
        f"best epoch {int(best['epoch'])}\nF1 {best['val_mean_macro_f1']:.3f}",
        xy=(best["epoch"], best["val_mean_macro_f1"]),
        xytext=(0.66, 0.16),
        textcoords="axes fraction",
        arrowprops={"arrowstyle": "->", "color": "#333333"},
        fontsize=10,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#bbbbbb", "alpha": 0.92},
    )
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("Macro F1")
    axes[1].grid(alpha=0.25)
    axes[1].legend(frameon=False)

    fig.suptitle(title, fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path


def save_task_metrics(
    best: pd.Series,
    output_name: str = "08_3grade_task_metrics.png",
    title: str = "Best validation metrics by task (3-grade)",
) -> tuple[Path, list[dict[str, float | str]]]:
    output_path = _safe_output_path(output_name)
    rows: list[dict[str, float | str]] = []
    for task, label in [
        ("forehead_pigmentation", "Forehead pigmentation"),
        ("forehead_wrinkle", "Forehead wrinkle"),
        ("glabella_wrinkle", "Glabella wrinkle"),
    ]:
        rows.append(
            {
                "task": label,
                "Accuracy": float(best[f"val_{task}_acc"]),
                "Macro F1": float(best[f"val_{task}_macro_f1"]),
            }
        )

    metrics_df = pd.DataFrame(rows)
    x = np.arange(len(metrics_df))
    width = 0.34

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.bar(x - width / 2, metrics_df["Accuracy"], width, label="Accuracy", color="#2f6f9f")
    ax.bar(x + width / 2, metrics_df["Macro F1"], width, label="Macro F1", color="#d59b2d")
    ax.set_xticks(x)
    ax.set_xticklabels(metrics_df["task"], rotation=12, ha="right")
    ax.set_ylim(0, 1)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    ax.set_title(title, fontsize=14, fontweight="bold")
    for container in ax.containers:
        ax.bar_label(container, fmt="%.3f", padding=3, fontsize=9)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path, rows


def save_model_comparison(histories: dict[str, pd.DataFrame]) -> Path:
    output_path = _safe_output_path("10_model_comparison_3grade.png")
    run_labels = {
        "baseline_original": "Original labels\nbaseline",
        "regularized_original": "Original labels\nregularized",
        "integrated_3grade": "3-grade labels\nintegrated",
        "integrated_3grade_ordinal": "3-grade labels\nordinal",
    }
    rows = []
    for name, history in histories.items():
        label = run_labels.get(name, name.replace("dy_resnet50_", "").replace("_", "\n"))
        best = _best_row(history)
        rows.append(
            {
                "run": label,
                "best_epoch": int(best["epoch"]),
                "val_mean_macro_f1": float(best["val_mean_macro_f1"]),
                "val_mean_acc": float(best["val_mean_acc"]),
            }
        )

    comparison_df = pd.DataFrame(rows)
    if comparison_df.empty:
        raise FileNotFoundError("No comparable history.csv files found.")
    comparison_df.to_csv(ASSET_DIR / "model_comparison_summary.csv", index=False, encoding="utf-8-sig")

    x = np.arange(len(comparison_df))
    width = 0.34
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.bar(x - width / 2, comparison_df["val_mean_macro_f1"], width, label="Mean Macro F1", color="#5b7f95")
    ax.bar(x + width / 2, comparison_df["val_mean_acc"], width, label="Mean Accuracy", color="#b65d45")
    ax.set_xticks(x)
    ax.set_xticklabels(comparison_df["run"])
    ax.set_ylim(0, 1)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    ax.set_title("Validation performance by experiment", fontsize=14, fontweight="bold")
    ax.text(
        0.02,
        -0.22,
        "Note: 3-grade labels are a grouped service target, so compare as a new target setting.",
        transform=ax.transAxes,
        fontsize=9,
        color="#444444",
    )
    for container in ax.containers:
        ax.bar_label(container, fmt="%.3f", padding=3, fontsize=9)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path


def save_crop_quality() -> Path:
    output_path = _safe_output_path("09_crop_quality_check.png")
    train_df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "dy_forehead_glabella_train_metadata.csv")
    val_df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "dy_forehead_glabella_val_metadata.csv")
    train_df["split"] = "train"
    val_df["split"] = "val"
    crop_df = pd.concat([train_df, val_df], ignore_index=True)
    crop_df["aspect_ratio"] = crop_df["crop_width"] / crop_df["crop_height"].replace(0, np.nan)
    crop_df["too_small_for_224"] = (crop_df["crop_width"] < 224) | (crop_df["crop_height"] < 224)

    summary_rows = []
    for (split, part), group in crop_df.groupby(["split", "part_name"], dropna=False):
        row: dict[str, float | int | str] = {
            "split": str(split),
            "part_name": str(part),
            "count": int(len(group)),
            "too_small_for_224": int(group["too_small_for_224"].sum()),
        }
        for col in ["crop_width", "crop_height", "aspect_ratio"]:
            values = pd.to_numeric(group[col], errors="coerce").dropna()
            row[f"{col}_min"] = float(values.min())
            row[f"{col}_p05"] = float(values.quantile(0.05))
            row[f"{col}_median"] = float(values.median())
            row[f"{col}_p95"] = float(values.quantile(0.95))
            row[f"{col}_max"] = float(values.max())
        summary_rows.append(row)

    pd.DataFrame(summary_rows).to_csv(ASSET_DIR / "crop_quality_report.csv", index=False, encoding="utf-8-sig")

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    colors = {"forehead": "#2f6f9f", "glabella": "#d59b2d"}
    for part, group in crop_df.groupby("part_name"):
        label = str(part)
        axes[0].hist(group["crop_width"], bins=28, alpha=0.62, label=label, color=colors.get(label))
        axes[1].hist(group["crop_height"], bins=28, alpha=0.62, label=label, color=colors.get(label))
        axes[2].hist(group["aspect_ratio"].dropna(), bins=28, alpha=0.62, label=label, color=colors.get(label))
    axes[0].axvline(224, color="#333333", linestyle="--", linewidth=1)
    axes[1].axvline(224, color="#333333", linestyle="--", linewidth=1)
    axes[0].set_title("Crop width")
    axes[1].set_title("Crop height")
    axes[2].set_title("Aspect ratio")
    for ax in axes:
        ax.grid(alpha=0.22)
        ax.legend(frameon=False)
    fig.suptitle("Crop quality check for forehead/glabella", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    histories = _load_histories()
    if not histories:
        raise FileNotFoundError(
            f"No history.csv files found under {CHECKPOINT_ROOT}. "
            "Run notebooks/dy/train.py first."
        )

    primary_name = max(
        histories,
        key=lambda name: float(_best_row(histories[name])["val_mean_macro_f1"]),
    )

    history = histories[primary_name]
    best = _best_row(history)
    is_ordinal = "ordinal" in primary_name
    model_label = "DINOv3" if "dinov3" in primary_name else "ResNet-50"
    curves_path = save_3grade_curves(
        history,
        output_name="11_3grade_ordinal_training_curves.png" if is_ordinal else "07_3grade_training_curves.png",
        title=f"3-grade ordinal {model_label} training curve" if is_ordinal else f"3-grade integrated {model_label} training curve",
    )
    task_path, task_rows = save_task_metrics(
        best,
        output_name="12_3grade_ordinal_task_metrics.png" if is_ordinal else "08_3grade_task_metrics.png",
        title="Best validation metrics by task (3-grade + ordinal)" if is_ordinal else "Best validation metrics by task (3-grade)",
    )
    ordinal_summary = None
    if "integrated_3grade_ordinal" in histories:
        ordinal_history = histories["integrated_3grade_ordinal"]
        ordinal_best = _best_row(ordinal_history)
        ordinal_curves_path = save_3grade_curves(
            ordinal_history,
            output_name="11_3grade_ordinal_training_curves.png",
            title="3-grade ordinal ResNet-50 training curve",
        )
        ordinal_task_path, ordinal_task_rows = save_task_metrics(
            ordinal_best,
            output_name="12_3grade_ordinal_task_metrics.png",
            title="Best validation metrics by task (3-grade + ordinal)",
        )
        ordinal_summary = {
            "run_name": "dy_resnet50_3grade_ordinal_v1",
            "best_epoch": int(ordinal_best["epoch"]),
            "best_val_mean_macro_f1": float(ordinal_best["val_mean_macro_f1"]),
            "best_val_mean_acc": float(ordinal_best["val_mean_acc"]),
            "task_metrics": ordinal_task_rows,
            "artifacts": {
                "history": str(CHECKPOINT_ROOT / "dy_resnet50_3grade_ordinal_v1" / "history.csv"),
                "best_checkpoint": str(CHECKPOINT_ROOT / "dy_resnet50_3grade_ordinal_v1" / "best.pth"),
                "training_curves": str(ordinal_curves_path),
                "task_metrics": str(ordinal_task_path),
            },
        }
    comparison_path = save_model_comparison(histories)
    crop_path = save_crop_quality()

    summary = {
        "run_name": primary_name,
        "grade_scheme": "three",
        "best_epoch": int(best["epoch"]),
        "best_val_mean_macro_f1": float(best["val_mean_macro_f1"]),
        "best_val_mean_acc": float(best["val_mean_acc"]),
        "task_metrics": task_rows,
        "artifacts": {
            "history": str(CHECKPOINT_ROOT / primary_name / "history.csv"),
            "best_checkpoint": str(CHECKPOINT_ROOT / primary_name / "best.pth"),
            "training_curves": str(curves_path),
            "task_metrics": str(task_path),
            "crop_quality": str(crop_path),
            "comparison": str(comparison_path),
        },
    }
    if ordinal_summary is not None:
        summary["ordinal_experiment"] = ordinal_summary
    summary_path = ASSET_DIR / "dy_3grade_training_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
