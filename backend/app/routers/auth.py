from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    SignupRequest,
    SignupResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
    description="사용자 계정을 생성한다. 비밀번호는 bcrypt 해시로 저장된다.",
)
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    return auth_service.signup(db, request)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="로그인",
    description=(
        "이메일과 비밀번호로 로그인한다. 성공 시 `access_token`과 `refresh_token`을 반환한다.\n\n"
        "이후 인증이 필요한 API는 Swagger 우측 상단 **Authorize**에 `access_token`을 입력한 뒤 호출한다."
    ),
)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    return auth_service.login(db, request)


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    summary="Access Token 재발급",
    description=(
        "`refresh_token`을 사용해 새로운 `access_token`을 발급한다.\n\n"
        "사용자가 직접 호출하는 API가 아니라 프론트엔드가 `access_token` 만료 시 내부적으로 호출하는 API다."
    ),
)
def refresh_token(request: TokenRefreshRequest, db: Session = Depends(get_db)):
    return auth_service.refresh_access_token(db, request.refresh_token)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="로그아웃",
    description=(
        "현재 로그인 사용자의 `refresh_token`을 전체 폐기한다. "
        "**Authorization: Bearer access_token 필요**\n\n"
        "실제 프론트엔드에서는 로그아웃 성공 후 저장된 `access_token`과 `refresh_token`을 삭제해야 한다. "
        "Swagger에서는 별도로 Authorize 창의 Logout 버튼을 눌러야 UI에 저장된 토큰이 제거된다."
    ),
)
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    auth_service.logout(db, current_user.id)
    return LogoutResponse()
