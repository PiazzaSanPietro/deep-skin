from services import api_client

_REQUIRED_FIELDS = [
    "age", "gender", "skin_type", "sensitive",
    "main_concerns", "allergy_ingredients", "preferred_product_types",
]
_LIST_FIELDS = {"main_concerns", "allergy_ingredients", "preferred_product_types"}


def get_profile(token: str) -> dict:
    return api_client.get("/users/me/profile", token=token)


def update_profile(token: str, data: dict) -> dict:
    return api_client.put("/users/me/profile", json=data, token=token)


def is_profile_complete(profile: dict) -> bool:
    """필수 필드가 모두 채워진 경우 True."""
    if api_client.is_error(profile):
        return False
    for field in _REQUIRED_FIELDS:
        val = profile.get(field)
        if val is None:
            return False
        # 리스트 필드는 빈 리스트도 미완성으로 간주
        if field in _LIST_FIELDS and isinstance(val, list) and len(val) == 0:
            return False
    return True
