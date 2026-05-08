from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.exceptions import inactive_user, invalid_token, not_authenticated
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

http_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise not_authenticated()

    token = credentials.credentials  # "Bearer <token>" 에서 토큰 부분만 추출됨

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise invalid_token()
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise invalid_token()

    user: User | None = db.get(User, user_id)
    if user is None:
        raise invalid_token()
    if not user.is_active:
        raise inactive_user()

    return user
