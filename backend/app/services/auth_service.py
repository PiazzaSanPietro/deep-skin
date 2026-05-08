from datetime import datetime, timedelta, timezone

from jose import ExpiredSignatureError, JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    email_already_exists,
    inactive_user,
    invalid_credentials,
    invalid_refresh_token,
    refresh_token_expired,
    refresh_token_revoked,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import LoginRequest, SignupRequest


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def signup(db: Session, request: SignupRequest) -> User:
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise email_already_exists()

    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        name=request.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login(db: Session, request: LoginRequest) -> dict:
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise invalid_credentials()
    if not user.is_active:
        raise inactive_user()

    user.last_login_at = _utcnow()
    db.commit()

    access_token = create_access_token(user.id)
    refresh_token_raw = create_refresh_token(user.id)

    rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token_raw),
        expires_at=_utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(rt)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_raw,
        "token_type": "bearer",
    }


def refresh_access_token(db: Session, raw_token: str) -> dict:
    try:
        payload = decode_token(raw_token)
    except ExpiredSignatureError:
        raise refresh_token_expired()
    except JWTError:
        raise invalid_refresh_token()

    if payload.get("type") != "refresh":
        raise invalid_refresh_token()

    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise invalid_refresh_token()

    token_hash = hash_refresh_token(raw_token)
    rt = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.user_id == user_id,
        )
        .first()
    )

    if rt is None:
        raise invalid_refresh_token()
    if rt.revoked_at is not None:
        raise refresh_token_revoked()
    if rt.expires_at < _utcnow():
        raise refresh_token_expired()

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise invalid_refresh_token()

    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


def logout(db: Session, user_id: int) -> None:
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    ).update({"revoked_at": _utcnow()}, synchronize_session=False)
    db.commit()
