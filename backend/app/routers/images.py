from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.image_upload import ImageUploadResponse
from app.services import image_service

router = APIRouter(prefix="/analysis", tags=["images"])


@router.post(
    "/sessions/{session_id}/images",
    response_model=ImageUploadResponse,
    summary="얼굴 이미지 업로드 및 피부 분석",
    description=(
        "얼굴 이미지를 업로드하면 AI 모델이 부위별 피부 상태를 분석합니다. "
        "실제 서비스에서는 file만 필수이며, angle과 facepart는 AI 모델이 자동으로 판단합니다."
    ),
)
async def upload_image(
    session_id: int,
    file: UploadFile = File(..., description="분석할 얼굴 이미지 (jpg, jpeg, png, 최대 10MB)"),
    angle: Optional[int] = Form(
        None,
        description="[개발/테스트용] 촬영 각도 메타데이터. 실제 서비스에서는 AI 모델이 판단한다.",
    ),
    facepart: Optional[int] = Form(
        None,
        description="[개발/테스트용] 얼굴 부위 메타데이터. 실제 서비스에서는 AI 모델이 bbox/crop 결과로 판단한다.",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await image_service.upload_image(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
        file=file,
        angle=angle,
        facepart=facepart,
    )
