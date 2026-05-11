# Backend Test Guide

현재 백엔드 실행 및 통합 테스트 기준입니다.

## 1. 의존성 설치

```powershell
cd backend
pip install -r requirements.txt
```

## 2. 환경 변수

`backend/.env` 파일을 사용합니다. 실제 값은 로컬 환경에 맞게 설정하세요.

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=<your-password>
DB_NAME=deep_skin

JWT_SECRET_KEY=<local-dev-secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=14

UPLOAD_DIR=uploads/skin_images
MAX_IMAGE_SIZE_MB=10

AI_INFERENCE_MODE=mock
AI_INFERENCE_URL=http://localhost:9000/inference/skin
AI_INFERENCE_TIMEOUT_SECONDS=30
```

주의: 현재 `Settings`는 `DATABASE_URL` 환경 변수를 직접 읽지 않습니다. DB 접속 URL은 위 `DB_*` 값으로 조합됩니다.

## 3. DB migration

```powershell
cd backend
alembic upgrade head
```

## 4. 서버 실행

Mock 모드:

```powershell
cd backend
python -m uvicorn app.main:app --reload
```

확인:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/health
```

Swagger:

```text
http://localhost:8000/docs
```

## 5. Remote 모드 테스트

터미널 1: dummy AI server

```powershell
cd backend
python -m uvicorn scripts.dummy_ai_server:app --reload --port 9000
```

터미널 2: backend remote 모드

```powershell
cd backend
$env:AI_INFERENCE_MODE="remote"
python -m uvicorn app.main:app --reload
```

확인:

```powershell
Invoke-RestMethod -Uri http://localhost:9000/health
Invoke-RestMethod -Uri http://localhost:8000/health
```

## 6. 수동 API 테스트 순서

Swagger 또는 HTTP client에서 아래 순서로 확인합니다.

1. `POST /auth/signup`
2. `POST /auth/login`
3. Swagger 상단 Authorize에 `access_token` 입력
4. `PUT /users/me/profile`
5. `POST /analysis/sessions`
6. `POST /analysis/sessions/{session_id}/images`
7. `GET /recommendations/sessions/{session_id}`
8. `GET /analysis/sessions/{session_id}/report`

개발용 JSON 흐름은 6번 대신 아래 API를 사용합니다.

```text
POST /dev/analysis/sessions/{session_id}/json
```

## 7. 자동 통합 테스트 스크립트

```powershell
cd backend
python scripts/run_test.py --mode mock
```

Remote 모드:

```powershell
cd backend
python scripts/run_test.py --mode remote
```

주의/TODO:

- 현재 `scripts/run_test.py` 내부의 `DB_URL`은 하드코딩되어 있습니다.
- 로컬 DB 계정/비밀번호가 다르면 스크립트 실행 전 `DB_URL`을 수정해야 합니다.
- 추후 `app.core.config.settings.DATABASE_URL`을 사용하도록 스크립트 개선을 권장합니다.

## 8. 기대 확인 항목

Mock 모드 기준:

- `/health`가 `{"status":"ok","service":"deep-skin-api"}`를 반환
- 회원가입 201 반환
- 로그인 응답에 `access_token`, `refresh_token` 포함
- 프로필 저장 200 반환
- 세션 생성 201 반환
- 이미지 업로드 후 `upload_status=processed`, `session_status=completed`
- `inference_result.model_name=mock_skin_model`
- `skin_part_results`에 parts 수만큼 row 저장
- `part_recommendations` 생성
- 추천 API가 `recommendations` 배열 반환
- 리포트 API가 `overall_summary`, `part_reports` 반환

Remote 모드 기준:

- dummy AI server가 `/health`에 응답
- backend가 dummy AI server로 multipart 요청을 보냄
- `inference_result.model_name=skin_multitask_model`
- 이후 추천/리포트 흐름은 mock과 동일하게 동작