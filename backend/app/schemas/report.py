from typing import Optional

from pydantic import BaseModel

from app.schemas.recommendation import ExcludedIngredientItem, IngredientItem


class IssueItem(BaseModel):
    metric_name: str
    metric_display_name: str
    issue_type: str
    severity: str
    grade_value: Optional[int]
    reason: Optional[str]


class MainIssue(BaseModel):
    issue_type: str
    severity: str


class OverallSummary(BaseModel):
    status: str
    main_message: str
    main_issues: list[MainIssue]


class RecommendationSummary(BaseModel):
    categories: list[str]
    ingredients: list[IngredientItem]
    excluded_ingredients: list[ExcludedIngredientItem]
    exclusion_reason: Optional[str]
    care_tips: list[str]


class PartReport(BaseModel):
    display_part_name: str
    summary: str
    issues: list[IssueItem]
    recommendation: Optional[RecommendationSummary]


class ReportResponse(BaseModel):
    session_id: int
    status: str
    overall_summary: OverallSummary
    part_reports: list[PartReport]
