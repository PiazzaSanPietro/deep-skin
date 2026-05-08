"""Smoke test for cheek crop generation and metadata CSV validation."""

import logging
import sys
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crop import (
    build_cheek_dataset,
    save_crop_samples,
    save_csv,
    save_error_log,
    save_skip_log,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DATA_ROOT = PROJECT_ROOT / "data" / "raw" / "aihub_skin"
OUTPUT_DIR = PROJECT_ROOT / "data" / "cropped" / "test"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "test"
SAMPLES_DIR = PROJECT_ROOT / "results" / "test" / "crop_samples"
SKIP_LOG = PROJECT_ROOT / "results" / "test" / "crop_skip_log.csv"
ERROR_LOG = PROJECT_ROOT / "results" / "test" / "crop_error_log.csv"

MAX_TRAIN = 200
MAX_VAL = 80


def check_csv(csv_path: Path, split: str) -> bool:
    import csv

    required_cols = {
        "image_path",
        "original_image_path",
        "original_filename",
        "json_path",
        "id",
        "gender",
        "age",
        "date",
        "skin_type",
        "sensitive",
        "device",
        "image_width",
        "image_height",
        "angle",
        "facepart",
        "side",
        "bbox",
        "pore_label",
        "pigmentation_label",
        "split",
        "info_json",
        "images_json",
        "annotations_json",
        "equipment_json",
        "raw_json",
    }

    ok = True
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        cols = set(reader.fieldnames or [])

    missing = required_cols - cols
    if missing:
        logger.error("[%s] missing CSV columns: %s", split, sorted(missing))
        ok = False
    else:
        logger.info("[%s] CSV columns OK (%d)", split, len(cols))

    pore_counter: Counter = Counter()
    pig_counter: Counter = Counter()
    path_errors = 0

    for row in rows:
        if not Path(row["image_path"]).exists():
            path_errors += 1

        try:
            pore = int(row["pore_label"])
            pig = int(row["pigmentation_label"])
        except (ValueError, KeyError):
            logger.error("label parse failed: %s", row)
            ok = False
            continue

        if not (0 <= pore <= 5):
            logger.error("invalid pore_label=%d (%s)", pore, row.get("image_path"))
            ok = False
        if not (0 <= pig <= 5):
            logger.error("invalid pigmentation_label=%d (%s)", pig, row.get("image_path"))
            ok = False

        pore_counter[pore] += 1
        pig_counter[pig] += 1

    if path_errors:
        logger.warning("[%s] missing image_path files: %d", split, path_errors)
        ok = False
    else:
        logger.info("[%s] all image paths exist (%d)", split, len(rows))

    logger.info("[%s] pore_label distribution=%s", split, dict(sorted(pore_counter.items())))
    logger.info(
        "[%s] pigmentation_label distribution=%s",
        split,
        dict(sorted(pig_counter.items())),
    )

    return ok


def run_crop_test(split: str, max_samples: int) -> tuple[list[dict], list[dict], list[dict]]:
    logger.info("=" * 60)
    logger.info("[%s] crop smoke test start (max_samples=%d)", split, max_samples)

    rows, skips, errors = build_cheek_dataset(
        data_root=DATA_ROOT,
        output_dir=OUTPUT_DIR,
        split=split,
        max_samples=max_samples,
    )

    if not rows:
        logger.error("[%s] no crop rows produced. check raw data root: %s", split, DATA_ROOT)
        return rows, skips, errors

    l_count = sum(1 for row in rows if row["facepart"] == 5)
    r_count = sum(1 for row in rows if row["facepart"] == 6)
    logger.info("[%s] left=%d right=%d", split, l_count, r_count)

    csv_path = PROCESSED_DIR / f"cheek_{split}_metadata_test.csv"
    save_csv(rows, csv_path)
    save_crop_samples(rows, SAMPLES_DIR / split, n=10)
    return rows, skips, errors


def main() -> None:
    logger.info("project root: %s", PROJECT_ROOT)
    logger.info("data root: %s", DATA_ROOT)

    if not DATA_ROOT.exists():
        logger.error("missing raw dataset root: %s", DATA_ROOT)
        sys.exit(1)

    train_rows, train_skips, train_errors = run_crop_test("train", MAX_TRAIN)
    val_rows, val_skips, val_errors = run_crop_test("val", MAX_VAL)

    all_skips = [*train_skips, *val_skips]
    all_errors = [*train_errors, *val_errors]

    if all_skips:
        save_skip_log(all_skips, SKIP_LOG)
    if all_errors:
        save_error_log(all_errors, ERROR_LOG)

    logger.info("=" * 60)
    logger.info("CSV validation start")

    results = {}
    for split, rows in [("train", train_rows), ("val", val_rows)]:
        if not rows:
            logger.warning("[%s] no rows, skip CSV validation", split)
            results[split] = False
            continue
        csv_path = PROCESSED_DIR / f"cheek_{split}_metadata_test.csv"
        results[split] = check_csv(csv_path, split)

    logger.info("=" * 60)
    logger.info("crop smoke summary")
    logger.info(
        "train: success=%d skip=%d error=%d",
        len(train_rows),
        len(train_skips),
        len(train_errors),
    )
    logger.info(
        "val: success=%d skip=%d error=%d",
        len(val_rows),
        len(val_skips),
        len(val_errors),
    )
    logger.info("train CSV validation=%s", "PASS" if results.get("train") else "FAIL")
    logger.info("val CSV validation=%s", "PASS" if results.get("val") else "FAIL")

    all_pass = all(results.values()) and bool(train_rows) and bool(val_rows)
    if not all_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
