"""Create task-wise balanced metadata for forehead/glabella experiments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from task_config import REGRESSION_TARGETS, get_classification_tasks, map_grade


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "dy_forehead_glabella_train_metadata.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "dy_forehead_glabella_train_balanced_3grade_1000.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-json", type=Path, default=None)
    parser.add_argument("--grade-scheme", choices=["original", "three"], default="three")
    parser.add_argument("--target-per-class", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260511)
    parser.add_argument(
        "--keep-regression",
        action="store_true",
        help="Keep regression targets in duplicated rows. Default blanks them to run a classification-focused balance test.",
    )
    return parser.parse_args()


def mapped_counts(df: pd.DataFrame, column: str, grade_scheme: str, num_classes: int) -> dict[str, int]:
    values = pd.to_numeric(df[column], errors="coerce").dropna().astype(int)
    mapped = values.map(lambda grade: map_grade(int(grade), grade_scheme))
    counts = mapped.value_counts().reindex(range(num_classes), fill_value=0).sort_index()
    return {str(int(label)): int(count) for label, count in counts.items()}


def main() -> None:
    args = parse_args()
    tasks = get_classification_tasks(args.grade_scheme)
    df = pd.read_csv(args.input_csv)
    if "source_row_index" not in df.columns:
        df = df.copy()
        df["source_row_index"] = df.index

    label_columns = [task.column for task in tasks]
    output_parts: list[pd.DataFrame] = []
    task_summaries: list[dict[str, object]] = []

    for task_idx, task in enumerate(tasks):
        task_df = df[df[task.column].notna() & (df[task.column] != "")].copy()
        task_df["mapped_grade_for_balance"] = (
            pd.to_numeric(task_df[task.column], errors="coerce")
            .astype(int)
            .map(lambda grade: map_grade(int(grade), args.grade_scheme))
        )
        original_counts = (
            task_df["mapped_grade_for_balance"]
            .value_counts()
            .reindex(range(task.num_classes), fill_value=0)
            .sort_index()
        )
        target = args.target_per_class
        if target <= 0:
            target = int(original_counts.max())

        sampled_parts: list[pd.DataFrame] = []
        sampled_counts: dict[str, int] = {}
        unique_counts: dict[str, int] = {}
        for grade in range(task.num_classes):
            grade_df = task_df[task_df["mapped_grade_for_balance"] == grade]
            if grade_df.empty:
                sampled_counts[str(grade)] = 0
                unique_counts[str(grade)] = 0
                continue
            replace = len(grade_df) < target
            sampled = grade_df.sample(
                n=target,
                replace=replace,
                random_state=args.seed + (task_idx * 101) + grade,
            ).copy()
            sampled["balance_task"] = task.name
            sampled["balance_grade"] = grade
            sampled["balance_original_count"] = len(grade_df)
            sampled["balance_sampled_with_replacement"] = replace

            for column in label_columns:
                if column != task.column:
                    sampled[column] = pd.NA
            if not args.keep_regression:
                for target_col in REGRESSION_TARGETS:
                    if target_col in sampled.columns:
                        sampled[target_col] = pd.NA

            sampled_parts.append(sampled)
            sampled_counts[str(grade)] = int(len(sampled))
            unique_counts[str(grade)] = int(sampled["source_row_index"].nunique())

        task_balanced = pd.concat(sampled_parts, ignore_index=True)
        output_parts.append(task_balanced)
        task_summaries.append(
            {
                "task": task.name,
                "target_per_class": target,
                "original_counts": {str(int(k)): int(v) for k, v in original_counts.items()},
                "sampled_counts": sampled_counts,
                "unique_source_rows": unique_counts,
            }
        )

    balanced = pd.concat(output_parts, ignore_index=True)
    balanced = balanced.sample(frac=1.0, random_state=args.seed).reset_index(drop=True)
    if "mapped_grade_for_balance" in balanced.columns:
        balanced = balanced.drop(columns=["mapped_grade_for_balance"])

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    balanced.to_csv(args.output_csv, index=False, encoding="utf-8-sig")

    effective_counts = {
        task.name: mapped_counts(balanced, task.column, args.grade_scheme, task.num_classes)
        for task in tasks
    }
    summary = {
        "input_csv": str(args.input_csv),
        "output_csv": str(args.output_csv),
        "grade_scheme": args.grade_scheme,
        "rows": int(len(balanced)),
        "keep_regression": bool(args.keep_regression),
        "task_summaries": task_summaries,
        "effective_label_counts": effective_counts,
    }

    summary_path = args.summary_json or args.output_csv.with_suffix(".summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
