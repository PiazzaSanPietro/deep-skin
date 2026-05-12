"""Unit tests for recommendation_boost_service — all DB-free (pure function + mock)."""
from unittest.mock import MagicMock, patch

import pytest

from app.services.recommendation_boost_service import (
    _add_new_ingredients,
    _add_unique,
    _boost_ingredient_priority,
    _matches_threshold,
    apply_boost,
)
from app.services.recommendation_service import _filter_ingredients


# ── 1. _boost_ingredient_priority ────────────────────────────────────────────


def test_boost_ingredient_priority_moves_to_front():
    ingredients = [
        {"key": "niacinamide", "name": "나이아신아마이드"},
        {"key": "bha", "name": "살리실산"},
        {"key": "zinc_pca", "name": "징크PCA"},
    ]
    result = _boost_ingredient_priority(ingredients, ["bha", "zinc_pca"])
    assert result[0]["key"] == "bha"
    assert result[1]["key"] == "zinc_pca"
    assert result[2]["key"] == "niacinamide"


# ── 2. _add_new_ingredients ───────────────────────────────────────────────────


def test_add_new_ingredients_appends_without_duplicates():
    existing = [
        {"key": "hyaluronic_acid", "name": "히알루론산"},
        {"key": "glycerin", "name": "글리세린"},
    ]
    result = _add_new_ingredients(existing, ["ceramide", "panthenol"])
    keys = [ing["key"] for ing in result]
    assert keys == ["hyaluronic_acid", "glycerin", "ceramide", "panthenol"]


def test_add_new_ingredients_skips_existing_key():
    existing = [{"key": "hyaluronic_acid", "name": "히알루론산"}]
    result = _add_new_ingredients(existing, ["hyaluronic_acid", "ceramide"])
    keys = [ing["key"] for ing in result]
    assert keys == ["hyaluronic_acid", "ceramide"]


# ── 3. _add_unique for categories ────────────────────────────────────────────


def test_add_unique_categories_deduplication():
    existing = ["보습", "진정"]
    result = _add_unique(existing, ["진정", "미백", "보습"])
    assert result == ["보습", "진정", "미백"]


# ── 4. _add_unique for care_tips ─────────────────────────────────────────────


def test_add_unique_care_tips_deduplication():
    existing = ["자외선 차단제를 매일 사용하세요."]
    result = _add_unique(existing, [
        "자외선 차단제를 매일 사용하세요.",
        "충분한 수분 섭취를 권장합니다.",
    ])
    assert result == [
        "자외선 차단제를 매일 사용하세요.",
        "충분한 수분 섭취를 권장합니다.",
    ]


# ── 5. is_dummy=True metric excluded ─────────────────────────────────────────


def test_apply_boost_excludes_dummy_metrics():
    """SkinMetricValue query returns empty when all metrics are dummy."""
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []

    categories = ["보습"]
    ingredients = [{"key": "hyaluronic_acid", "name": "히알루론산"}]
    care_tips = ["충분한 수분 섭취"]

    result = apply_boost(db, session_id=1, display_part_name="이마",
                         categories=categories, ingredients=ingredients, care_tips=care_tips)
    assert result == (categories, ingredients, care_tips)


def test_apply_boost_dummy_vs_real_metric_contrast():
    """Contrast: real metric triggers boost; dummy metric (DB filtered → []) does not."""
    from app.models.metric_recommendation_boost_rule import MetricRecommendationBoostRule
    from app.models.skin_metric_value import SkinMetricValue

    mock_rule = MagicMock()
    mock_rule.id = 99
    mock_rule.boost_ingredients = None
    mock_rule.add_ingredients = ["ceramide"]
    mock_rule.add_categories = None
    mock_rule.add_care_tips = None
    mock_rule.threshold_min = None
    mock_rule.threshold_max = 35.0

    def _make_db(with_metric: bool):
        mock_metric = MagicMock()
        mock_metric.metric_group = "moisture"
        mock_metric.metric_name = "moisture"
        mock_metric.raw_part_name = "forehead"
        mock_metric.value = 25.0

        db = MagicMock()
        metric_q = MagicMock()
        rule_q = MagicMock()

        def side_effect(model):
            if model is SkinMetricValue:
                return metric_q
            return rule_q

        db.query.side_effect = side_effect
        metric_q.filter.return_value.all.return_value = [mock_metric] if with_metric else []
        rule_q.filter.return_value.order_by.return_value.all.return_value = [mock_rule]
        return db

    ingredients = [{"key": "hyaluronic_acid", "name": "히알루론산"}]

    # real metric (is_dummy=False, DB returns it) → ceramide added
    _, ings_real, _ = apply_boost(
        _make_db(with_metric=True), session_id=1, display_part_name="이마",
        categories=[], ingredients=list(ingredients), care_tips=[],
    )
    assert any(i["key"] == "ceramide" for i in ings_real)

    # dummy metric (is_dummy=True filtered out by DB → []) → ceramide NOT added
    _, ings_dummy, _ = apply_boost(
        _make_db(with_metric=False), session_id=1, display_part_name="이마",
        categories=[], ingredients=list(ingredients), care_tips=[],
    )
    assert not any(i["key"] == "ceramide" for i in ings_dummy)


# ── 6. _matches_threshold — threshold not met ────────────────────────────────


def test_matches_threshold_not_met_returns_false():
    rule = MagicMock()
    rule.threshold_min = 40.0
    rule.threshold_max = None
    assert _matches_threshold(rule, 30.0) is False


def test_matches_threshold_met_returns_true():
    rule = MagicMock()
    rule.threshold_min = 20.0
    rule.threshold_max = 50.0
    assert _matches_threshold(rule, 35.0) is True


# ── 7. No matching boost rules → original unchanged ──────────────────────────


def test_apply_boost_no_rules_returns_original():
    """When metric query returns items but rule query returns nothing."""
    mock_metric = MagicMock()
    mock_metric.metric_group = "moisture"
    mock_metric.metric_name = "moisture"
    mock_metric.raw_part_name = "forehead"
    mock_metric.value = 25.0

    db = MagicMock()
    metric_query = MagicMock()
    rule_query = MagicMock()

    def side_effect(model):
        from app.models.skin_metric_value import SkinMetricValue
        from app.models.metric_recommendation_boost_rule import MetricRecommendationBoostRule
        if model is SkinMetricValue:
            return metric_query
        return rule_query

    db.query.side_effect = side_effect
    metric_query.filter.return_value.all.return_value = [mock_metric]
    rule_query.filter.return_value.order_by.return_value.all.return_value = []

    categories = ["보습"]
    ingredients = [{"key": "hyaluronic_acid", "name": "히알루론산"}]
    care_tips = ["충분한 수분 섭취"]

    result_cats, result_ings, result_tips = apply_boost(
        db, session_id=1, display_part_name="이마",
        categories=categories, ingredients=ingredients, care_tips=care_tips,
    )
    assert result_cats == categories
    assert result_ings == ingredients
    assert result_tips == care_tips


# ── 8. Allergy filter applied after boost ────────────────────────────────────


def test_allergy_filter_applied_after_boost():
    """Boost adds ceramide; allergy list includes ceramide → it should be excluded."""
    ingredients_before_boost = [{"key": "niacinamide", "name": "나이아신아마이드"}]
    add_items = ["ceramide"]
    after_boost = _add_new_ingredients(ingredients_before_boost, add_items)
    assert any(i["key"] == "ceramide" for i in after_boost), "ceramide should be added by boost"

    allergy_keys = {"ceramide"}
    caution_keys: set[str] = set()
    kept, excluded, reason = _filter_ingredients(after_boost, allergy_keys, caution_keys)

    kept_keys = [i["key"] for i in kept]
    excluded_keys = [i["key"] for i in excluded]
    assert "ceramide" not in kept_keys
    assert "ceramide" in excluded_keys
    assert "niacinamide" in kept_keys
