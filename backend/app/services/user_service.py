from sqlalchemy.orm import Session

from app.models.user_profile import UserProfile
from app.schemas.user import UserProfileUpsertRequest


def get_profile(db: Session, user_id: int) -> UserProfile | None:
    return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()


def upsert_profile(db: Session, user_id: int, request: UserProfileUpsertRequest) -> UserProfile:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    data = request.model_dump(exclude_unset=True)

    if profile is None:
        profile = UserProfile(user_id=user_id, **data)
        db.add(profile)
    else:
        for field, value in data.items():
            setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile
