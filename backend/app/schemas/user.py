from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class UserProfileUpsertRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "age": 28,
                "birth_year": 1998,
                "gender": "F",
                "skin_type": 3,
                "sensitive": 1,
                "main_concerns": ["wrinkle", "pore"],
                "allergy_ingredients": ["retinol"],
                "preferred_product_types": ["세럼", "크림"],
            }
        }
    )

    age: Optional[int] = None
    birth_year: Optional[int] = None
    gender: Optional[str] = None
    skin_type: Optional[int] = None
    sensitive: Optional[int] = None
    main_concerns: Optional[list[str]] = None
    allergy_ingredients: Optional[list[str]] = None
    preferred_product_types: Optional[list[str]] = None

    @field_validator("age")
    @classmethod
    def validate_age(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 149):
            raise ValueError("나이는 1에서 149 사이여야 합니다.")
        return v

    @field_validator("skin_type")
    @classmethod
    def validate_skin_type(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in range(10):
            raise ValueError("피부 타입 코드가 올바르지 않습니다.")
        return v

    @field_validator("sensitive")
    @classmethod
    def validate_sensitive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in (0, 1):
            raise ValueError("민감 여부는 0 또는 1이어야 합니다.")
        return v


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "age": 28,
                "birth_year": 1998,
                "gender": "F",
                "skin_type": 3,
                "sensitive": 1,
                "main_concerns": ["wrinkle", "pore"],
                "allergy_ingredients": ["retinol"],
                "preferred_product_types": ["세럼", "크림"],
            }
        },
    )

    age: Optional[int] = None
    birth_year: Optional[int] = None
    gender: Optional[str] = None
    skin_type: Optional[int] = None
    sensitive: Optional[int] = None
    main_concerns: Optional[list[str]] = None
    allergy_ingredients: Optional[list[str]] = None
    preferred_product_types: Optional[list[str]] = None


class UserProfileUpdateResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "프로필이 저장되었습니다.",
                "profile": {
                    "age": 28,
                    "birth_year": 1998,
                    "gender": "F",
                    "skin_type": 3,
                    "sensitive": 1,
                    "main_concerns": ["wrinkle", "pore"],
                    "allergy_ingredients": ["retinol"],
                    "preferred_product_types": ["세럼", "크림"],
                },
            }
        }
    )

    message: str
    profile: UserProfileResponse
