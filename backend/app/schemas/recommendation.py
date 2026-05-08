from typing import Optional

from pydantic import BaseModel, ConfigDict


class IngredientItem(BaseModel):
    key: str
    name: str


class ExcludedIngredientItem(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"key": "retinol", "name": "레티놀", "reason_type": "allergy"}
        }
    )

    key: str
    name: str
    reason_type: Optional[str] = None  # "allergy" | "sensitive"


class RecommendationItem(BaseModel):
    display_part_name: str
    issue_type: str
    issue_display_name: str
    severity: str
    reason: str
    recommend_categories: list[str]
    recommend_ingredients: list[IngredientItem]
    excluded_ingredients: list[ExcludedIngredientItem]
    exclusion_reason: Optional[str]
    care_tips: list[str]


class RecommendationsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": 1,
                "recommendations": [
                    {
                        "display_part_name": "볼",
                        "issue_type": "pore",
                        "issue_display_name": "모공",
                        "severity": "moderate",
                        "reason": "볼 부위의 모공 관리가 필요합니다.",
                        "recommend_categories": ["모공 케어 토너", "피지 조절 세럼"],
                        "recommend_ingredients": [
                            {"key": "niacinamide", "name": "나이아신아마이드"},
                            {"key": "zinc_pca", "name": "징크 PCA"},
                        ],
                        "excluded_ingredients": [
                            {"key": "retinol", "name": "레티놀", "reason_type": "allergy"}
                        ],
                        "exclusion_reason": "사용자가 피해야 할 성분으로 등록된 성분이 제외되었습니다.",
                        "care_tips": ["피지 조절과 모공 케어 중심의 제품을 사용하는 것이 좋습니다."],
                    }
                ],
            }
        }
    )

    session_id: int
    recommendations: list[RecommendationItem]
