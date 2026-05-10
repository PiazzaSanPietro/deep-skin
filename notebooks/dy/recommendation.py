"""Rule-based explanations and cosmetic recommendations for model outputs."""

from __future__ import annotations

from typing import Any

from task_config import (
    CLASSIFICATION_TASK_BY_NAME,
    REGRESSION_DISPLAY_NAMES,
    grade_to_severity,
)


RECOMMENDATION_RULES: dict[tuple[str, str, str], dict[str, Any]] = {
    ("forehead", "pigmentation", "normal"): {
        "categories": ["수분 크림", "자외선 차단제"],
        "ingredients": ["히알루론산", "세라마이드", "판테놀"],
        "care_tips": ["현재 톤을 유지하기 위해 낮 시간 자외선 차단을 꾸준히 유지합니다."],
    },
    ("forehead", "pigmentation", "mild"): {
        "categories": ["미백 기능성 세럼", "자외선 차단제", "진정 크림"],
        "ingredients": ["나이아신아마이드", "감초추출물", "판테놀"],
        "care_tips": ["강한 미백 성분보다 저자극 톤 케어를 먼저 적용합니다."],
    },
    ("forehead", "pigmentation", "moderate"): {
        "categories": ["잡티 케어 세럼", "미백 앰플", "자외선 차단제"],
        "ingredients": ["나이아신아마이드", "비타민 C", "알부틴"],
        "care_tips": ["비타민 C 제품은 아침 사용 시 자외선 차단제와 함께 사용합니다."],
    },
    ("forehead", "pigmentation", "severe"): {
        "categories": ["고기능 잡티 케어 세럼", "미백 앰플", "자외선 차단제"],
        "ingredients": ["트라넥사믹애씨드", "알부틴", "감초추출물"],
        "care_tips": ["색소침착이 높게 예측되어 자외선 차단과 미백 케어를 우선합니다."],
    },
    ("forehead", "wrinkle", "normal"): {
        "categories": ["수분 크림", "자외선 차단제"],
        "ingredients": ["히알루론산", "세라마이드", "글리세린"],
        "care_tips": ["건조로 인한 잔주름이 생기지 않도록 보습을 유지합니다."],
    },
    ("forehead", "wrinkle", "mild"): {
        "categories": ["보습 세럼", "탄력 크림", "주름 예방 세럼"],
        "ingredients": ["펩타이드", "아데노신", "히알루론산"],
        "care_tips": ["수분감과 탄력 성분을 함께 사용해 잔주름을 완화합니다."],
    },
    ("forehead", "wrinkle", "moderate"): {
        "categories": ["탄력 세럼", "주름 개선 크림", "보습 크림"],
        "ingredients": ["펩타이드", "아데노신", "바쿠치올"],
        "care_tips": ["주름 개선 성분은 낮은 빈도부터 적용해 자극을 확인합니다."],
    },
    ("forehead", "wrinkle", "severe"): {
        "categories": ["고기능 탄력 크림", "레티놀 또는 바쿠치올 세럼", "자외선 차단제"],
        "ingredients": ["레티놀", "바쿠치올", "펩타이드"],
        "care_tips": ["레티놀은 밤에 소량부터 사용하고 낮에는 자외선 차단을 병행합니다."],
    },
    ("glabella", "wrinkle", "normal"): {
        "categories": ["수분 크림", "자외선 차단제"],
        "ingredients": ["히알루론산", "세라마이드", "글리세린"],
        "care_tips": ["미간 부위는 표정 주름이 누적되기 쉬워 보습을 꾸준히 유지합니다."],
    },
    ("glabella", "wrinkle", "mild"): {
        "categories": ["탄력 세럼", "보습 크림", "주름 예방 세럼"],
        "ingredients": ["펩타이드", "아데노신", "히알루론산"],
        "care_tips": ["미간을 자주 찡그리는 습관을 줄이고 보습막을 유지합니다."],
    },
    ("glabella", "wrinkle", "moderate"): {
        "categories": ["주름 개선 세럼", "탄력 크림", "보습 크림"],
        "ingredients": ["펩타이드", "아데노신", "바쿠치올"],
        "care_tips": ["건조하면 미간 주름이 더 뚜렷해 보일 수 있어 보습을 먼저 보강합니다."],
    },
}

MOISTURE_RULES = [
    (
        45.0,
        "low",
        {
            "categories": ["수분 앰플", "장벽 크림", "보습 마스크"],
            "ingredients": ["히알루론산", "글리세린", "세라마이드", "판테놀"],
            "reason": "이마 수분 예측값이 낮아 보습과 장벽 보강이 필요합니다.",
        },
    ),
    (
        60.0,
        "borderline",
        {
            "categories": ["수분 세럼", "보습 크림"],
            "ingredients": ["히알루론산", "베타글루칸", "판테놀"],
            "reason": "이마 수분 예측값이 중간 구간이라 보습 유지가 중요합니다.",
        },
    ),
]


def part_result(
    task_name: str,
    grade: int,
    confidence: float,
    grade_scheme: str = "original",
) -> dict[str, Any]:
    task = CLASSIFICATION_TASK_BY_NAME[task_name]
    return {
        "raw_part_name": task.part_name,
        "display_part_name": task.display_part_name,
        "metric_name": task.metric_name,
        "metric_display_name": task.metric_display_name,
        "issue_type": task.issue_type,
        "grade_value": int(grade),
        "severity": grade_to_severity(int(grade), grade_scheme=grade_scheme),
        "confidence_score": round(float(confidence), 4),
    }


def recommendation_for_part_result(result: dict[str, Any]) -> dict[str, Any]:
    key = (
        result["raw_part_name"],
        result["issue_type"],
        result["severity"],
    )
    rule = RECOMMENDATION_RULES.get(key, {})
    return {
        "display_part_name": result["display_part_name"],
        "issue_type": result["issue_type"],
        "issue_display_name": result["metric_display_name"],
        "severity": result["severity"],
        "reason": (
            f"{result['display_part_name']} {result['metric_display_name']} "
            f"{result['grade_value']}등급으로 예측되어 {result['severity']} 관리가 필요합니다."
        ),
        "recommend_categories": rule.get("categories", []),
        "recommend_ingredients": rule.get("ingredients", []),
        "care_tips": rule.get("care_tips", []),
    }


def numeric_explanations(regression: dict[str, float]) -> list[dict[str, Any]]:
    explanations: list[dict[str, Any]] = []
    moisture = regression.get("forehead_moisture")
    if moisture is not None:
        for threshold, status, rule in MOISTURE_RULES:
            if moisture < threshold:
                explanations.append(
                    {
                        "target": "forehead_moisture",
                        "display_name": REGRESSION_DISPLAY_NAMES["forehead_moisture"],
                        "value": round(float(moisture), 3),
                        "status": status,
                        "reason": rule["reason"],
                        "recommend_categories": rule["categories"],
                        "recommend_ingredients": rule["ingredients"],
                    }
                )
                break

    for name, value in regression.items():
        if name == "forehead_moisture":
            continue
        if "elasticity" in name:
            explanations.append(
                {
                    "target": name,
                    "display_name": REGRESSION_DISPLAY_NAMES.get(name, name),
                    "value": round(float(value), 3),
                    "status": "evidence",
                    "reason": "탄력 회귀 예측값을 주름 등급 설명의 보조 근거로 사용합니다.",
                }
            )
    return explanations


def build_report(
    classification_predictions: dict[str, dict[str, float | int]],
    regression_predictions: dict[str, float],
    grade_scheme: str = "original",
) -> dict[str, Any]:
    parts = [
        part_result(
            task_name=task_name,
            grade=int(prediction["grade"]),
            confidence=float(prediction["confidence"]),
            grade_scheme=grade_scheme,
        )
        for task_name, prediction in classification_predictions.items()
    ]
    recommendations = [recommendation_for_part_result(result) for result in parts]
    numeric = numeric_explanations(regression_predictions)

    for item in numeric:
        if not item.get("recommend_categories"):
            continue
        recommendations.append(
            {
                "display_part_name": "이마",
                "issue_type": "moisture" if item["target"] == "forehead_moisture" else "elasticity",
                "issue_display_name": item["display_name"],
                "severity": "moderate" if item.get("status") == "low" else "mild",
                "reason": item["reason"],
                "recommend_categories": item.get("recommend_categories", []),
                "recommend_ingredients": item.get("recommend_ingredients", []),
                "care_tips": [],
            }
        )

    return {
        "model_name": "resnet50_forehead_glabella_multitask",
        "model_version": "0.1.0",
        "parts": parts,
        "regression": regression_predictions,
        "explanations": numeric,
        "recommendations": recommendations,
    }
