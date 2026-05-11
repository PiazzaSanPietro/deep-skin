from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.analysis_session import AnalysisSession
from app.models.user import User
from app.schemas.analysis import SessionCreateRequest, SessionCreateResponse
from app.schemas.report import ReportResponse
from app.services import report_service

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
