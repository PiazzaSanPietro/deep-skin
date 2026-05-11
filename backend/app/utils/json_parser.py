from dataclasses import dataclass


@dataclass
class ParsedPartResult:
    raw_part_name: str
    display_part_name: str
    metric_name: str
    metric_display_name: str
    issue_type: str
    grade_value: int
    measured_value: float | None
    severity: str


# AI-Hub annotation key → 내부 표준 지표 매핑
_ANNOTATION_MAP: dict[str, dict] = {
    "l_cheek_pore": {
        "raw_part_name": "left_cheek",
        "display_part_name": "볼",
        "metric_name": "pore",
        "metric_display_name": "모공",
        "issue_type": "pore",
    },
    "r_cheek_pore": {
        "raw_part_name": "right_cheek",
        "display_part_name": "볼",
        "metric_name": "pore",
        "metric_display_name": "모공",
        "issue_type": "pore",
    },
    "l_cheek_pigmentation": {
        "raw_part_name": "left_cheek",
        "display_part_name": "볼",
        "metric_name": "pigmentation",
        "metric_display_name": "색소침착",
        "issue_type": "pigmentation",
    },
    "r_cheek_pigmentation": {
        "raw_part_name": "right_cheek",
        "display_part_name": "볼",
        "metric_name": "pigmentation",
        "metric_display_name": "색소침착",
        "issue_type": "pigmentation",
    },
    "forehead_wrinkle": {
        "raw_part_name": "forehead",
        "display_part_name": "이마",
        "metric_name": "wrinkle",
        "metric_display_name": "주름",
        "issue_type": "wrinkle",
    },
    "forehead_pigmentation": {
        "raw_part_name": "forehead",
        "display_part_name": "이마",
        "metric_name": "pigmentation",
        "metric_display_name": "색소침착",
        "issue_type": "pigmentation",
    },
    "glabellus_wrinkle": {
        "raw_part_name": "glabella",
        "display_part_name": "미간",
        "metric_name": "wrinkle",
        "metric_display_name": "주름",
        "issue_type": "wrinkle",
    },
    "l_perocular_wrinkle": {
        "raw_part_name": "left_eye",
        "display_part_name": "눈가",
        "metric_name": "wrinkle",
        "metric_display_name": "주름",
        "issue_type": "wrinkle",
    },
    "r_perocular_wrinkle": {
        "raw_part_name": "right_eye",
        "display_part_name": "눈가",
        "metric_name": "wrinkle",
        "metric_display_name": "주름",
        "issue_type": "wrinkle",
    },
    "lip_dryness": {
        "raw_part_name": "lips",
        "display_part_name": "입술",
        "metric_name": "dryness",
        "metric_display_name": "건조",
        "issue_type": "dryness",
    },
    "chin_sagging": {
        "raw_part_name": "chin",
        "display_part_name": "턱",
        "metric_name": "sagging",
        "metric_display_name": "처짐",
        "issue_type": "sagging",
    },
    "acne": {
        "raw_part_name": "full_face",
        "display_part_name": "전체 얼굴",
        "metric_name": "acne",
        "metric_display_name": "여드름",
        "issue_type": "acne",
    },
}


def grade_to_severity(grade: int) -> str:
    if grade <= 0:
        return "normal"
    if grade == 1:
        return "mild"
    if grade == 2:
        return "moderate"
    return "severe"


def parse_annotations(annotations: dict) -> list[ParsedPartResult]:
    """AI-Hub annotations dict를 내부 표준 지표 목록으로 변환한다. 알 수 없는 key는 무시한다."""
    results = []
    for key, raw_value in annotations.items():
        mapping = _ANNOTATION_MAP.get(key)
        if mapping is None:
            continue
        try:
            raw_float = float(raw_value)
        except (ValueError, TypeError):
            continue
        grade = int(raw_float)
        results.append(
            ParsedPartResult(
                raw_part_name=mapping["raw_part_name"],
                display_part_name=mapping["display_part_name"],
                metric_name=mapping["metric_name"],
                metric_display_name=mapping["metric_display_name"],
                issue_type=mapping["issue_type"],
                grade_value=grade,
                measured_value=raw_float,
                severity=grade_to_severity(grade),
            )
        )
    return results
