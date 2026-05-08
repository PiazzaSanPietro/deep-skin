from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class JsonItemInfo(BaseModel):
    filename: Optional[str] = None
    id: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    date: Optional[str] = None
    skin_type: Optional[int] = None
    sensitive: Optional[int] = None


class JsonItemImages(BaseModel):
    device: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    angle: Optional[int] = None
    facepart: Optional[int] = None
    bbox: Optional[list[int]] = None

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v: Optional[list[int]]) -> Optional[list[int]]:
        if v is not None and len(v) != 4:
            raise ValueError("bbox는 [x, y, w, h] 형태의 정수 4개여야 합니다.")
        return v


class JsonItem(BaseModel):
    info: JsonItemInfo
    images: JsonItemImages
    annotations: dict[str, Any]
    equipment: Optional[dict[str, Any]] = None


class DevJsonUploadRequest(BaseModel):
    json_items: list[JsonItem]

    @field_validator("json_items")
    @classmethod
    def validate_json_items(cls, v: list[JsonItem]) -> list[JsonItem]:
        if not v:
            raise ValueError("json_items는 1개 이상이어야 합니다.")
        return v


class DevJsonUploadResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": 1,
                "saved_json_count": 1,
                "created_result_count": 4,
                "status": "completed",
                "message": "개발용 JSON 분석 결과가 저장되었습니다.",
            }
        }
    )

    session_id: int
    saved_json_count: int
    created_result_count: int
    status: str
    message: str
