"""
추천 보정 seed 후보 검증 테스트

운영 DB seed 미삽입 상태에서, 테스트 내에서 직접 생성한
MetricRecommendationBoostRule / SkinMetricValue 객체로
boost 동작을 검증한다. DB 연결 불필요 (순수 mock 기반).

확인 항목:
  1. pore_count >= 700 → bha/zinc_pca 우선순위 상승
  2. moisture <= 35   → ceramide/panthenol 추가
  3. wrinkle Ra >= 25 → peptide/adenosine 우선순위 상승
  4. elasticity R2 <= 0.35 → peptide/adenosine 추가
  5. threshold 불충족 → 원본 유지
  6. is_dummy=True metric → 보정 제외
  7. allergy 성분은 boost 후에도 제거
  8. sensitive caution 성분은 boost 후에도 제거
  9. boost rule 없음 → 원본 유지
 10. 잘못된 rule (비정상 boost_ingredients) → warning + skip, 원본 유지
"""
from unittest.mock import MagicMock

from app.models.metric_recommendation_boost_rule import MetricRecommendationBoostRule
from app.models.skin_metric_value import SkinMetricValue
from app.services.recommendation_boost_service import apply_boost
from app.services.recommendation_service import _filter_ingredients


# ── 공통 헬퍼 ────────────────────────────────────────────────────────────────
# SQLAlchemy ORM 인스턴스는 세션 없이 __new__로 생성하면 속성 설정이 실패한다.
# MagicMock으로 필드를 흉내낸다.


def _make_metric(
    metric_group: str,
    metric_name: str,
    value: float,
    raw_part_name: str = "left_cheek",
    display_part_name: str = "볼",
    is_dummy: bool = False,
) -> MagicMock:
    m = MagicMock(spec=SkinMetricValue)
    m.id = 1
    m.session_id = 1
    m.user_id = 1
    m.image_id = None
    m.part_result_id = None
    m.raw_part_name = raw_part_name
    m.display_part_name = display_part_name
    m.facepart = 3
    m.metric_group = metric_group
    m.metric_name = metric_name
    m.metric_key = f"{raw_part_name}_{metric_group}_{metric_name}"
    m.value = value
    m.value_type = "reg"
    m.unit = None
    m.is_dummy = is_dummy
    m.dummy_reason = None
    m.source = "multivalue_inference"
    return m


def _make_rule(
    rule_id: int,
    metric_group: str,
    metric_name: str,
    direction: str,
    threshold_min=None,
    threshold_max=None,
    boost_ingredients=None,
    add_ingredients=None,
    add_categories=None,
    add_care_tips=None,
    raw_part_name=None,
) -> MagicMock:
    r = MagicMock(spec=MetricRecommendationBoostRule)
    r.id = rule_id
    r.metric_group = metric_group
    r.metric_name = metric_name
    r.raw_part_name = raw_part_name
    r.direction = direction
    r.threshold_min = threshold_min
    r.threshold_max = threshold_max
    r.boost_ingredients = boost_ingredients
    r.add_ingredients = add_ingredients
    r.add_categories = add_categories
    r.add_care_tips = add_care_tips
    r.priority = 0
    r.is_active = True
    return r


def _make_db(metrics: list, rules: list) -> MagicMock:
    db = MagicMock()
    metric_q = MagicMock()
    rule_q = MagicMock()

    metric_q.filter.return_value.all.return_value = metrics
    rule_q.filter.return_value.order_by.return_value.all.return_value = rules

    def _side_effect(model):
        if model is SkinMetricValue:
            return metric_q
        return rule_q

    db.query.side_effect = _side_effect
    return db


# ── 1. pore_count >= 700 → BHA/zinc_pca 우선순위 상승 ────────────────────────


def test_pore_boost_priority_above_threshold():
    metric = _make_metric("pore", "pore_count", 753.0)
    rule = _make_rule(
        1, "pore", "pore_count", "high_is_bad",
        threshold_min=700.0,
        boost_ingredients=["bha", "zinc_pca"],
        add_care_tips="피지와 모공 관리를 함께 진행하세요.",
    )
    ingredients = [
        {"key": "niacinamide", "name": "나이아신아마이드"},
        {"key": "bha", "name": "살리실산"},
        {"key": "zinc_pca", "name": "징크PCA"},
    ]
    _, result, tips = apply_boost(
        _make_db([metric], [rule]),
        session_id=1, display_part_name="볼",
        categories=[], ingredients=ingredients, care_tips=[],
    )
    assert result[0]["key"] == "bha"
    assert result[1]["key"] == "zinc_pca"
    assert result[2]["key"] == "niacinamide"
    assert "피지와 모공 관리를 함께 진행하세요." in tips


# ── 2. moisture <= 35 → ceramide/panthenol 추가 ──────────────────────────────


def test_moisture_add_ingredients_below_threshold():
    metric = _make_metric(
        "moisture", "moisture", 31.2,
        raw_part_name="forehead", display_part_name="이마",
    )
    rule = _make_rule(
        2, "moisture", "moisture", "low_is_bad",
        threshold_max=35.0,
        add_ingredients=["ceramide", "panthenol"],
        add_care_tips="보습 후 장벽 케어 제품을 함께 사용하세요.",
    )
    ingredients = [
        {"key": "hyaluronic_acid", "name": "히알루론산"},
        {"key": "glycerin", "name": "글리세린"},
    ]
    _, result, tips = apply_boost(
        _make_db([metric], [rule]),
        session_id=1, display_part_name="이마",
        categories=[], ingredients=ingredients, care_tips=[],
    )
    keys = [i["key"] for i in result]
    assert keys == ["hyaluronic_acid", "glycerin", "ceramide", "panthenol"]
    assert "보습 후 장벽 케어 제품을 함께 사용하세요." in tips


# ── 3. wrinkle Ra >= 25 → peptide/adenosine 우선순위 상승 ─────────────────────


def test_wrinkle_ra_boost_priority_above_threshold():
    metric = _make_metric(
        "wrinkle", "Ra", 28.5,
        raw_part_name="left_eye", display_part_name="눈가",
    )
    rule = _make_rule(
        3, "wrinkle", "Ra", "high_is_bad",
        threshold_min=25.0,
        boost_ingredients=["peptide", "adenosine"],
        add_care_tips="눈가 주름은 보습과 탄력 케어를 함께 관리해주세요.",
    )
    ingredients = [
        {"key": "retinol", "name": "레티놀"},
        {"key": "adenosine", "name": "아데노신"},
        {"key": "peptide", "name": "펩타이드"},
    ]
    _, result, tips = apply_boost(
        _make_db([metric], [rule]),
        session_id=1, display_part_name="눈가",
        categories=[], ingredients=ingredients, care_tips=[],
    )
    assert result[0]["key"] in {"peptide", "adenosine"}
    assert result[1]["key"] in {"peptide", "adenosine"}
    assert result[2]["key"] == "retinol"
    assert "눈가 주름은 보습과 탄력 케어를 함께 관리해주세요." in tips


# ── 4. elasticity R2 <= 0.35 → peptide/adenosine 추가 ───────────────────────


def test_elasticity_r2_add_ingredients_below_threshold():
    metric = _make_metric(
        "elasticity", "R2", 0.28,
        raw_part_name="forehead", display_part_name="이마",
    )
    rule = _make_rule(
        4, "elasticity", "R2", "low_is_bad",
        threshold_max=0.35,
        add_ingredients=["peptide", "adenosine"],
        add_care_tips="탄력 저하가 보이는 부위는 장벽 케어와 탄력 케어를 병행해주세요.",
    )
    ingredients = [{"key": "niacinamide", "name": "나이아신아마이드"}]
    _, result, tips = apply_boost(
        _make_db([metric], [rule]),
        session_id=1, display_part_name="이마",
        categories=[], ingredients=ingredients, care_tips=[],
    )
    keys = [i["key"] for i in result]
    assert "peptide" in keys
    assert "adenosine" in keys
    assert "niacinamide" in keys
    assert "탄력 저하가 보이는 부위는 장벽 케어와 탄력 케어를 병행해주세요." in tips


# ── 5. threshold 불충족 → 원본 유지 ─────────────────────────────────────────


def test_threshold_not_met_returns_original():
    """pore_count = 500, threshold_min = 700 → threshold 불충족."""
    metric = _make_metric("pore", "pore_count", 500.0)
    rule = _make_rule(
        5, "pore", "pore_count", "high_is_bad",
        threshold_min=700.0,
        boost_ingredients=["bha", "zinc_pca"],
    )
    ingredients = [
        {"key": "niacinamide", "name": "나이아신아마이드"},
        {"key": "bha", "name": "살리실산"},
    ]
    _, result, _ = apply_boost(
        _make_db([metric], [rule]),
        session_id=1, display_part_name="볼",
        categories=[], ingredients=ingredients, care_tips=[],
    )
    assert result[0]["key"] == "niacinamide"
    assert result[1]["key"] == "bha"


# ── 6. is_dummy=True metric → 보정 제외 ──────────────────────────────────────


def test_dummy_metric_excluded_from_boost():
    """is_dummy=True 지표는 apply_boost 내 filter로 제외되어 DB 쿼리 결과 빈 리스트."""
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []

    ingredients = [{"key": "hyaluronic_acid", "name": "히알루론산"}]
    _, result, _ = apply_boost(
        db, session_id=1, display_part_name="이마",
        categories=[], ingredients=ingredients, care_tips=[],
    )
    assert result == ingredients


# ── 7. allergy 성분은 boost 후에도 제거 ──────────────────────────────────────


def test_allergy_ingredient_removed_after_boost():
    """boost로 ceramide 추가 → allergy 목록에 ceramide → excluded."""
    metric = _make_metric(
        "moisture", "moisture", 31.2,
        raw_part_name="forehead", display_part_name="이마",
    )
    rule = _make_rule(
        7, "moisture", "moisture", "low_is_bad",
        threshold_max=35.0,
        add_ingredients=["ceramide", "panthenol"],
    )
    base_ingredients = [{"key": "hyaluronic_acid", "name": "히알루론산"}]

    _, boosted, _ = apply_boost(
        _make_db([metric], [rule]),
        session_id=1, display_part_name="이마",
        categories=[], ingredients=base_ingredients, care_tips=[],
    )

    assert any(i["key"] == "ceramide" for i in boosted), "ceramide이 boost로 추가되어야 함"

    allergy_keys = {"ceramide"}
    kept, excluded, reason = _filter_ingredients(boosted, allergy_keys, set())

    kept_keys = [i["key"] for i in kept]
    excluded_keys = [i["key"] for i in excluded]
    assert "ceramide" not in kept_keys
    assert "ceramide" in excluded_keys
    assert "allergy" in excluded[0].get("reason_type", "")


# ── 8. sensitive caution 성분은 boost 후에도 제거 ────────────────────────────


def test_sensitive_caution_ingredient_removed_after_boost():
    """boost로 peptide 추가 → caution_keys에 peptide → excluded."""
    metric = _make_metric(
        "elasticity", "R2", 0.28,
        raw_part_name="forehead", display_part_name="이마",
    )
    rule = _make_rule(
        8, "elasticity", "R2", "low_is_bad",
        threshold_max=0.35,
        add_ingredients=["peptide"],
    )
    base_ingredients = [{"key": "niacinamide", "name": "나이아신아마이드"}]

    _, boosted, _ = apply_boost(
        _make_db([metric], [rule]),
        session_id=1, display_part_name="이마",
        categories=[], ingredients=base_ingredients, care_tips=[],
    )

    assert any(i["key"] == "peptide" for i in boosted), "peptide이 boost로 추가되어야 함"

    caution_keys = {"peptide"}
    kept, excluded, reason = _filter_ingredients(boosted, set(), caution_keys)

    kept_keys = [i["key"] for i in kept]
    assert "peptide" not in kept_keys
    assert any(i["key"] == "peptide" for i in excluded)
    assert "sensitive" in excluded[0].get("reason_type", "")


# ── 9. boost rule 없음 → 원본 유지 ───────────────────────────────────────────


def test_no_boost_rules_returns_original():
    """metric 존재하지만 매칭 rule이 없으면 원본 반환."""
    metric = _make_metric("pore", "pore_count", 753.0)
    ingredients = [
        {"key": "niacinamide", "name": "나이아신아마이드"},
        {"key": "bha", "name": "살리실산"},
    ]
    _, result, _ = apply_boost(
        _make_db([metric], []),   # rules = []
        session_id=1, display_part_name="볼",
        categories=[], ingredients=ingredients, care_tips=[],
    )
    assert [i["key"] for i in result] == ["niacinamide", "bha"]


# ── 10. 잘못된 rule → warning + skip, 원본 유지 ──────────────────────────────


def test_invalid_rule_skipped_with_warning(caplog):
    """boost_ingredients가 정수 (비정상 JSON) → _apply_single_rule 내 예외 → skip."""
    import logging

    metric = _make_metric("pore", "pore_count", 753.0)

    bad_rule = _make_rule(
        10, "pore", "pore_count", "high_is_bad",
        threshold_min=700.0,
        boost_ingredients=42,   # 비정상: 리스트가 아님
    )

    ingredients = [
        {"key": "niacinamide", "name": "나이아신아마이드"},
        {"key": "bha", "name": "살리실산"},
    ]

    with caplog.at_level(logging.WARNING, logger="app.services.recommendation_boost_service"):
        _, result, _ = apply_boost(
            _make_db([metric], [bad_rule]),
            session_id=1, display_part_name="볼",
            categories=[], ingredients=ingredients, care_tips=[],
        )

    # rule이 skip됐으므로 원본 순서 유지
    assert [i["key"] for i in result] == ["niacinamide", "bha"]
    # warning이 기록됐는지 확인
    assert any("skipped" in r.message for r in caplog.records)
