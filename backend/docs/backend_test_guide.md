# Backend Test Guide

백엔드 통합 테스트 실행 방법과 전체 API 흐름을 정리한 문서다.

---

## 1. 사전 준비

### 의존성 설치

```powershell
cd backend
pip install -r requirements.txt
```

### DB 마이그레이션

```powershell
cd backend
alembic upgrade head
```

### .env 설정

`backend/.env` 파일에 아래 값이 설정되어 있어야 한다.

```env
# MySQL
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=zxasqw12
DB_NAME=deep_skin

DATABASE_URL=mysql+pymysql://root:zxasqw12@localhost:3306/deep_skin?charset=utf8mb4

# JWT
JWT_SECRET_KEY=deep-skin-local-dev-secret-key-2026
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=14

# Upload
UPLOAD_DIR=uploads/skin_images
MAX_IMAGE_SIZE_MB=10

# AI Inference (mock 또는 remote)
AI_INFERENCE_MODE=mock
AI_INFERENCE_URL=http://localhost:9000/inference/skin
AI_INFERENCE_TIMEOUT_SECONDS=30
```

---

## 2. AI Inference 모드

### Mock 모드

AI 서버 없이 고정된 6개 부위 결과를 반환한다. 기본 개발/테스트 모드다.

```env
AI_INFERENCE_MODE=mock
```

반환 결과:

| 부위 | 지표 | severity |
|------|------|----------|
| 볼 (left_cheek) | 모공 | moderate |
| 볼 (right_cheek) | 모공 | mild |
| 이마 | 주름 | normal |
| 눈가 | 주름 | severe |
| 입술 | 건조 | mild |
| 턱 | 처짐 | moderate |

### Remote 모드

실제 AI 서버(또는 dummy AI 서버)에 HTTP 요청을 보낸다.

```env
AI_INFERENCE_MODE=remote
AI_INFERENCE_URL=http://localhost:9000/inference/skin
```

---

## 3. Mock 모드 실행

터미널 1개로 백엔드만 실행한다.

```powershell
cd backend
python -m uvicorn app.main:app --reload
```

서버 기동 확인:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/health
```

---

## 4. Remote 모드 실행

터미널 2개가 필요하다.

**터미널 1 — dummy AI 서버 실행 (port 9000):**

```powershell
cd backend
python -m uvicorn scripts.dummy_ai_server:app --reload --port 9000
```

**터미널 2 — 백엔드 실행 (remote 모드):**

`.env`에서 `AI_INFERENCE_MODE=remote`로 수정하거나 환경변수로 지정한다.

```powershell
cd backend
$env:AI_INFERENCE_MODE="remote"
python -m uvicorn app.main:app --reload
```

서버 기동 확인:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/health
Invoke-RestMethod -Uri http://localhost:9000/health
```

---

## 5. 이미지 업로드 후 추천/리포트 흐름

이미지 업로드 API 호출 한 번으로 아래 순서가 자동으로 실행된다.

```
POST /analysis/sessions/{session_id}/images
  ↓ 이미지 검증 (확장자, MIME, 크기, 손상 여부)
  ↓ 파일 저장: uploads/skin_images/{user_id}/{session_id}/{uuid}.jpg
  ↓ uploaded_images 테이블에 메타데이터 저장
  ↓ inference_service.run_inference() 호출
      ├─ mock 모드: 고정 6개 parts 반환
      └─ remote 모드: AI 서버에 multipart/form-data 전송 → parts 수신
  ↓ skin_part_results 저장 (기존 image_id IS NOT NULL rows 삭제 후 재저장)
  ↓ recommendation_service.generate_and_save() 호출
      ↓ part_recommendations 생성 (rule-based, 알러지/민감 성분 제외)
  ↓ uploaded_images.upload_status = "processed"
  ↓ analysis_sessions.status = "completed"
```

이후 아래 API로 결과를 조회한다.

| API | 설명 |
|-----|------|
| `GET /recommendations/sessions/{session_id}` | 부위별 추천 성분/제품 카테고리, 제외 성분(reason_type 포함) |
| `GET /analysis/sessions/{session_id}/report` | 전체 리포트 (overall_summary + part_reports) |

---

## 6. 자동화 통합 테스트

`scripts/run_test.py`가 전체 흐름을 자동으로 검증한다.

### Mock 모드 테스트

```powershell
cd backend
python scripts/run_test.py --mode mock
```

### Remote 모드 테스트

dummy AI 서버와 백엔드를 모두 기동한 뒤 실행한다.

```powershell
cd backend
python scripts/run_test.py --mode remote
```

### 테스트 항목

| # | 항목 | 검증 내용 |
|---|------|-----------|
| 1 | 회원가입 | `POST /auth/signup` → HTTP 201, user_id 반환 |
| 2 | 로그인 | `POST /auth/login` → HTTP 200, access_token 발급 |
| 3 | 프로필 저장 | `PUT /users/me/profile` → HTTP 200 |
| 4 | 세션 생성 | `POST /analysis/sessions` → HTTP 201, session_id 반환 |
| 5 | 이미지 업로드 | `POST /analysis/sessions/{id}/images` → upload_status=processed, session_status=completed |
| 6 | DB 확인: skin_part_results | parts 수와 DB row 수 일치 |
| 7 | DB 확인: part_recommendations | 1개 이상 생성 |
| 8 | 추천 API | `GET /recommendations/sessions/{id}` → 추천 목록 반환, 제외 성분 reason_type 확인 |
| 9 | 리포트 API | `GET /analysis/sessions/{id}/report` → overall_summary, part_reports 반환 |

---

## 7. Swagger UI 수동 테스트

`http://localhost:8000/docs`에서 아래 순서로 테스트한다.

1. `POST /auth/signup` — 회원가입
2. `POST /auth/login` — 로그인 후 `access_token` 복사
3. 우측 상단 **Authorize** 클릭 → `access_token` 붙여넣기
4. `PUT /users/me/profile` — 프로필 저장 (나이, 민감도, 알러지 성분)
5. `POST /analysis/sessions` — 세션 생성 후 `session_id` 복사
6. `POST /analysis/sessions/{session_id}/images` — 이미지 업로드
7. `GET /recommendations/sessions/{session_id}` — 추천 결과 확인
8. `GET /analysis/sessions/{session_id}/report` — 리포트 확인

> AI-Hub JSON 데이터를 직접 입력하려면 6번 대신 `POST /dev/analysis/sessions/{session_id}/json`을 사용한다.

---

## 8. 테스트 완료 체크리스트

### Mock 모드

- [ ] 서버가 `http://localhost:8000/health`에 응답한다
- [ ] 회원가입 → 로그인 → 토큰 발급이 정상 동작한다
- [ ] 이미지 업로드 후 `upload_status=processed`, `session_status=completed`가 반환된다
- [ ] `inference_result.model_name`이 `mock_skin_model`이다
- [ ] `skin_part_results` DB에 parts 수만큼 row가 저장된다
- [ ] `part_recommendations` DB에 row가 생성된다
- [ ] 추천 API에서 알러지 성분은 `reason_type=allergy`, 민감 성분은 `reason_type=sensitive`로 제외된다
- [ ] 리포트 API의 `main_issues`가 severity 내림차순으로 정렬된다 (severe → moderate → mild → normal)
- [ ] 리포트 API의 `main_message`가 쉼표 구분 형식으로 반환된다

### Remote 모드 (추가 확인)

- [ ] dummy AI 서버가 `http://localhost:9000/health`에 응답한다
- [ ] 이미지 업로드 시 dummy AI 서버 로그에 수신 로그가 출력된다
- [ ] `inference_result.model_name`이 `skin_multitask_model`이다 (mock_skin_model이 아님)
- [ ] mock 모드와 동일한 추천/리포트 결과가 반환된다
