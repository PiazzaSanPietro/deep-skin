from typing import Optional

from pydantic import BaseModel


class MetricItem(BaseModel):
    metric_group: str
    metric_name: str
    metric_key: str
    value: float
    value_type: str
    unit: Optional[str] = None
    is_dummy: bool
    dummy_reason: Optional[str] = None
    source: str


class PartMetrics(BaseModel):
    raw_part_name: str
    display_part_name: str
    facepart: int
    metrics: list[MetricItem]


class MetricsResponse(BaseModel):
    session_id: int
    parts: list[PartMetrics]


class TrendPoint(BaseModel):
    session_id: int
    analyzed_at: str
    value: float


class TrendsResponse(BaseModel):
    raw_part_name: str
    display_part_name: Optional[str] = None
    metric_group: str
    metric_name: str
    metric_key: Optional[str] = None
    trend: list[TrendPoint]
