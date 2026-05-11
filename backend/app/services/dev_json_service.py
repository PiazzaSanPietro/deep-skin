from sqlalchemy.orm import Session

from app.core.exceptions import session_access_denied, session_not_found
from app.models.analysis_session import AnalysisSession
from app.models.skin_json_record import SkinJsonRecord
from app.models.skin_part_result import SkinPartResult
from app.schemas.dev_json import DevJsonUploadRequest, DevJsonUploadResponse
from app.services import recommendation_service
from app.utils.json_parser import parse_annotations


def upload_dev_json(
    db: Session,
    session_id: int,
    user_id: int,
    request: DevJsonUploadRequest,
) -> DevJsonUploadResponse:
    session = db.get(AnalysisSession, session_id)
    if session is None:
        raise session_not_found()
    if session.user_id != user_id:
        raise session_access_denied()

    session.status = "processing"
    db.commit()

    saved_json_count = 0
    created_result_count = 0

    for item in request.json_items:
        bbox = item.images.bbox or []
        bbox_x = bbox[0] if len(bbox) > 0 else None
        bbox_y = bbox[1] if len(bbox) > 1 else None
        bbox_w = bbox[2] if len(bbox) > 2 else None
        bbox_h = bbox[3] if len(bbox) > 3 else None

        json_record = SkinJsonRecord(
            session_id=session_id,
            user_id=user_id,
            filename=item.info.filename,
            raw_subject_id=item.info.id,
            device=item.images.device,
            angle=item.images.angle,
            facepart=item.images.facepart,
            width=item.images.width,
            height=item.images.height,
            bbox_x=bbox_x,
            bbox_y=bbox_y,
            bbox_w=bbox_w,
            bbox_h=bbox_h,
            raw_json=item.model_dump(),
        )
        db.add(json_record)
        db.flush()  # json_record.id 확보
        saved_json_count += 1

        parsed_parts = parse_annotations(item.annotations)
        for part in parsed_parts:
            result = SkinPartResult(
                session_id=session_id,
                user_id=user_id,
                json_record_id=json_record.id,
                raw_part_name=part.raw_part_name,
                display_part_name=part.display_part_name,
                metric_name=part.metric_name,
                metric_display_name=part.metric_display_name,
                grade_value=part.grade_value,
                measured_value=part.measured_value,
                severity=part.severity,
                issue_type=part.issue_type,
                model_name="ai_hub_annotation",
                model_version="1.0",
            )
            db.add(result)
            created_result_count += 1

    session.status = "completed"
    db.commit()

    # 추천 생성
    recommendation_service.generate_and_save(db, session_id, user_id)

    return DevJsonUploadResponse(
        session_id=session_id,
        saved_json_count=saved_json_count,
        created_result_count=created_result_count,
        status="completed",
        message="개발용 JSON 분석 결과가 저장되었습니다.",
    )
