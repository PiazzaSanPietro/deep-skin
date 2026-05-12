"""Metric-based recommendation boost logic.

Queries SkinMetricValue + MetricRecommendationBoostRule to adjust
(categories, ingredients, care_tips) before allergy/sensitive filtering.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.metric_recommendation_boost_rule import MetricRecommendationBoostRule
from app.models.skin_metric_value import SkinMetricValue

logger = logging.getLogger(__name__)


def apply_boost(
    db: Session,
    session_id: int,
    display_part_name: str,
    categories: list[str],
    ingredients: list[dict],
    care_tips: list[str],
) -> tuple[list[str], list[dict], list[str]]:
    """Apply metric-based boosts to recommendation fields.

    Returns (categories, ingredients, care_tips) — modified in-place copies.
    On any unexpected error the originals are returned unchanged.
    """
    try:
        metrics = (
            db.query(SkinMetricValue)
            .filter(
                SkinMetricValue.session_id == session_id,
                SkinMetricValue.display_part_name == display_part_name,
                SkinMetricValue.is_dummy == False,  # noqa: E712
            )
            .all()
        )
        if not metrics:
            return categories, ingredients, care_tips

        out_categories = list(categories)
        out_ingredients = list(ingredients)
        out_care_tips = list(care_tips)

        seen_rule_ids: set[int] = set()

        for metric in metrics:
            rules = (
                db.query(MetricRecommendationBoostRule)
                .filter(
                    MetricRecommendationBoostRule.metric_group == metric.metric_group,
                    MetricRecommendationBoostRule.metric_name == metric.metric_name,
                    or_(
                        MetricRecommendationBoostRule.raw_part_name == metric.raw_part_name,
                        MetricRecommendationBoostRule.raw_part_name == None,  # noqa: E711
                    ),
                    MetricRecommendationBoostRule.is_active == True,  # noqa: E712
                )
                .order_by(MetricRecommendationBoostRule.priority.desc())
                .all()
            )

            for rule in rules:
                if rule.id in seen_rule_ids:
                    continue
                if not _matches_threshold(rule, metric.value):
                    continue
                seen_rule_ids.add(rule.id)
                try:
                    out_categories, out_ingredients, out_care_tips = _apply_single_rule(
                        rule, out_categories, out_ingredients, out_care_tips
                    )
                except Exception:
                    logger.warning(
                        "boost rule id=%s failed for session=%s part=%s — skipped",
                        rule.id, session_id, display_part_name,
                        exc_info=True,
                    )

        return out_categories, out_ingredients, out_care_tips

    except Exception:
        logger.warning(
            "apply_boost failed for session=%s part=%s — returning original",
            session_id, display_part_name,
            exc_info=True,
        )
        return categories, ingredients, care_tips


# ── helpers ──────────────────────────────────────────────────────────────────


def _matches_threshold(rule: MetricRecommendationBoostRule, value: float) -> bool:
    """Return True when value falls within [threshold_min, threshold_max]."""
    if rule.threshold_min is not None and value < rule.threshold_min:
        return False
    if rule.threshold_max is not None and value > rule.threshold_max:
        return False
    return True


def _apply_single_rule(
    rule: MetricRecommendationBoostRule,
    categories: list[str],
    ingredients: list[dict],
    care_tips: list[str],
) -> tuple[list[str], list[dict], list[str]]:
    out_categories = list(categories)
    out_ingredients = list(ingredients)
    out_care_tips = list(care_tips)

    if rule.boost_ingredients:
        boost_keys = _extract_keys(rule.boost_ingredients)
        out_ingredients = _boost_ingredient_priority(out_ingredients, boost_keys)

    if rule.add_ingredients:
        out_ingredients = _add_new_ingredients(out_ingredients, rule.add_ingredients)

    if rule.add_categories:
        new_cats = _extract_keys(rule.add_categories)
        out_categories = _add_unique(out_categories, new_cats)

    if rule.add_care_tips:
        new_tips = [t.strip() for t in rule.add_care_tips.splitlines() if t.strip()]
        out_care_tips = _add_unique(out_care_tips, new_tips)

    return out_categories, out_ingredients, out_care_tips


def _boost_ingredient_priority(
    ingredients: list[dict], boost_keys: list[str]
) -> list[dict]:
    """Move ingredients whose key appears in boost_keys to the front."""
    boost_set = set(boost_keys)
    priority = [ing for ing in ingredients if ing.get("key") in boost_set]
    rest = [ing for ing in ingredients if ing.get("key") not in boost_set]
    return priority + rest


def _add_new_ingredients(
    ingredients: list[dict], add_items: list[Any]
) -> list[dict]:
    """Append ingredients not already present.

    add_items may contain plain string keys or full {"key": ..., "name": ...} dicts.
    """
    existing_keys = {ing.get("key") for ing in ingredients}
    result = list(ingredients)
    for item in add_items:
        if isinstance(item, dict):
            key = item.get("key", "")
            name = item.get("name", key)
        else:
            key = str(item)
            name = key
        if key and key not in existing_keys:
            result.append({"key": key, "name": name})
            existing_keys.add(key)
    return result


def _add_unique(existing: list[str], new_items: list[str]) -> list[str]:
    """Return existing + new_items, skipping duplicates (case-sensitive)."""
    seen = set(existing)
    result = list(existing)
    for item in new_items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _extract_keys(items: list[Any]) -> list[str]:
    """Extract string keys from a list that may contain strings or dicts."""
    keys = []
    for item in items:
        if isinstance(item, dict):
            k = item.get("key", "")
            if k:
                keys.append(k)
        elif isinstance(item, str) and item:
            keys.append(item)
    return keys
