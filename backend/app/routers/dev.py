from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.dev_json import DevJsonUploadRequest, DevJsonUploadResponse
from app.services import dev_json_service

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post(
    "/analysis/sessions/{session_id}/json",
    response_model=DevJsonUploadResponse,
    summary="[개발용] AI-Hub JSON 업로드",
    description=(
        "**개발/테스트 전용 API. 실제 사용자 서비스에서는 사용하지 않는다.** "
        "**Authorization: Bearer access_token 필요**\n\n"
        "AI-Hub 라벨링 JSON을 업로드하여 실제 AI 모델 없이 "
        "`skin_part_results` 저장, 추천 생성, 리포트 생성을 테스트한다.\n\n"
        "업로드 후 `GET /recommendations/sessions/{session_id}`와 "
        "`GET /analysis/sessions/{session_id}/report`로 결과를 확인할 수 있다."
    ),
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "example": {
                        "json_items": [
                            {
                                "info": {
                                    "filename": "test.jpg",
                                    "id": "0001",
                                    "gender": "F",
                                    "age": 28,
                                },
                                "images": {
                                    "facepart": 5,
                                    "angle": 0,
                                    "width": 2136,
                                    "height": 3216,
                                    "bbox": [712, 676, 1835, 1139],
                                },
                                "annotations": {
                                    "l_cheek_pore": 2,
                                    "r_cheek_pore": 1,
                                    "l_perocular_wrinkle": 3,
                                    "lip_dryness": 0,
                                },
                            }
                        ]
                    }
                }
            }
        }
    },
)
def upload_dev_json(
    session_id: int,
    request: DevJsonUploadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return dev_json_service.upload_dev_json(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
        request=request,
    )
