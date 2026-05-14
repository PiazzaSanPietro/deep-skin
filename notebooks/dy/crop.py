"""Build forehead and glabella crops from the Korean skin dataset."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image

from task_config import ALL_EQUIPMENT_COLUMNS


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOWNLOAD_ROOT = (
    Path.home()
    / "Downloads"
    / "028.한국인 피부상태 측정 데이터"
    / "3.개방데이터"
    / "1.데이터"
)
DEFAULT_PROJECT_RAW_ROOT = PROJECT_ROOT / "data" / "raw" / "aihub_skin"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
FACEPART_NAME = {1: "forehead", 2: "glabella"}
FACEPART_DISPLAY = {1: "이마", 2: "미간"}
ALLOWED_ANGLES = {0, 1, 2}  # F, Ft, Fb
ALL_ANGLES = set(range(9))
MARGINS = {
    1: (0.05, 0.08),
    2: (0.12, 0.14),
}

BASE_COLUMNS = [
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
    "part_name",
    "display_part_name",
    "bbox",
    "crop_width",
    "crop_height",
    "label_forehead_pigmentation",
    "label_forehead_wrinkle",
    "label_glabella_wrinkle",
]
JSON_COLUMNS = [
    "split",
    "info_json",
    "images_json",
    "annotations_json",
    "equipment_json",
    "raw_json",
]
CSV_COLUMNS = BASE_COLUMNS + list(ALL_EQUIPMENT_COLUMNS) + JSON_COLUMNS
ISSUE_COLUMNS = ["split", "json_path", "reason", "detail"]

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crop forehead/glabella images and build metadata CSV files."
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help=(
            "Dataset root. Accepts either the 028 dataset folder or the inner "
            "'3.개방데이터/1.데이터' folder."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "cropped" / "dy_forehead_glabella",
        help="Directory for cropped images.",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed",
        help="Directory for metadata CSV files.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=PROJECT_ROOT / "results" / "dy_forehead_glabella",
        help="Directory for summaries, issue logs, and crop samples.",
    )
    parser.add_argument("--max-train", type=int, default=None)
    parser.add_argument("--max-val", type=int, default=None)
    parser.add_argument("--save-samples", type=int, default=12)
    parser.add_argument(
        "--include-side-angles",
        action="store_true",
        help="Include side-angle images as well as F/Ft/Fb.",
    )
    parser.add_argument("--min-crop-px", type=int, default=24)
    return parser.parse_args()


def resolve_data_root(data_root: Path | None) -> Path:
    candidates: list[Path] = []
    if data_root is not None:
        candidates.extend(
            [
                data_root,
                data_root / "3.개방데이터" / "1.데이터",
                data_root / "1.데이터",
            ]
        )
    candidates.extend([DEFAULT_DOWNLOAD_ROOT, DEFAULT_PROJECT_RAW_ROOT])

    for candidate in candidates:
        if (candidate / "Training").exists() and (candidate / "Validation").exists():
            return candidate

    checked = "\n".join(str(path) for path in candidates)
    raise FileNotFoundError(f"Dataset root not found. Checked:\n{checked}")


def _split_roots(data_root: Path, split: str) -> tuple[Path, Path]:
    split_dir = "Training" if split == "train" else "Validation"
    label_dir = "TL" if split == "train" else "VL"
    image_dir = "TS" if split == "train" else "VS"
    label_root = data_root / split_dir / "02.라벨링데이터" / label_dir
    image_root = data_root / split_dir / "01.원천데이터" / image_dir
    if not label_root.exists():
        raise FileNotFoundError(f"Missing label root: {label_root}")
    if not image_root.exists():
        raise FileNotFoundError(f"Missing image root: {image_root}")
    return label_root, image_root


def _load_json(json_path: Path) -> dict[str, Any] | None:
    try:
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("JSON parse failed: %s (%s)", json_path, exc)
        return None


def _json_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _build_image_index(image_root: Path) -> dict[str, Path]:
    image_index: dict[str, Path] = {}
    duplicate_count = 0
    for path in image_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if path.name in image_index:
            duplicate_count += 1
            continue
        image_index[path.name] = path
    logger.info(
        "indexed source images=%d under %s (duplicates ignored=%d)",
        len(image_index),
        image_root,
        duplicate_count,
    )
    return image_index


def _normalize_bbox(bbox: list[Any], img_w: int, img_h: int) -> tuple[int, int, int, int]:
    if len(bbox) != 4:
        raise ValueError(f"bbox must have 4 values: {bbox}")
    a, b, c, d = [int(round(float(v))) for v in bbox]
    if c > a and d > b:
        x1, y1, x2, y2 = a, b, c, d
    else:
        x1, y1, x2, y2 = a, b, a + max(1, c), b + max(1, d)
    return (
        max(0, min(img_w, x1)),
        max(0, min(img_h, y1)),
        max(0, min(img_w, x2)),
        max(0, min(img_h, y2)),
    )


def _expand_bbox(
    bbox: list[Any],
    img_w: int,
    img_h: int,
    facepart: int,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = _normalize_bbox(bbox, img_w, img_h)
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)
    margin_x_ratio, margin_y_ratio = MARGINS[facepart]
    margin_x = int(round(width * margin_x_ratio))
    margin_y = int(round(height * margin_y_ratio))
    return (
        max(0, x1 - margin_x),
        max(0, y1 - margin_y),
        min(img_w, x2 + margin_x),
        min(img_h, y2 + margin_y),
    )


def _empty_label_values() -> dict[str, str | int]:
    return {
        "label_forehead_pigmentation": "",
        "label_forehead_wrinkle": "",
        "label_glabella_wrinkle": "",
    }


def _extract_labels(facepart: int, annotations: dict[str, Any]) -> dict[str, str | int] | None:
    labels = _empty_label_values()
    if facepart == 1:
        pigmentation = annotations.get("forehead_pigmentation")
        wrinkle = annotations.get("forehead_wrinkle")
        if pigmentation is None or wrinkle is None:
            return None
        labels["label_forehead_pigmentation"] = int(pigmentation)
        labels["label_forehead_wrinkle"] = int(wrinkle)
    elif facepart == 2:
        wrinkle = annotations.get("glabellus_wrinkle")
        if wrinkle is None:
            return None
        labels["label_glabella_wrinkle"] = int(wrinkle)
    else:
        return None
    return labels


def _equipment_values(equipment: dict[str, Any] | None) -> dict[str, Any]:
    equipment = equipment or {}
    return {column: equipment.get(column, "") for column in ALL_EQUIPMENT_COLUMNS}


def _issue(split: str, json_path: Path, reason: str, detail: str = "") -> dict[str, str]:
    return {
        "split": split,
        "json_path": str(json_path),
        "reason": reason,
        "detail": detail,
    }


def process_json_file(
    json_path: Path,
    image_index: dict[str, Path],
    output_dir: Path,
    split: str,
    allowed_angles: set[int],
    min_crop_px: int,
) -> tuple[str, dict[str, Any] | None, dict[str, str]]:
    data = _load_json(json_path)
    if data is None:
        return "error", None, _issue(split, json_path, "json_parse_failed")

    info = data.get("info") or {}
    images = data.get("images") or {}
    annotations = data.get("annotations") or {}
    equipment = data.get("equipment") or {}

    facepart = images.get("facepart")
    if facepart not in FACEPART_NAME:
        return "skip", None, _issue(split, json_path, "non_target_facepart", str(facepart))

    angle = images.get("angle")
    if angle not in allowed_angles:
        return "skip", None, _issue(split, json_path, "angle_filtered", str(angle))

    bbox = images.get("bbox")
    if not bbox:
        return "error", None, _issue(split, json_path, "missing_bbox")

    labels = _extract_labels(int(facepart), annotations)
    if labels is None:
        return "error", None, _issue(split, json_path, "missing_target_label")

    filename = info.get("filename")
    if not filename:
        return "error", None, _issue(split, json_path, "missing_filename")

    source_path = image_index.get(filename)
    if source_path is None:
        return "error", None, _issue(split, json_path, "missing_source_image", str(filename))

    try:
        image = Image.open(source_path).convert("RGB")
    except Exception as exc:
        return "error", None, _issue(split, json_path, "image_load_failed", str(exc))

    img_w, img_h = image.size
    try:
        x1, y1, x2, y2 = _expand_bbox(bbox, img_w, img_h, int(facepart))
    except ValueError as exc:
        return "error", None, _issue(split, json_path, "invalid_bbox", str(exc))

    if x2 <= x1 or y2 <= y1:
        return "error", None, _issue(split, json_path, "collapsed_bbox")

    crop = image.crop((x1, y1, x2, y2))
    crop_w, crop_h = crop.size
    if crop_w < min_crop_px or crop_h < min_crop_px:
        return "error", None, _issue(
            split,
            json_path,
            "crop_too_small",
            f"width={crop_w}, height={crop_h}",
        )

    part_name = FACEPART_NAME[int(facepart)]
    out_dir = output_dir / split / part_name
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(str(filename)).stem
    subject_id = str(info.get("id", "unknown"))
    out_path = out_dir / f"{subject_id}_{stem}_{part_name}.jpg"
    crop.save(out_path, quality=95)

    row: dict[str, Any] = {
        "image_path": str(out_path),
        "original_image_path": str(source_path),
        "original_filename": filename,
        "json_path": str(json_path),
        "id": subject_id,
        "gender": info.get("gender", ""),
        "age": info.get("age", ""),
        "date": info.get("date", ""),
        "skin_type": info.get("skin_type", ""),
        "sensitive": info.get("sensitive", ""),
        "device": images.get("device", ""),
        "image_width": img_w,
        "image_height": img_h,
        "angle": angle,
        "facepart": facepart,
        "part_name": part_name,
        "display_part_name": FACEPART_DISPLAY[int(facepart)],
        "bbox": str([x1, y1, x2, y2]),
        "crop_width": crop_w,
        "crop_height": crop_h,
        **labels,
        **_equipment_values(equipment),
        "split": split,
        "info_json": _json_text(info),
        "images_json": _json_text(images),
        "annotations_json": _json_text(annotations),
        "equipment_json": _json_text(equipment),
        "raw_json": _json_text(data),
    }
    return "success", row, _issue(split, json_path, "success")


def build_split(
    data_root: Path,
    output_dir: Path,
    split: str,
    allowed_angles: set[int],
    min_crop_px: int,
    max_samples: int | None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, str]]]:
    label_root, image_root = _split_roots(data_root, split)
    json_files = sorted(label_root.rglob("*.json"))
    logger.info("[%s] json files=%d", split, len(json_files))
    image_index = _build_image_index(image_root)

    rows: list[dict[str, Any]] = []
    skips: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    for json_path in json_files:
        status, row, issue = process_json_file(
            json_path=json_path,
            image_index=image_index,
            output_dir=output_dir,
            split=split,
            allowed_angles=allowed_angles,
            min_crop_px=min_crop_px,
        )
        if status == "success":
            rows.append(row or {})
            if max_samples is not None and len(rows) >= max_samples:
                break
        elif status == "skip":
            skips.append(issue)
        else:
            errors.append(issue)

    logger.info("[%s] success=%d skip=%d error=%d", split, len(rows), len(skips), len(errors))
    return rows, skips, errors


def save_csv(rows: list[dict[str, Any]], csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    logger.info("saved %s (%d rows)", csv_path, len(rows))


def save_issue_log(records: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ISSUE_COLUMNS)
        writer.writeheader()
        writer.writerows(records)
    logger.info("saved %s (%d rows)", path, len(records))


def save_samples(rows: list[dict[str, Any]], samples_dir: Path, n: int) -> None:
    samples_dir.mkdir(parents=True, exist_ok=True)
    for row in rows[:n]:
        source = Path(row["image_path"])
        if source.exists():
            shutil.copy2(source, samples_dir / source.name)
    logger.info("saved crop samples: %s", samples_dir)


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "rows": len(rows),
        "parts": dict(Counter(str(row["part_name"]) for row in rows)),
        "angles": dict(Counter(str(row["angle"]) for row in rows)),
    }
    for label_col in [
        "label_forehead_pigmentation",
        "label_forehead_wrinkle",
        "label_glabella_wrinkle",
    ]:
        values = [str(row[label_col]) for row in rows if row.get(label_col) != ""]
        summary[label_col] = dict(Counter(values))
    return summary


def run_dataset_build(
    data_root: Path | None,
    output_dir: Path,
    processed_dir: Path,
    results_dir: Path,
    include_side_angles: bool = False,
    min_crop_px: int = 24,
    max_train: int | None = None,
    max_val: int | None = None,
    sample_count: int = 12,
) -> dict[str, Any]:
    resolved_root = resolve_data_root(data_root)
    allowed_angles = ALL_ANGLES if include_side_angles else ALLOWED_ANGLES
    logger.info("dataset root=%s", resolved_root)
    logger.info("allowed angles=%s", sorted(allowed_angles))

    summary: dict[str, Any] = {
        "data_root": str(resolved_root),
        "output_dir": str(output_dir),
        "processed_dir": str(processed_dir),
        "allowed_angles": sorted(allowed_angles),
    }
    all_skips: list[dict[str, str]] = []
    all_errors: list[dict[str, str]] = []

    for split, max_samples in (("train", max_train), ("val", max_val)):
        rows, skips, errors = build_split(
            data_root=resolved_root,
            output_dir=output_dir,
            split=split,
            allowed_angles=allowed_angles,
            min_crop_px=min_crop_px,
            max_samples=max_samples,
        )
        csv_path = processed_dir / f"dy_forehead_glabella_{split}_metadata.csv"
        save_csv(rows, csv_path)
        if sample_count > 0 and rows:
            save_samples(rows, results_dir / "crop_samples" / split, sample_count)
        summary[split] = {**summarize_rows(rows), "csv_path": str(csv_path)}
        all_skips.extend(skips)
        all_errors.extend(errors)

    if all_skips:
        skip_path = results_dir / "crop_skip_log.csv"
        save_issue_log(all_skips, skip_path)
        summary["skip_log_path"] = str(skip_path)
    if all_errors:
        error_path = results_dir / "crop_error_log.csv"
        save_issue_log(all_errors, error_path)
        summary["error_log_path"] = str(error_path)

    summary_path = results_dir / "crop_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    summary["summary_path"] = str(summary_path)
    return summary


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    args = parse_args()
    summary = run_dataset_build(
        data_root=args.data_root,
        output_dir=args.output_dir,
        processed_dir=args.processed_dir,
        results_dir=args.results_dir,
        include_side_angles=args.include_side_angles,
        min_crop_px=args.min_crop_px,
        max_train=args.max_train,
        max_val=args.max_val,
        sample_count=args.save_samples,
    )
    logger.info("dataset build summary=%s", json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
