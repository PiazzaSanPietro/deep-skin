from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.analysis_session import AnalysisSession
from app.models.user import User
from app.schemas.analysis import SessionCreateRequest, SessionCreateResponse
from app.schemas.metrics import MetricsResponse, TrendsResponse
from app.schemas.report import ReportResponse
from app.services import metric_service, metric_trend_service, report_service

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post(
    "/sessions",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="분석 세션 생성",
    description=(
        "피부 분석 1회를 관리하기 위한 세션을 생성한다. "
        "**Authorization: Bearer access_token 필요**\n\n"
        "이미지 업로드(`POST /analysis/sessions/{session_id}/images`) 또는 "
        "개발용 JSON 업로드(`POST /dev/analysis/sessions/{session_id}/json`) 전에 먼저 호출한다."
    ),
)
def create_session(
    request: SessionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = AnalysisSession(
        user_id=current_user.id,
        session_name=request.session_name,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get(
    "/reports/latest",
    response_model=ReportResponse,
    summary="최신 완료 분석 리포트 조회",
    description=(
        "현재 로그인한 사용자 기준 가장 최근 completed 분석 세션을 찾아 "
        "기존 리포트 응답 구조로 반환한다. "
        "session_id를 알 수 없는 재로그인 복구 흐름에서 사용한다."
    ),
)
def get_latest_session_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return report_service.get_latest_report(db, current_user.id)


@router.get(
    "/metrics/trends",
    response_model=TrendsResponse,
    summary="피부 측정값 추이 조회",
    description=(
        "현재 로그인 사용자의 특정 부위/지표에 대한 세션별 측정값 추이를 반환한다.\n\n"
        "**Authorization: Bearer access_token 필요**\n\n"
        "- `status=completed` 세션만 포함한다.\n"
        "- `is_dummy=True` 지표는 제외한다.\n"
        "- 최근 `limit`개를 가져와 시간 오름차순으로 정렬하여 반환한다.\n"
        "- 조건에 맞는 데이터가 없으면 `trend=[]`를 반환한다."
    ),
)
def get_metric_trends(
    raw_part_name: str = Query(..., description="부위 원본명 (예: forehead, left_cheek)"),
    metric_group: str = Query(..., description="지표 그룹 (예: moisture, pore, elasticity)"),
    metric_name: str = Query(..., description="지표명 (예: moisture, pore_count, R2)"),
    limit: int = Query(default=10, ge=1, le=50, description="최대 조회 개수 (기본 10, 최대 50)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return metric_trend_service.get_trends(
        db, current_user.id, raw_part_name, metric_group, metric_name, limit
    )


@router.get(
    "/sessions/{session_id}/metrics",
    response_model=MetricsResponse,
    summary="상세 측정값 조회",
    description=(
        "특정 분석 세션의 `skin_metric_values` 상세 측정값을 부위별로 묶어 반환한다.\n\n"
        "**Authorization: Bearer access_token 필요**\n\n"
        "- `mock` / `remote` flat 모드로 분석한 세션은 `parts=[]`를 반환한다.\n"
        "- dummy 값(예: `chin_moisture`)은 `is_dummy=true`와 함께 포함된다.\n"
        "- 다른 사용자 세션은 404를 반환한다."
    ),
)
def get_session_metrics(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return metric_service.get_metrics(db, session_id, current_user.id)


@router.get(
    "/sessions/{session_id}/report",
    response_model=ReportResponse,
    summary="분석 리포트 조회",
    description=(
        "사용자 화면에 보여줄 최종 피부 분석 리포트를 조회한다. "
        "**Authorization: Bearer access_token 필요**\n\n"
        "`skin_part_results`와 `part_recommendations`를 조합하여 "
        "`overall_summary`와 `part_reports`를 반환한다.\n\n"
        "- `left_cheek`, `right_cheek`은 `display_part_name='볼'` 기준으로 병합된다.\n"
        "- `normal` 상태도 유지 관리 추천이 있으면 리포트에 포함된다.\n"
        "- `main_issues`는 severity 높은 순으로 정렬된다."
    ),
)
def get_session_report(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return report_service.get_report(db, session_id, current_user.id)
