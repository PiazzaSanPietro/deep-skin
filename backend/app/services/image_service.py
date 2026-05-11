import io
import uuid
from pathlib import Path

from fastapi import UploadFile
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    image_file_required,
    image_too_large,
    inference_failed,
    invalid_image_extension,
    invalid_image_file,
    invalid_image_type,
    session_access_denied,
    session_not_found,
)
from app.models.analysis_session import AnalysisSession
from app.models.skin_part_result import SkinPartResult
from app.models.uploaded_image import UploadedImage
from app.schemas.image_upload import ImageUploadResponse, InferenceResult
from app.services import inference_service, recommendation_service

_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
_ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}


async def upload_image(
    db: Session,
    session_id: int,
    user_id: int,
    file: UploadFile,
    angle: int | None,
    facepart: int | None,
) -> ImageUploadResponse:
    # 1. 세션 존재 및 소유자 확인
    session = db.get(AnalysisSession, session_id)
    if session is None:
        raise session_not_found()
    if session.user_id != user_id:
        raise session_access_denied()

    # 2. 파일 존재 확인
    if not file or not file.filename:
        raise image_file_required()

    # 3. 확장자 확인
    ext = Path(file.filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise invalid_image_extension()

    # 4. 파일 내용 읽기
    content = await file.read()

    # 5. MIME type 확인
    if file.content_type not in _ALLOWED_MIME_TYPES:
        raise invalid_image_type()

    # 6. 파일 크기 확인
    if len(content) > settings.MAX_IMAGE_SIZE_BYTES:
        raise image_too_large()

    # 7. 이미지 손상 여부 + 크기 확인
    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
        img = Image.open(io.BytesIO(content))  # verify() 후 재오픈 필요
        width, height = img.size
    except Exception:
        raise invalid_image_file()

    # 8. 저장 경로 생성
    stored_filename = f"{uuid.uuid4()}.jpg"
    save_dir = Path(settings.UPLOAD_DIR) / str(user_id) / str(session_id)
    save_dir.mkdir(parents=True, exist_ok=True)
    file_path = save_dir / stored_filename

    # 9. 파일 저장
    file_path.write_bytes(content)

    # 10. DB 저장 — 실패 시 파일 롤백
    try:
        image_record = UploadedImage(
            session_id=session_id,
            user_id=user_id,
            original_filename=file.filename,
            stored_filename=stored_filename,
            file_path=str(file_path),
            content_type=file.content_type or "image/jpeg",
            file_size=len(content),
            width=width,
            height=height,
            angle=angle,
            facepart=facepart,
            upload_status="uploaded",
        )
        db.add(image_record)
        session.status = "processing"
        db.commit()
        db.refresh(image_record)
    except Exception:
        _delete_file(file_path)
        raise

    # 11. Mock 추론 → skin_part_results 저장 → 추천 생성
    try:
        image_record.upload_status = "processing"
        db.commit()

        result: InferenceResult = inference_service.run_inference(
            str(file_path),
            session_id=session_id,
            user_id=user_id,
            image_id=image_record.id,
        )

        # 이 세션의 기존 이미지 기반 결과 삭제 (재업로드 중복 방지)
        db.query(SkinPartResult).filter(
            SkinPartResult.session_id == session_id,
            SkinPartResult.image_id.is_not(None),
        ).delete(synchronize_session=False)

        # inference parts 전체 저장
        for part in result.parts:
            db.add(SkinPartResult(
                session_id=session_id,
                user_id=user_id,
                image_id=image_record.id,
                raw_part_name=part.raw_part_name,
                display_part_name=part.display_part_name,
                metric_name=part.metric_name,
                metric_display_name=part.metric_display_name,
                issue_type=part.issue_type,
                grade_value=part.grade_value,
                predicted_value=part.predicted_value,
                measured_value=part.measured_value,
                severity=part.severity,
                confidence_score=part.confidence_score,
                model_name=result.model_name,
                model_version=result.model_version,
            ))

        image_record.upload_status = "processed"
        session.status = "completed"
        db.commit()

        recommendation_service.generate_and_save(db, session_id, user_id)
    except Exception as exc:
        image_record.upload_status = "failed"
        image_record.failure_reason = str(exc)
        session.status = "failed"
        session.error_message = "모델 추론 중 오류가 발생했습니다."
        db.commit()
        raise inference_failed()

    return ImageUploadResponse(
        image_id=image_record.id,
        session_id=session_id,
        original_filename=image_record.original_filename,
        stored_filename=stored_filename,
        file_path=str(file_path),
        width=width,
        height=height,
        upload_status=image_record.upload_status,
        session_status=session.status,
        inference_result=result,
    )


def _delete_file(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass
