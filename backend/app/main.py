from fastapi import FastAPI

from app.routers import analysis, auth, dev, images, recommendations, users

_DESCRIPTION = """
Deep Skin API는 얼굴 이미지 기반 피부 분석 백엔드입니다.

## 테스트 순서

1. **`POST /auth/signup`** 회원가입
2. **`POST /auth/login`** 로그인
3. Swagger 우측 상단 **Authorize**에 `access_token` 입력
4. **`PUT /users/me/profile`** 프로필 저장 (나이, 민감도, 알러지 성분)
5. **`POST /analysis/sessions`** 분석 세션 생성
6. **`POST /analysis/sessions/{session_id}/images`** 이미지 업로드
7. **`GET /recommendations/sessions/{session_id}`** 추천 결과 조회
8. **`GET /analysis/sessions/{session_id}/report`** 분석 리포트 조회

## AI Inference 모드

서버 기동 전 `.env`의 `AI_INFERENCE_MODE` 값으로 모드를 선택한다.

| 모드 | 설명 |
|---|---|
| `mock` | AI 서버 없이 고정 결과 반환. 기본 개발/테스트용 |
| `remote` | `AI_INFERENCE_URL`로 설정된 AI 서버에 실제 요청. dummy AI 서버(`scripts/dummy_ai_server.py`)로 테스트 가능 |

## 개발용 테스트

- AI-Hub JSON 데이터를 직접 입력하려면 6번 대신 **`POST /dev/analysis/sessions/{session_id}/json`** 을 사용한다.
- 자동화 통합 테스트: `python scripts/run_test.py --mode mock|remote`
- 상세 실행 방법: `docs/backend_test_guide.md` 참고
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
