"""Inspect training progress from saved checkpoints and history logs."""

import argparse
import csv
import json
from pathlib import Path

import torch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHECKPOINT_ROOT = PROJECT_ROOT / "checkpoints" / "trained"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show the current training status for a saved cheek model run."
    )
    parser.add_argument(
        "--target",
        choices=["pore", "pigmentation"],
        required=True,
        help="Training target to inspect.",
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        default=None,
        help="Run directory to inspect. If omitted, the latest run directory for the target is used.",
    )
    parser.add_argument(
        "--which",
        choices=["latest", "best"],
        default="latest",
        help="Which checkpoint alias to inspect.",
    )
    parser.add_argument(
        "--checkpoint-path",
        type=Path,
        default=None,
        help="Optional explicit checkpoint path.",
    )
    parser.add_argument(
        "--show-history",
        type=int,
        default=5,
        help="How many recent history rows to print.",
    )
    return parser.parse_args()


def resolve_checkpoint_path(
    checkpoint_dir: Path,
    target: str,
    which: str,
    checkpoint_path: Path | None,
) -> Path:
    if checkpoint_path is not None:
        return checkpoint_path
    return checkpoint_dir / f"{target}_{which}.pth"


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
        if not (checkpoint_dir / f"{args.target}_{args.which}.pth").exists():
            try:
                return find_latest_run_dir(checkpoint_dir, args.target, args.which)
            except FileNotFoundError:
                return checkpoint_dir
        return checkpoint_dir

    return find_latest_run_dir(DEFAULT_CHECKPOINT_ROOT / args.target, args.target, args.which)


def read_history(history_csv: Path) -> list[dict]:
    if not history_csv.exists():
        return []
    with open(history_csv, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def format_float(value) -> str:
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def main() -> None:
    args = parse_args()
    checkpoint_dir = resolve_checkpoint_dir(args)
    checkpoint_path = resolve_checkpoint_path(
        checkpoint_dir=checkpoint_dir,
        target=args.target,
        which=args.which,
        checkpoint_path=args.checkpoint_path,
    )
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    epoch = int(checkpoint.get("epoch", -1))
    best_macro_f1 = checkpoint.get("best_macro_f1")
    best_epoch = checkpoint.get("best_epoch")
    epochs_without_improve = checkpoint.get("epochs_without_improve")
    metrics = checkpoint.get("metrics", {})
    config = checkpoint.get("config", {})

    history_csv = checkpoint_dir / f"{args.target}_history.csv"
    history_rows = read_history(history_csv)

    summary = {
        "target": args.target,
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_dir": str(checkpoint_dir),
        "completed_epoch": epoch + 1 if epoch >= 0 else 0,
        "next_epoch": epoch + 2 if epoch >= 0 else 1,
        "best_macro_f1": best_macro_f1,
        "best_epoch": (int(best_epoch) + 1) if best_epoch is not None and int(best_epoch) >= 0 else 0,
        "epochs_without_improve": epochs_without_improve,
        "history_path": str(history_csv),
        "history_rows": len(history_rows),
    }

    print("=== Training Status ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if config:
        print("\n=== Config ===")
        print(json.dumps(config, ensure_ascii=False, indent=2))

    if metrics:
        print("\n=== Latest Metrics ===")
        for key in ["train_loss", "train_acc", "val_loss", "val_acc", "macro_f1", "lr"]:
            if key in metrics:
                print(f"{key}: {format_float(metrics[key])}")

    if history_rows:
        print(f"\n=== Recent History (last {min(args.show_history, len(history_rows))}) ===")
        for row in history_rows[-args.show_history:]:
            print(
                "epoch={epoch} train_loss={train_loss} train_acc={train_acc} "
                "val_loss={val_loss} val_acc={val_acc} macro_f1={macro_f1} "
                "best_macro_f1={best_macro_f1}".format(
                    epoch=row.get("epoch", ""),
                    train_loss=format_float(row.get("train_loss", "")),
                    train_acc=format_float(row.get("train_acc", "")),
                    val_loss=format_float(row.get("val_loss", "")),
                    val_acc=format_float(row.get("val_acc", "")),
                    macro_f1=format_float(row.get("macro_f1", "")),
                    best_macro_f1=format_float(row.get("best_macro_f1", "")),
                )
            )
    else:
        print("\n=== Recent History ===")
        print("No history CSV found yet.")


if __name__ == "__main__":
    main()
