"""
metric_recommendation_boost_rules 1차 베타 seed 삽입 스크립트.

근거:
  - moisture: Corneometer 계열 수분 측정값 기반 (low_is_bad)
  - pore_count: 영상 기반 모공 count (high_is_bad)
  - wrinkle Ra/Rmax/Rt/Rz/Rq: 피부 표면 roughness 지표 (high_is_bad)
  - elasticity R2/R7: Cutometer 계열 탄력 지표 (low_is_bad)
  - pigmentation_count: 색소침착 count (high_is_bad, 낮은 priority)
  - acne_count: 여드름 lesion count (high_is_bad)

중복 판단 기준:
  (metric_group, metric_name, raw_part_name, direction, threshold_min, threshold_max)

실행:
    cd backend
    python scripts/seed_metric_boost_rules.py
"""
from __future__ import annotations

import os
import sys

# backend/를 sys.path에 추가
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.db.database import SessionLocal
from app.models.metric_recommendation_boost_rule import MetricRecommendationBoostRule

# ── 1차 베타 seed 정의 ────────────────────────────────────────────────────────
# raw_part_name=None → 모든 부위에 적용
SEEDS = [
    # ── 수분 부족 ──────────────────────────────────────────────────────────────
    {
        "metric_group": "moisture",
        "metric_name": "moisture",
        "raw_part_name": None,
        "direction": "low_is_bad",
        "threshold_min": None,
        "threshold_max": 35.0,
        "boost_ingredients": None,
        "add_ingredients": ["ceramide", "panthenol"],
        "add_categories": None,
        "add_care_tips": "보습 후 장벽 케어 제품을 함께 사용하세요.",
        "priority": 100,
        "is_active": True,
    },
    # ── 모공 ───────────────────────────────────────────────────────────────────
    # zinc_pca는 ingredient_rules 미등록 → add_ingredients 사용 불가.
    # boost_ingredients로만 사용 (기존 recommendation_rules의 pore 추천에 포함됨).
    {
        "metric_group": "pore",
        "metric_name": "pore_count",
        "raw_part_name": None,
        "direction": "high_is_bad",
        "threshold_min": 700.0,
        "threshold_max": None,
        "boost_ingredients": ["bha", "zinc_pca"],
        "add_ingredients": None,
        "add_categories": None,
        "add_care_tips": "피지와 모공 관리를 함께 진행하세요.",
        "priority": 100,
        "is_active": True,
    },
    # ── 주름 Ra ────────────────────────────────────────────────────────────────
    {
        "metric_group": "wrinkle",
        "metric_name": "Ra",
        "raw_part_name": None,
        "direction": "high_is_bad",
        "threshold_min": 25.0,
        "threshold_max": None,
        "boost_ingredients": ["peptide", "adenosine"],
        "add_ingredients": None,
        "add_categories": None,
        "add_care_tips": "눈가 주름은 보습과 탄력 케어를 함께 관리해주세요.",
        "priority": 100,
        "is_active": True,
    },
    # ── 탄력 R2 (1차 베타: ≤ 0.50) ────────────────────────────────────────────
    {
        "metric_group": "elasticity",
        "metric_name": "R2",
        "raw_part_name": None,
        "direction": "low_is_bad",
        "threshold_min": None,
        "threshold_max": 0.50,
        "boost_ingredients": None,
        "add_ingredients": ["peptide", "adenosine"],
        "add_categories": None,
        "add_care_tips": "탄력 저하가 보이는 부위는 탄력 케어와 장벽 케어를 함께 진행해주세요.",
        "priority": 90,
        "is_active": True,
    },
    # ── 탄력 R7 ────────────────────────────────────────────────────────────────
    {
        "metric_group": "elasticity",
        "metric_name": "R7",
        "raw_part_name": None,
        "direction": "low_is_bad",
        "threshold_min": None,
        "threshold_max": 0.35,
        "boost_ingredients": None,
        "add_ingredients": ["peptide", "adenosine"],
        "add_categories": None,
        "add_care_tips": "피부 탄력 회복을 위해 펩타이드와 보습 장벽 케어를 함께 관리해주세요.",
        "priority": 90,
        "is_active": True,
    },
    # ── 주름 Rmax ──────────────────────────────────────────────────────────────
    {
        "metric_group": "wrinkle",
        "metric_name": "Rmax",
        "raw_part_name": None,
        "direction": "high_is_bad",
        "threshold_min": 120.0,
        "threshold_max": None,
        "boost_ingredients": ["peptide", "adenosine"],
        "add_ingredients": None,
        "add_categories": None,
        "add_care_tips": "주름 깊이와 표면 거칠기 관리를 위해 보습과 탄력 케어를 병행해주세요.",
        "priority": 80,
        "is_active": True,
    },
    # ── 주름 Rt ────────────────────────────────────────────────────────────────
    {
        "metric_group": "wrinkle",
        "metric_name": "Rt",
        "raw_part_name": None,
        "direction": "high_is_bad",
        "threshold_min": 120.0,
        "threshold_max": None,
        "boost_ingredients": ["peptide", "adenosine"],
        "add_ingredients": None,
        "add_categories": None,
        "add_care_tips": "주름 깊이와 표면 거칠기 관리를 위해 보습과 탄력 케어를 병행해주세요.",
        "priority": 80,
        "is_active": True,
    },
    # ── 주름 Rz (DB metric_name="Rz", metric_key="..._Rz=Rtm") ───────────────
    {
        "metric_group": "wrinkle",
        "metric_name": "Rz",
        "raw_part_name": None,
        "direction": "high_is_bad",
        "threshold_min": 80.0,
        "threshold_max": None,
        "boost_ingredients": ["peptide", "adenosine"],
        "add_ingredients": None,
        "add_categories": None,
        "add_care_tips": "피부 표면 거칠기 개선을 위해 꾸준한 보습과 탄력 케어를 권장합니다.",
        "priority": 80,
        "is_active": True,
    },
    # ── 주름 Rq ────────────────────────────────────────────────────────────────
    {
        "metric_group": "wrinkle",
        "metric_name": "Rq",
        "raw_part_name": None,
        "direction": "high_is_bad",
        "threshold_min": 18.0,
        "threshold_max": None,
        "boost_ingredients": ["peptide", "adenosine"],
        "add_ingredients": None,
        "add_categories": None,
        "add_care_tips": "주름과 피부 결 관리를 위해 탄력 케어 성분을 함께 고려해주세요.",
        "priority": 80,
        "is_active": True,
    },
    # ── 색소침착 count (낮은 priority — ROI/조명 영향 큼) ─────────────────────
    {
        "metric_group": "pigmentation",
        "metric_name": "pigmentation_count",
        "raw_part_name": None,
        "direction": "high_is_bad",
        "threshold_min": 100.0,
        "threshold_max": None,
        "boost_ingredients": None,
        "add_ingredients": ["niacinamide"],
        "add_categories": None,
        "add_care_tips": "색소침착 관리는 자외선 차단과 톤 케어를 함께 진행해주세요.",
        "priority": 60,
        "is_active": True,
    },
    # ── 여드름 count ───────────────────────────────────────────────────────────
    {
        "metric_group": "acne",
        "metric_name": "acne_count",
        "raw_part_name": None,
        "direction": "high_is_bad",
        "threshold_min": 30.0,
        "threshold_max": None,
        "boost_ingredients": None,
        "add_ingredients": ["bha", "panthenol"],
        "add_categories": None,
        "add_care_tips": "트러블 부위는 자극을 줄이고 피지·진정 관리를 함께 진행해주세요.",
        "priority": 70,
        "is_active": True,
    },
]


def _fingerprint(seed: dict) -> tuple:
    """중복 판단용 키 튜플 반환."""
    return (
        seed["metric_group"],
        seed["metric_name"],
        seed["raw_part_name"],
        seed["direction"],
        seed["threshold_min"],
        seed["threshold_max"],
    )


def run_seed(db) -> tuple[int, int]:
    """seed를 삽입하고 (inserted, skipped) 튜플을 반환한다."""
    existing_rules = db.query(MetricRecommendationBoostRule).all()
    existing_fps = {
        (
            r.metric_group,
            r.metric_name,
            r.raw_part_name,
            r.direction,
            r.threshold_min,
            r.threshold_max,
        )
        for r in existing_rules
    }

    inserted = 0
    skipped = 0
    for seed in SEEDS:
        fp = _fingerprint(seed)
        if fp in existing_fps:
            skipped += 1
            continue
        db.add(MetricRecommendationBoostRule(**seed))
        existing_fps.add(fp)
        inserted += 1

    db.commit()
    return inserted, skipped


def main() -> None:
    db = SessionLocal()
    try:
        inserted, skipped = run_seed(db)
        total = db.query(MetricRecommendationBoostRule).count()
        print(f"[seed] inserted={inserted}  skipped={skipped}  total_in_db={total}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
