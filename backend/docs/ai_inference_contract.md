# AI Inference API Contract

백엔드와 AI inference 서버 간의 요청/응답 규격 문서.

---

## 1. 목적

사용자가 업로드한 얼굴 이미지를 AI 모델 서버에 전달하고,
부위별 피부 지표 분석 결과(parts 배열)를 받아 백엔드 DB에 저장하기 위한 인터페이스를 정의한다.

---

## 2. 백엔드 처리 흐름

```
프론트엔드
  → POST /analysis/sessions/{session_id}/images (이미지 업로드)
  → 백엔드: 이미지 검증
  → 백엔드: uploads/skin_images/{user_id}/{session_id}/{uuid}.jpg 저장
  → 백엔드: uploaded_images 테이블에 메타데이터 저장
  → 백엔드: 저장된 이미지 파일을 열어 AI 서버로 multipart/form-data 전달
  → AI 서버: 부위별 분석 결과 parts 반환
  → 백엔드: parts 전체를 skin_part_results에 저장
  → 백엔드: recommendation_service로 part_recommendations 생성
  → 프론트엔드: 추천/리포트 API 조회 가능
```

> 백엔드는 이미지 경로나 URL만 AI 서버에 넘기지 않는다.
> 반드시 저장된 이미지 파일을 바이너리로 열어 multipart/form-data의 `file` 필드로 전달한다.

---

## 3. 운영 모드

`.env` 설정으로 mock/remote 모드를 전환한다.

```env
AI_INFERENCE_MODE=mock          # mock | remote
AI_INFERENCE_URL=http://localhost:9000/inference/skin
AI_INFERENCE_TIMEOUT_SECONDS=30
```

| 모드 | 동작 |
|---|---|
| `mock` | `inference_service._run_mock()` — 고정된 mock 결과 반환 |
| `remote` | `inference_service._run_remote()` — AI 서버에 실제 HTTP 요청 |

---

## 4. AI 서버 요청 규격

### Endpoint

```
POST {AI_INFERENCE_URL}
Content-Type: multipart/form-data
```

### Form-data 필드

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `file` | binary | 필수 | 저장된 이미지 파일 (jpg/png) |
| `session_id` | string | 선택 | 분석 세션 ID |
| `user_id` | string | 선택 | 사용자 ID |
| `image_id` | string | 선택 | 업로드 이미지 DB ID |

### 요청 예시 (curl)

```bash
curl -X POST http://localhost:9000/inference/skin \
  -F "file=@/uploads/skin_images/1/1/abc123.jpg" \
  -F "session_id=1" \
  -F "user_id=1" \
  -F "image_id=1"
```

---

## 5. AI 서버 응답 규격

### 성공 응답 (200 OK)

```json
{
  "model_name": "skin_multitask_model",
  "model_version": "0.1.0",
  "parts": [
    {
      "raw_part_name": "left_cheek",
      "display_part_name": "볼",
      "metric_name": "pore",
      "metric_display_name": "모공",
      "issue_type": "pore",
      "grade_value": 2,
      "severity": "moderate",
      "confidence_score": 0.82
    },
    {
      "raw_part_name": "left_eye",
      "display_part_name": "눈가",
      "metric_name": "wrinkle",
      "metric_display_name": "주름",
      "issue_type": "wrinkle",
      "grade_value": 3,
      "severity": "severe",
      "confidence_score": 0.88
    }
  ]
}
```

### parts 필드 상세

| 필드 | 타입 | 설명 |
|---|---|---|
| `raw_part_name` | string | 내부 부위 키 (예: `left_cheek`, `forehead`) |
| `display_part_name` | string | 사용자 표시 부위명 (예: `볼`, `이마`) |
| `metric_name` | string | 지표 키 (예: `pore`, `wrinkle`) |
| `metric_display_name` | string | 지표 표시명 (예: `모공`, `주름`) |
| `issue_type` | string | 지표 분류 (아래 규칙 참고) |
| `grade_value` | int | 모델 원본 등급 (0~3 이상) |
| `severity` | string | 상태 등급 (아래 규칙 참고) |
| `confidence_score` | float | 예측 신뢰도 (0.0 ~ 1.0) |

---

## 6. issue_type 저장 규칙

`issue_type`은 **지표명만** 사용한다. 상태값을 포함하지 않는다.

| 허용 값 | 설명 |
|---|---|
| `pore` | 모공 |
| `wrinkle` | 주름 |
| `pigmentation` | 색소침착 |
| `moisture` | 수분 |
| `dryness` | 건조 |
| `sagging` | 처짐/탄력 |
| `acne` | 여드름 |

**사용 금지 패턴**:
- `pore_high`, `wrinkle_moderate` 등 상태값이 포함된 값은 사용하지 않는다.
- 상태 구분은 반드시 `severity` 필드로만 표현한다.

---

## 7. severity 저장 규칙

| 값 | 의미 |
|---|---|
| `normal` | 정상 / 양호 |
| `mild` | 경미 |
| `moderate` | 보통 이상 |
| `severe` | 심각 |

`grade_value` → `severity` 매핑 기준 (AI 모델 측 참고용):

| grade_value | severity |
|---|---|
| 0 | normal |
| 1 | mild |
| 2 | moderate |
| 3 이상 | severe |

---

## 8. 에러 응답 형식

AI 서버가 정상 처리하지 못한 경우 HTTP 4xx 또는 5xx와 함께 아래 형식으로 반환한다.

```json
{
  "error": "분석 실패 사유"
}
```

백엔드는 non-200 응답을 받으면:
- `uploaded_images.upload_status = "failed"`
- `uploaded_images.failure_reason = "AI 서버 오류 메시지"`
- `analysis_sessions.status = "failed"`
- `analysis_sessions.error_message = "모델 추론 중 오류가 발생했습니다."`

---

## 9. 백엔드 DB 저장 흐름

AI 서버로부터 parts 배열을 수신한 뒤 백엔드가 수행하는 저장 순서:

1. 기존 이미지 기반 `skin_part_results` 삭제 (재업로드 중복 방지 — `image_id IS NOT NULL` 조건)
2. `parts` 배열 전체를 `skin_part_results`에 저장
   - `image_id`: 업로드된 이미지 DB ID 연결
   - `model_name`, `model_version`: AI 서버 응답값 저장
3. `uploaded_images.upload_status = "processed"`
4. `analysis_sessions.status = "completed"`
5. `recommendation_service.generate_and_save()` 호출 → `part_recommendations` 생성

---

## 10. 테스트 방법

자세한 실행 방법과 체크리스트는 [`docs/backend_test_guide.md`](./backend_test_guide.md)를 참고한다.

### Mock 모드

```env
AI_INFERENCE_MODE=mock
```

```powershell
cd backend
python -m uvicorn app.main:app --reload
```

### Remote 모드 (dummy AI 서버 사용)

터미널 1 — dummy AI 서버 실행:
```powershell
cd backend
python -m uvicorn scripts.dummy_ai_server:app --reload --port 9000
```

터미널 2 — 백엔드 실행 (remote 모드):
```powershell
cd backend
$env:AI_INFERENCE_MODE="remote"
python -m uvicorn app.main:app --reload
```

이미지 업로드 시 dummy AI 서버 로그에서 수신 확인:
```
[dummy-ai] 수신 | filename=abc123.jpg size=204800bytes session_id=1 user_id=1 image_id=1
```

### 자동화 통합 테스트

```powershell
cd backend
python scripts/run_test.py --mode mock    # mock 모드
python scripts/run_test.py --mode remote  # remote 모드 (서버 2개 기동 후)
```

통합 테스트는 회원가입 → 로그인 → 프로필 → 세션 생성 → 이미지 업로드 → DB 확인 → 추천 API → 리포트 API 순서로 전체 흐름을 검증한다.

### 테스트 완료 기준

| 항목 | Mock | Remote |
|------|------|--------|
| 이미지 업로드 후 upload_status=processed | ✅ | ✅ |
| model_name | mock_skin_model | skin_multitask_model |
| skin_part_results DB 저장 (6개) | ✅ | ✅ |
| part_recommendations DB 생성 | ✅ | ✅ |
| 추천 API reason_type(allergy/sensitive) | ✅ | ✅ |
| 리포트 API main_issues severity 정렬 | ✅ | ✅ |
