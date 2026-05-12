from fastapi import HTTPException


def _exc(status_code: int, error_code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error_code": error_code, "message": message},
    )


# ── 인증 ──────────────────────────────────────────────
def email_already_exists() -> HTTPException:
    return _exc(400, "EMAIL_ALREADY_EXISTS", "이미 사용 중인 이메일입니다.")

def invalid_credentials() -> HTTPException:
    return _exc(401, "INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않습니다.")

def inactive_user() -> HTTPException:
    return _exc(403, "INACTIVE_USER", "비활성화된 사용자입니다.")

def not_authenticated() -> HTTPException:
    return _exc(401, "NOT_AUTHENTICATED", "인증이 필요합니다.")

def invalid_token() -> HTTPException:
    return _exc(401, "INVALID_TOKEN", "유효하지 않은 토큰입니다.")

def refresh_token_required() -> HTTPException:
    return _exc(401, "REFRESH_TOKEN_REQUIRED", "refresh token이 필요합니다.")

def invalid_refresh_token() -> HTTPException:
    return _exc(401, "INVALID_REFRESH_TOKEN", "유효하지 않은 refresh token입니다.")

def refresh_token_expired() -> HTTPException:
    return _exc(401, "REFRESH_TOKEN_EXPIRED", "만료된 refresh token입니다.")

def refresh_token_revoked() -> HTTPException:
    return _exc(401, "REFRESH_TOKEN_REVOKED", "폐기된 refresh token입니다.")

# ── 세션 ──────────────────────────────────────────────
def session_not_found() -> HTTPException:
    return _exc(404, "SESSION_NOT_FOUND", "분석 세션을 찾을 수 없습니다.")

def completed_report_not_found() -> HTTPException:
    return _exc(404, "COMPLETED_REPORT_NOT_FOUND", "완료된 분석 리포트가 없습니다.")

def session_access_denied() -> HTTPException:
    return _exc(403, "SESSION_ACCESS_DENIED", "본인의 분석 세션만 접근할 수 있습니다.")

# ── 이미지 ────────────────────────────────────────────
def image_file_required() -> HTTPException:
    return _exc(400, "IMAGE_FILE_REQUIRED", "이미지 파일이 필요합니다.")

def invalid_image_extension() -> HTTPException:
    return _exc(400, "INVALID_IMAGE_EXTENSION", "jpg, jpeg, png 파일만 업로드할 수 있습니다.")

def invalid_image_type() -> HTTPException:
    return _exc(400, "INVALID_IMAGE_TYPE", "이미지 MIME type이 올바르지 않습니다.")

def image_too_large() -> HTTPException:
    return _exc(400, "IMAGE_TOO_LARGE", "이미지 파일 크기는 10MB 이하만 업로드할 수 있습니다.")

def invalid_image_file() -> HTTPException:
    return _exc(400, "INVALID_IMAGE_FILE", "손상된 이미지 파일입니다.")

def inference_failed() -> HTTPException:
    return _exc(500, "INFERENCE_FAILED", "모델 추론 중 오류가 발생했습니다.")
