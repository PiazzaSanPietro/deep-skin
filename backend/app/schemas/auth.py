from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class SignupRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"email": "test@example.com", "password": "test1234", "name": "테스트"}
        }
    )

    email: EmailStr
    password: str
    name: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 4:
            raise ValueError("비밀번호는 4자 이상이어야 합니다.")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("이름을 입력해 주세요.")
        return v.strip()


class SignupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"email": "test@example.com", "password": "test1234"}
        }
    )

    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"refresh_token": "<POST /auth/login 응답의 refresh_token>"}
        }
    )

    refresh_token: str


class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    message: str = "로그아웃되었습니다."
