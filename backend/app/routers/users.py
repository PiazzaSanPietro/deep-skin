from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserProfileResponse, UserProfileUpdateResponse, UserProfileUpsertRequest
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me/profile",
    response_model=UserProfileResponse,
    summary="내 프로필 조회",
    description=(
        "현재 로그인한 사용자의 프로필 정보를 조회한다. "
        "**Authorization: Bearer access_token 필요**\n\n"
        "피부 타입, 민감성 여부, 알레르기 성분, 선호 제품 타입 등을 확인한다."
    ),
)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = user_service.get_profile(db, current_user.id)
    if profile is None:
        return UserProfileResponse()
    return profile


@router.put(
    "/me/profile",
    response_model=UserProfileUpdateResponse,
    summary="내 프로필 저장/수정",
    description=(
        "사용자 프로필을 저장하거나 수정한다. "
        "**Authorization: Bearer access_token 필요**\n\n"
        "`sensitive`와 `allergy_ingredients`는 추천 생성 시 성분 필터링에 사용된다. "
        "`sensitive=1`이면 민감 피부 주의 성분이 추천에서 제외되고, "
        "`allergy_ingredients`에 등록된 성분도 제외된다."
    ),
)
def update_my_profile(
    request: UserProfileUpsertRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = user_service.upsert_profile(db, current_user.id, request)
    return UserProfileUpdateResponse(
        message="프로필이 저장되었습니다.",
        profile=UserProfileResponse.model_validate(profile),
    )
