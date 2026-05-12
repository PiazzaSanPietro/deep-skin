# Backend Agent Notes

이 문서는 `backend` 폴더에서 작업할 때 기준으로 삼는 최신 백엔드 요약입니다. 실제 코드는 FastAPI + MySQL + SQLAlchemy + Alembic 기반입니다.

## 현재 역할

Deep Skin 백엔드는 사용자가 업로드한 얼굴 이미지를 분석 세션에 연결하고, AI 추론 결과를 DB에 저장한 뒤 부위별 리포트와 rule-based 추천 결과를 제공합니다.

개발/테스트용으로 AI-Hub 형식 JSON을 직접 넣는 `/dev/analysis/sessions/{session_id}/json` 엔드포인트도 있습니다.

## 기술 스택

- FastAPI
- SQLAlchemy 2.x
- Alembic
- MySQL / PyMySQL
- Pydantic v2
- JWT Bearer 인증 (`python-jose`)
- bcrypt 비밀번호 해시
- Pillow 이미지 검증
- httpx 원격 AI 서버 호출

## 주요 폴더

```text
backend/
├── app/
│   ├── main.py
│   ├── core/          # config, security, dependencies, exceptions
│   ├── db/            # SQLAlchemy engine/session
│   ├── models/        # ORM models
│   ├── routers/       # FastAPI routers
│   ├── schemas/       # Pydantic request/response schemas
│   ├── services/      # business logic
│   └── utils/         # AI-Hub JSON parser
├── alembic/           # migrations and seed migrations
├── docs/              # backend documents
├── scripts/           # test runner, dummy AI server, cleanup script
└── uploads/           # local uploaded image storage
```

## 실행 기준

```powershell
cd backend
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --reload
```

환경 변수는 `app/core/config.py`의 `Settings`가 `.env`에서 읽습니다. `DATABASE_URL`은 직접 환경 변수로 읽지 않고 `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`으로 조합합니다.

## 현재 API

- `GET /health`
- `POST /auth/signup`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /users/me/profile`
- `PUT /users/me/profile`
- `POST /analysis/sessions`
- `POST /analysis/sessions/{session_id}/images`
- `GET /analysis/sessions/{session_id}/report`
- `GET /recommendations/sessions/{session_id}`
- `POST /dev/analysis/sessions/{session_id}/json`

## 회귀값 반영 현황 (2026-05-11 완료)

현재 백엔드는 `skin_part_results.measured_value` / `predicted_value` 컬럼을 활용합니다.

- `predicted_value`: 이미지 기반 AI 모델 예측 회귀값. mock/remote inference 경로에서 저장
- `measured_value`: AI-Hub JSON 또는 피부 측정 장비 기반 원본 수치. dev JSON 경로에서 저장
- `grade_value` / `severity` 기존 흐름 유지 — 기존 코드와 하위 호환
- `recommendation_service`는 현재 `severity` 기반으로 동작 (미변경)
- 두 컬럼은 migration 0003에서 이미 생성되어 있으며, 신규 migration 추가 불필요

관련 문서: `docs/ai_inference_contract.md`, `docs/regression_implementation_plan.md`, `docs/regression_result_db_plan.md`

## 작업 주의사항

- 기능 코드를 수정할 때는 라우터보다 서비스 계층의 실제 흐름을 먼저 확인합니다.
- 인증 필요 API는 `Depends(get_current_user)`와 `Authorization: Bearer <access_token>`을 기준으로 합니다.
- 업로드 파일은 로컬 `UPLOAD_DIR/{user_id}/{session_id}/{uuid}.jpg`에 저장되고 DB에는 경로와 메타데이터만 저장됩니다.
- 추천 로직은 현재 `recommendation_rules`, `ingredient_rules`, `part_recommendations` 기반 rule-based 방식입니다.
- `products` 테이블/모델은 존재하지만 현재 API 응답 생성 흐름에서는 직접 사용하지 않습니다.
- 모델 학습, EfficientNet/ViT 학습 코드, 이미지 분류 학습 파이프라인은 현재 백엔드 범위가 아닙니다.

## 참고 문서

- `docs/agent_backend_overview.md`
- `docs/agent_api_design_fixed.md`
- `docs/agent_auth_jwt.md`
- `docs/agent_db_design_fixed.md`
- `docs/agent_image_upload.md`
- `docs/agent_recommendation_seed_fixed.md`
- `docs/ai_inference_contract.md`
- `docs/backend_test_guide.md`