from fastapi import FastAPI

from app.routers import analysis, auth, dev, images, recommendations, users

_DESCRIPTION = """
Deep Skin API는 얼굴 이미지 기반 피부 분석 백엔드입니다.

## 테스트 순서

1. **`POST /auth/signup`** 회원가입
2. **`POST /auth/login`** 로그인
3. Swagger 우측 상단 **Authorize**에 `access_token` 입력
4. **`PUT /users/me/profile`** 프로필 저장
5. **`POST /analysis/sessions`** 분석 세션 생성
6. **`POST /analysis/sessions/{session_id}/images`** 이미지 업로드
7. **`GET /recommendations/sessions/{session_id}`** 추천 결과 조회
8. **`GET /analysis/sessions/{session_id}/report`** 분석 리포트 조회

## 개발용 테스트

실제 모델 없이 테스트할 경우 6번 대신 **`POST /dev/analysis/sessions/{session_id}/json`** 을 사용한다.
"""

app = FastAPI(
    title="Deep Skin API",
    description=_DESCRIPTION,
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(analysis.router)
app.include_router(images.router)
app.include_router(dev.router)
app.include_router(recommendations.router)


@app.get(
    "/health",
    tags=["health"],
    summary="서버 상태 확인",
    description="서버가 정상 실행 중인지 확인하는 API다. 인증이 필요 없다.",
)
def health_check():
    return {"status": "ok", "service": "deep-skin-api"}
