from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SessionCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"session_name": "이미지 업로드 테스트"}}
    )

    session_name: str = Field(description="분석 세션 이름. 사용자가 구분할 수 있는 이름을 입력한다.")

    @field_validator("session_name")
    @classmethod
    def validate_session_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("세션 이름을 입력해 주세요.")
        return v.strip()


class SessionCreateResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "session_name": "이미지 업로드 테스트",
                "status": "pending",
                "input_type": "image",
                "created_at": "2026-05-09T10:30:00",
            }
        },
    )

    id: int = Field(description="세션 고유 ID")
    session_name: str = Field(description="분석 세션 이름")
    status: str = Field(description="세션 상태. pending / processing / completed / failed 중 하나")
    input_type: str = Field(description="입력 방식. image(이미지 업로드) 또는 dev_json(개발용 JSON)")
    created_at: datetime = Field(description="세션 생성 시각")
