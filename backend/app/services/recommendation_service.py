from sqlalchemy.orm import Session

from app.core.exceptions import session_access_denied, session_not_found
from app.models.analysis_session import AnalysisSession
from app.models.ingredient_rule import IngredientRule
from app.models.part_recommendation import PartRecommendation
from app.models.recommendation_rule import RecommendationRule
from app.models.skin_part_result import SkinPartResult
from app.models.user_profile import UserProfile
from app.schemas.recommendation import (
    ExcludedIngredientItem,
    IngredientItem,
    RecommendationItem,
    RecommendationsResponse,
)

_SEVERITY_ORDER = {"normal": 0, "mild": 1, "moderate": 2, "severe": 3}


def generate_and_save(db: Session, session_id: int, user_id: int) -> None:
    """skin_part_results 기반으로 추천 생성 후 part_recommendations에 저장 (멱등)."""
    db.query(PartRecommendation).filter(
        PartRecommendation.session_id == session_id
    ).delete(synchronize_session=False)

    results = (
        db.query(SkinPartResult)
        .filter(SkinPartResult.session_id == session_id)
        .all()
    )

    profile = (
        db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    )
    allergy_keys: set[str] = set(profile.allergy_ingredients or []) if profile else set()
    is_sensitive = bool(profile and profile.sensitive == 1)

    caution_keys: set[str] = set()
    if is_sensitive:
        caution_keys = {
            r.ingredient_name
            for r in db.query(IngredientRule)
            .filter(IngredientRule.caution_for_sensitive == True)
            .all()
        }

    # (display_part_name, issue_type) → 가장 높은 severity
    worst: dict[tuple[str, str], str] = {}
    for r in results:
        key = (r.display_part_name, r.issue_type)
        if key not in worst or _SEVERITY_ORDER.get(r.severity, 0) > _SEVERITY_ORDER.get(worst[key], 0):
            worst[key] = r.severity

    to_add: list[PartRecommendation] = []

    for (display_part_name, issue_type), severity in worst.items():
        rule = (
            db.query(RecommendationRule)
            .filter(
                RecommendationRule.display_part_name == display_part_name,
                RecommendationRule.issue_type == issue_type,
                RecommendationRule.severity == severity,
                RecommendationRule.is_active == True,
            )
            .first()
        )
        if not rule:
            continue

        kept, excluded, exclusion_reason = _filter_ingredients(
            rule.recommend_ingredients or [], allergy_keys, caution_keys
        )

        to_add.append(
            PartRecommendation(
                session_id=session_id,
                user_id=user_id,
                rule_id=rule.id,
                display_part_name=display_part_name,
                issue_type=issue_type,
                issue_display_name=rule.issue_display_name,
                severity=severity,
                reason=rule.reason_template,
                recommend_categories=rule.recommend_categories,
                recommend_ingredients=kept,
                excluded_ingredients=excluded,
                exclusion_reason=exclusion_reason,
                care_tips=rule.care_tips,
            )
        )

    # 민감성 피부 추가 추천
    if is_sensitive:
        sensitive_rule = (
            db.query(RecommendationRule)
            .filter(
                RecommendationRule.display_part_name == "전체 얼굴",
                RecommendationRule.issue_type == "sensitive",
                RecommendationRule.severity == "moderate",
                RecommendationRule.is_active == True,
            )
            .first()
        )
        if sensitive_rule:
            to_add.append(
                PartRecommendation(
                    session_id=session_id,
                    user_id=user_id,
                    rule_id=sensitive_rule.id,
                    display_part_name="전체 얼굴",
                    issue_type="sensitive",
                    issue_display_name="민감 피부",
                    severity="moderate",
                    reason=sensitive_rule.reason_template,
                    recommend_categories=sensitive_rule.recommend_categories,
                    recommend_ingredients=sensitive_rule.recommend_ingredients or [],
                    excluded_ingredients=[],
                    exclusion_reason=None,
                    care_tips=sensitive_rule.care_tips,
                )
            )

    db.add_all(to_add)
    db.commit()


def get_recommendations(
    db: Session, session_id: int, user_id: int
) -> RecommendationsResponse:
    session = db.get(AnalysisSession, session_id)
    if session is None:
        raise session_not_found()
    if session.user_id != user_id:
        raise session_access_denied()

    recs = (
        db.query(PartRecommendation)
        .filter(PartRecommendation.session_id == session_id)
        .all()
    )

    # 저장된 추천이 없고 세션이 완료 상태면 지연 생성
    if not recs and session.status == "completed":
        generate_and_save(db, session_id, user_id)
        recs = (
            db.query(PartRecommendation)
            .filter(PartRecommendation.session_id == session_id)
            .all()
        )

    return RecommendationsResponse(
        session_id=session_id,
        recommendations=[_to_item(r) for r in recs],
    )


def _to_item(r: PartRecommendation) -> RecommendationItem:
    return RecommendationItem(
        display_part_name=r.display_part_name,
        issue_type=r.issue_type,
        issue_display_name=r.issue_display_name,
        severity=r.severity,
        reason=r.reason,
        recommend_categories=r.recommend_categories or [],
        recommend_ingredients=[
            IngredientItem(**ing) for ing in (r.recommend_ingredients or [])
        ],
        excluded_ingredients=[
            ExcludedIngredientItem(**ing) for ing in (r.excluded_ingredients or [])
        ],
        exclusion_reason=r.exclusion_reason,
        care_tips=r.care_tips or [],
    )


def _filter_ingredients(
    ingredients: list[dict],
    allergy_keys: set[str],
    caution_keys: set[str],
) -> tuple[list[dict], list[dict], str | None]:
    kept, allergy_excluded, caution_excluded = [], [], []

    for ing in ingredients:
        key = ing.get("key", "")
        if key in allergy_keys:
            allergy_excluded.append({**ing, "reason_type": "allergy"})
        elif key in caution_keys:
            caution_excluded.append({**ing, "reason_type": "sensitive"})
        else:
            kept.append(ing)

    excluded = allergy_excluded + caution_excluded
    if not excluded:
        return kept, [], None

    reasons = []
    if allergy_excluded:
        reasons.append("사용자가 피해야 할 성분으로 등록된 성분이 제외되었습니다.")
    if caution_excluded:
        reasons.append("민감 피부 주의 성분이 제외되었습니다.")

    return kept, excluded, " ".join(reasons)
