# AI Inference API Contract

백엔드와 외부 AI inference 서버 사이의 현재 계약입니다. 구현 기준은 `app/services/inference_service.py`와 `app/schemas/image_upload.py`입니다.

## 모드

`AI_INFERENCE_MODE`로 선택합니다.

| Mode | 동작 |
|---|---|
| `mock` | 외부 서버 호출 없이 `_run_mock()`의 고정 결과 반환 |
| `remote` | `AI_INFERENCE_URL`로 multipart/form-data HTTP 요청 |

환경 변수:

```env
AI_INFERENCE_MODE=mock
AI_INFERENCE_URL=http://localhost:9000/inference/skin
AI_INFERENCE_TIMEOUT_SECONDS=30
```

## Backend 처리 흐름

```text
POST /analysis/sessions/{session_id}/images
  -> 이미지 검증 및 저장
  -> uploaded_images row 생성
  -> inference_service.run_inference(image_path, session_id, user_id, image_id)
  -> InferenceResult 검증
  -> skin_part_results 저장
  -> recommendation_service.generate_and_save()
```

## Remote AI 요청

Endpoint:

```text
POST {AI_INFERENCE_URL}
Content-Type: multipart/form-data
```

Form-data:

| Field | Required | 설명 |
|---|---:|---|
| `file` | Yes | 저장된 이미지 파일 bytes. 현재 content type은 `image/jpeg`로 전송 |
| `session_id` | No | 분석 세션 ID 문자열 |
| `user_id` | No | 사용자 ID 문자열 |
| `image_id` | No | 업로드 이미지 DB ID 문자열 |

curl 예시:

```bash
curl -X POST http://localhost:9000/inference/skin \
  -F "file=@uploads/skin_images/1/1/example.jpg" \
  -F "session_id=1" \
  -F "user_id=1" \
  -F "image_id=1"
```

## Remote AI 성공 응답

백엔드는 아래 구조를 `InferenceResult`로 검증합니다.

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
    }
  ]
}
```

### parts 필드

| Field | Type | 설명 |
|---|---|---|
| `raw_part_name` | string | 모델 원본 부위명 |
| `display_part_name` | string | 화면 표시용 부위명 |
| `metric_name` | string | 지표 key |
| `metric_display_name` | string | 지표 표시명 |
| `issue_type` | string | 이슈 종류 key |
| `grade_value` | int | 원본 등급 값 |
| `severity` | string | `normal`, `mild`, `moderate`, `severe` |
| `confidence_score` | float | 신뢰도 |

## issue_type 규칙

현재 mock과 seed rule에서 주로 쓰는 값:

- `pore`
- `wrinkle`
- `dryness`
- `sagging`

외부 AI 확장 후보:

- `pigmentation`
- `moisture`
- `acne`

추천 rule이 없는 issue_type은 분석 결과로 저장될 수 있지만 추천 결과가 생성되지 않을 수 있습니다.

## severity 규칙

```text
normal
mild
moderate
severe
```

권장 매핑:

| grade_value | severity |
|---:|---|
| 0 | `normal` |
| 1 | `mild` |
| 2 | `moderate` |
| 3 이상 | `severe` |

## Remote 실패 처리

`httpx` timeout/request/status 오류 또는 응답 JSON/schema 검증 실패 시 백엔드는 이미지 업로드 흐름에서 실패 처리합니다.

- `uploaded_images.upload_status = failed`
- `uploaded_images.failure_reason` 기록
- `analysis_sessions.status = failed`
- `analysis_sessions.error_message` 기록
- API 응답은 `INFERENCE_FAILED`

## Dummy AI server

개발용 remote 테스트 서버:

```powershell
cd backend
python -m uvicorn scripts.dummy_ai_server:app --reload --port 9000
```

헬스체크:

```powershell
Invoke-RestMethod -Uri http://localhost:9000/health
```