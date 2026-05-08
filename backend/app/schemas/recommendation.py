from typing import Optional

from pydantic import BaseModel


class IngredientItem(BaseModel):
    key: str
    name: str


class ExcludedIngredientItem(BaseModel):
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
    session_id: int
    recommendations: list[RecommendationItem]
