from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.analysis_session import AnalysisSession
from app.models.skin_metric_value import SkinMetricValue
from app.schemas.metrics import TrendPoint, TrendsResponse


def get_trends(
    db: Session,
    user_id: int,
    raw_part_name: str,
    metric_group: str,
    metric_name: str,
    limit: int = 10,
) -> TrendsResponse:
    """현재 사용자의 특정 부위/지표 추이를 최근 limit개 반환 (시간 오름차순).

    - status=completed 세션만 포함
    - is_dummy=False metric만 포함
    - analyzed_at IS NULL이면 created_at으로 대체
    """
    sort_col = func.coalesce(AnalysisSession.analyzed_at, AnalysisSession.created_at)

    rows = (
        db.query(SkinMetricValue, AnalysisSession)
        .join(AnalysisSession, SkinMetricValue.session_id == AnalysisSession.id)
        .filter(
            AnalysisSession.user_id == user_id,
            AnalysisSession.status == "completed",
            SkinMetricValue.raw_part_name == raw_part_name,
            SkinMetricValue.metric_group == metric_group,
            SkinMetricValue.metric_name == metric_name,
            SkinMetricValue.is_dummy == False,  # noqa: E712
        )
        .order_by(sort_col.desc())
        .limit(limit)
        .all()
    )

    # ascending for graph display
    rows.sort(key=lambda r: r[1].analyzed_at or r[1].created_at)

    display_part_name = rows[0][0].display_part_name if rows else None
    metric_key = rows[0][0].metric_key if rows else None

    trend = [
        TrendPoint(
            session_id=smv.session_id,
            analyzed_at=(session.analyzed_at or session.created_at).isoformat(),
            value=smv.value,
        )
        for smv, session in rows
    ]

    return TrendsResponse(
        raw_part_name=raw_part_name,
        display_part_name=display_part_name,
        metric_group=metric_group,
        metric_name=metric_name,
        metric_key=metric_key,
        trend=trend,
    )
