from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class SessionCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"session_name": "이미지 업로드 테스트"}}
    )

    session_name: str

    @field_validator("session_name")
    @classmethod
    def validate_session_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("세션 이름을 입력해 주세요.")
        return v.strip()


class SessionCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_name: str
    status: str
    input_type: str
    created_at: datetime
