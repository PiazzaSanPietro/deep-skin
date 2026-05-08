from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.recommendation import RecommendationsResponse
from app.services import recommendation_service

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get(
    "/sessions/{session_id}",
    response_model=RecommendationsResponse,
    summary="추천 결과 조회",
    description=(
        "분석 세션의 부위별 추천 결과를 조회한다. "
        "**Authorization: Bearer access_token 필요**\n\n"
        "`recommendation_rules` 기반 rule-based 추천 결과를 반환한다.\n\n"
        "- `issue_type`은 `pore`, `wrinkle`, `dryness` 등 지표명만 사용한다.\n"
        "- `severity`는 `normal` / `mild` / `moderate` / `severe`로 구분한다.\n"
        "- `excluded_ingredients`의 `reason_type`: "
        "`allergy`(사용자 알레르기 성분), `sensitive`(민감 피부 주의 성분)."
    ),
)
def get_recommendations(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return recommendation_service.get_recommendations(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
    )
