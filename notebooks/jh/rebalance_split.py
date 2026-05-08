"""Rebuild train/val metadata CSVs with an ID-grouped, label-aware split."""

import argparse
import json
import logging
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LABEL_COLS = ["pore_label", "pigmentation_label"]
CLASS_RANGE = range(6)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebalance train/val metadata split while keeping person IDs isolated."
    )
    parser.add_argument(
        "--train-csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "cheek_train_metadata.csv",
    )
    parser.add_argument(
        "--val-csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "cheek_val_metadata.csv",
    )
    parser.add_argument(
        "--output-train-csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "cheek_train_metadata.csv",
    )
    parser.add_argument(
        "--output-val-csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "cheek_val_metadata.csv",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "backups",
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=None,
        help="Optional validation ratio. Defaults to the current ratio from input CSVs.",
    )
    return parser.parse_args()


def load_combined_df(train_csv: Path, val_csv: Path) -> tuple[pd.DataFrame, float]:
    train_df = pd.read_csv(train_csv)
    val_df = pd.read_csv(val_csv)
    train_df["source_split"] = "train"
    val_df["source_split"] = "val"

    total_rows = len(train_df) + len(val_df)
    val_ratio = len(val_df) / total_rows if total_rows else 0.1

    combined = pd.concat([train_df, val_df], ignore_index=True)
    combined["id"] = combined["id"].astype(str)
    return combined, val_ratio


def build_group_stats(df: pd.DataFrame) -> dict[str, dict]:
    groups: dict[str, dict] = {}
    for group_id, group_df in df.groupby("id", sort=False):
        stats = {
            "size": len(group_df),
            "rows": group_df.index.to_list(),
        }
        for label_col in LABEL_COLS:
            counts = (
                group_df[label_col]
                .value_counts()
                .reindex(CLASS_RANGE, fill_value=0)
                .sort_index()
                .to_numpy(dtype=np.int64)
            )
            stats[label_col] = counts
        groups[group_id] = stats
    return groups


def compute_overall_counts(df: pd.DataFrame) -> dict[str, np.ndarray]:
    totals: dict[str, np.ndarray] = {}
    for label_col in LABEL_COLS:
        totals[label_col] = (
            df[label_col]
            .value_counts()
            .reindex(CLASS_RANGE, fill_value=0)
            .sort_index()
            .to_numpy(dtype=np.int64)
        )
    return totals


def select_seed_groups(
    groups: dict[str, dict],
    overall_counts: dict[str, np.ndarray],
) -> set[str]:
    selected: set[str] = set()
    covered = {label_col: np.zeros(len(CLASS_RANGE), dtype=np.int64) for label_col in LABEL_COLS}

    # Prefer groups that help cover rare classes first.
    for label_col in LABEL_COLS:
        rare_classes = sorted(
            [cls for cls in CLASS_RANGE if overall_counts[label_col][cls] > 0],
            key=lambda cls: overall_counts[label_col][cls],
        )
        for cls in rare_classes:
            if covered[label_col][cls] > 0:
                continue
            candidates = [
                (group_id, stats)
                for group_id, stats in groups.items()
                if group_id not in selected and stats[label_col][cls] > 0
            ]
            if not candidates:
                continue

            def seed_score(item: tuple[str, dict]) -> tuple[float, float, int]:
                _, stats = item
                rare_gain = sum(
                    stats[col][c]
                    for col in LABEL_COLS
                    for c in CLASS_RANGE
                    if overall_counts[col][c] > 0 and covered[col][c] == 0 and stats[col][c] > 0
                )
                target_hits = stats[label_col][cls]
                return (rare_gain, target_hits, -stats["size"])

            best_group_id, best_stats = max(candidates, key=seed_score)
            selected.add(best_group_id)
            for col in LABEL_COLS:
                covered[col] += best_stats[col]

    return selected


def score_candidate(
    current_counts: dict[str, np.ndarray],
    current_size: int,
    candidate_stats: dict,
    overall_counts: dict[str, np.ndarray],
    target_val_size: int,
) -> float:
    projected_size = current_size + candidate_stats["size"]
    if projected_size <= 0:
        return float("inf")

    score = 0.0
    for label_col in LABEL_COLS:
        overall_total = overall_counts[label_col].sum()
        overall_ratio = overall_counts[label_col] / overall_total
        projected_counts = current_counts[label_col] + candidate_stats[label_col]
        projected_ratio = projected_counts / projected_counts.sum()
        score += float(np.abs(projected_ratio - overall_ratio).sum())

    size_penalty = abs(projected_size - target_val_size) / max(target_val_size, 1)
    # Slightly prefer smaller groups when quality is tied.
    compact_penalty = candidate_stats["size"] / max(target_val_size, 1)
    return score + (0.35 * size_penalty) + (0.05 * compact_penalty)


def assign_group_stratified_split(df: pd.DataFrame, val_ratio: float) -> dict[str, str]:
    groups = build_group_stats(df)
    overall_counts = compute_overall_counts(df)
    total_rows = len(df)
    target_val_size = int(round(total_rows * val_ratio))

    selected_val_ids = select_seed_groups(groups, overall_counts)
    current_counts = {label_col: np.zeros(len(CLASS_RANGE), dtype=np.int64) for label_col in LABEL_COLS}
    current_size = 0
    for group_id in selected_val_ids:
        current_size += groups[group_id]["size"]
        for label_col in LABEL_COLS:
            current_counts[label_col] += groups[group_id][label_col]

    remaining_ids = [group_id for group_id in groups if group_id not in selected_val_ids]
    while current_size < target_val_size and remaining_ids:
        best_group_id = min(
            remaining_ids,
            key=lambda gid: score_candidate(
                current_counts=current_counts,
                current_size=current_size,
                candidate_stats=groups[gid],
                overall_counts=overall_counts,
                target_val_size=target_val_size,
            ),
        )
        selected_val_ids.add(best_group_id)
        current_size += groups[best_group_id]["size"]
        for label_col in LABEL_COLS:
            current_counts[label_col] += groups[best_group_id][label_col]
        remaining_ids.remove(best_group_id)

    split_map = {
        group_id: ("val" if group_id in selected_val_ids else "train")
        for group_id in groups
    }
    return split_map


def summarize_split(df: pd.DataFrame, name: str) -> dict:
    summary = {
        "rows": len(df),
        "ids": int(df["id"].nunique()),
    }
    for label_col in LABEL_COLS:
        summary[label_col] = (
            df[label_col]
            .value_counts()
            .reindex(CLASS_RANGE, fill_value=0)
            .sort_index()
            .to_dict()
        )
    return {name: summary}


def backup_if_needed(src: Path, backup_dir: Path) -> None:
    if not src.exists():
        return
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = backup_dir / f"{src.stem}_{timestamp}{src.suffix}"
    shutil.copy2(src, dst)
    logger.info("backup saved: %s", dst)


def save_split_dfs(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    output_train_csv: Path,
    output_val_csv: Path,
    backup_dir: Path,
) -> None:
    backup_if_needed(output_train_csv, backup_dir)
    backup_if_needed(output_val_csv, backup_dir)
    output_train_csv.parent.mkdir(parents=True, exist_ok=True)
    output_val_csv.parent.mkdir(parents=True, exist_ok=True)
    train_df.to_csv(output_train_csv, index=False)
    val_df.to_csv(output_val_csv, index=False)
    logger.info("saved train csv: %s (%d rows)", output_train_csv, len(train_df))
    logger.info("saved val csv: %s (%d rows)", output_val_csv, len(val_df))


def main() -> None:
    args = parse_args()
    combined_df, current_val_ratio = load_combined_df(args.train_csv, args.val_csv)
    val_ratio = args.val_ratio if args.val_ratio is not None else current_val_ratio
    logger.info("combined rows=%d ids=%d val_ratio=%.4f", len(combined_df), combined_df["id"].nunique(), val_ratio)

    split_map = assign_group_stratified_split(combined_df, val_ratio=val_ratio)
    combined_df["split"] = combined_df["id"].map(split_map)

    train_df = combined_df[combined_df["split"] == "train"].copy()
    val_df = combined_df[combined_df["split"] == "val"].copy()

    logger.info(json.dumps(summarize_split(train_df, "train"), ensure_ascii=False, indent=2))
    logger.info(json.dumps(summarize_split(val_df, "val"), ensure_ascii=False, indent=2))

    overlap = set(train_df["id"]) & set(val_df["id"])
    if overlap:
        raise RuntimeError(f"ID leakage detected: {len(overlap)} overlapping IDs")

    save_split_dfs(
        train_df=train_df,
        val_df=val_df,
        output_train_csv=args.output_train_csv,
        output_val_csv=args.output_val_csv,
        backup_dir=args.backup_dir,
    )


if __name__ == "__main__":
    main()
