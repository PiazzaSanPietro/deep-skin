from sqlalchemy.orm import Session

from app.core.exceptions import session_not_found
from app.models.analysis_session import AnalysisSession
from app.models.skin_metric_value import SkinMetricValue
from app.schemas.metrics import MetricItem, MetricsResponse, PartMetrics


def get_metrics(db: Session, session_id: int, user_id: int) -> MetricsResponse:
    session = db.get(AnalysisSession, session_id)
    if session is None or session.user_id != user_id:
        raise session_not_found()

    rows = (
        db.query(SkinMetricValue)
        .filter(SkinMetricValue.session_id == session_id)
        .order_by(
            SkinMetricValue.facepart.asc(),
            SkinMetricValue.metric_group.asc(),
            SkinMetricValue.metric_name.asc(),
            SkinMetricValue.metric_key.asc(),
        )
        .all()
    )

    # facepart 순으로 삽입된 순서를 보존하며 부위별 그룹핑
    parts_map: dict[str, dict] = {}
    for row in rows:
        key = row.raw_part_name
        if key not in parts_map:
            parts_map[key] = {
                "raw_part_name": row.raw_part_name,
                "display_part_name": row.display_part_name,
                "facepart": row.facepart,
                "metrics": [],
            }
        parts_map[key]["metrics"].append(
            MetricItem(
                metric_group=row.metric_group,
                metric_name=row.metric_name,
                metric_key=row.metric_key,
                value=row.value,
                value_type=row.value_type,
                unit=row.unit,
                is_dummy=row.is_dummy,
                dummy_reason=row.dummy_reason,
                source=row.source,
            )
        )

    sorted_parts = sorted(parts_map.values(), key=lambda p: p["facepart"])

    return MetricsResponse(
        session_id=session_id,
        parts=[
            PartMetrics(
                raw_part_name=p["raw_part_name"],
                display_part_name=p["display_part_name"],
                facepart=p["facepart"],
                metrics=p["metrics"],
            )
            for p in sorted_parts
        ],
    )
