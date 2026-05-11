# AI Inference API Contract

백엔드와 외부 AI inference 서버 사이의 현재 계약입니다. 구현 기준은 `app/services/inference_service.py`와 `app/schemas/image_upload.py`입니다.

## 변경 이력

| 날짜 | 내용 |
|---|---|
| 2026-05-11 | `PartResult` 응답에 `predicted_value`, `measured_value` Optional 필드 추가. mock inference 및 dummy AI server 응답에 `predicted_value` 반영. dev JSON 경로에서는 `measured_value`를 원본 측정값으로 저장. 기존 `grade_value` / `severity` 기반 흐름은 유지. |

---

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

---

## Backend 처리 흐름

```text
POST /analysis/sessions/{session_id}/images
  -> 이미지 검증 및 저장
  -> uploaded_images row 생성
  -> inference_service.run_inference(image_path, session_id, user_id, image_id)
  -> InferenceResult 검증 (Pydantic)
  -> skin_part_results 저장 (predicted_value / measured_value 포함)
  -> recommendation_service.generate_and_save()
```

---

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

---

## Remote AI 성공 응답

백엔드는 아래 구조를 `InferenceResult`로 검증합니다.

```json
{
  "model_name": "mock_skin_model",
  "model_version": "0.1.0",
  "parts": [
    {
      "raw_part_name": "left_cheek",
      "display_part_name": "볼",
      "metric_name": "pore",
      "metric_display_name": "모공",
      "issue_type": "pore",
      "grade_value": 2,
      "predicted_value": 0.62,
      "measured_value": null,
      "severity": "moderate",
      "confidence_score": 0.82
    }
  ]
}
```

### parts 필드

| Field | Type | Required | 설명 |
|---|---|:---:|---|
| `raw_part_name` | string | Yes | 모델 원본 부위명 |
| `display_part_name` | string | Yes | 화면 표시용 부위명 |
| `metric_name` | string | Yes | 지표 key |
| `metric_display_name` | string | Yes | 지표 표시명 |
| `issue_type` | string | Yes | 이슈 종류 key |
| `grade_value` | int | **Yes** | 기존 서비스 호환을 위한 등급화된 정수값 (`0`, `1`, `2`, `3`) |
| `predicted_value` | float \| null | No | 이미지 기반 AI 모델이 예측한 회귀 연속값. 이미지 업로드 inference 경로에서 사용. |
| `measured_value` | float \| null | No | AI-Hub JSON 또는 피부 측정 장비 기반 원본 측정값. dev JSON / AI-Hub JSON 경로에서 사용. |
| `severity` | string | **Yes** | UI 표시 및 추천 로직에 사용하는 심각도. `normal` / `mild` / `moderate` / `severe` |
| `confidence_score` | float | Yes | 모델 신뢰도 |

> **주의**: 현재 단계에서 `grade_value`와 `severity`는 Optional로 변경하지 않습니다. 기존 추천 로직과 UI가 이 두 필드를 필수로 사용합니다.

---

## predicted_value vs measured_value

두 필드는 모두 회귀 연속값이지만 출처와 사용 경로가 다릅니다.

### predicted_value

- **출처**: 이미지 기반 AI 모델의 추론 결과
- **사용 경로**: 이미지 업로드 inference 경로 (`POST /analysis/sessions/{id}/images`)
- **저장 위치**: `skin_part_results.predicted_value`
- **포함 모드**: mock inference (`_run_mock()`), remote AI server 응답
- **예시**: `0.62`, `0.87`, `0.18`

### measured_value

- **출처**: AI-Hub JSON 또는 피부 측정 장비의 원본 측정 수치
- **사용 경로**: dev JSON 입력 경로 (`POST /dev/analysis/sessions/{id}/json`)
- **저장 위치**: `skin_part_results.measured_value`
- **포함 모드**: AI-Hub annotation JSON 파싱 결과 (`json_parser.py`)
- **예시**: `2.73`, `3.91`, `55.667`

### 경로별 정리

| 입력 경로 | predicted_value | measured_value |
|---|:---:|:---:|
| 이미지 업로드 inference | 저장됨 | NULL |
| dev JSON / AI-Hub JSON | NULL | 저장됨 |

---

## 하위 호환성

`predicted_value`와 `measured_value`는 Optional 필드입니다.

- 기존 AI 서버가 이 필드를 응답에 포함하지 않아도 백엔드는 정상 동작합니다.
- 필드가 누락되면 Pydantic schema에서 `None`으로 처리되고, DB에는 `NULL`로 저장됩니다.
- 기존 `grade_value`, `severity`, `confidence_score` 기반 흐름은 그대로 유지됩니다.

---

## severity 계산 기준

현재 구현에서는 `severity`를 `predicted_value` 또는 `measured_value` 기준으로 재계산하지 않습니다.

- **이미지 업로드 경로**: AI 서버가 `severity`를 직접 응답에 포함합니다.
- **dev JSON 경로**: `grade_value` 기준으로 `grade_to_severity()`가 계산합니다.
- `recommendation_service`는 `severity` 기반으로 동작하므로, 지표별 임계값이 확정되기 전까지 기존 흐름을 유지합니다.

권장 grade → severity 매핑:

| grade_value | severity |
|---:|---|
| 0 | `normal` |
| 1 | `mild` |
| 2 | `moderate` |
| 3 이상 | `severe` |

> **추후 고도화 메모**: 지표별 임계값과 방향성이 확정되면 `predicted_value` 또는 `measured_value` 기준으로 severity를 더 정교하게 계산할 수 있습니다.

---

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

---

## Remote 실패 처리

`httpx` timeout/request/status 오류 또는 응답 JSON/schema 검증 실패 시 백엔드는 이미지 업로드 흐름에서 실패 처리합니다.

- `uploaded_images.upload_status = failed`
- `uploaded_images.failure_reason` 기록
- `analysis_sessions.status = failed`
- `analysis_sessions.error_message` 기록
- API 응답은 `INFERENCE_FAILED`

---

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

`scripts/dummy_ai_server.py`의 `_MOCK_PARTS`에 `predicted_value`가 포함되어 있으므로, remote 모드 테스트 시에도 `predicted_value`가 DB에 저장됩니다.

---

## TODO: 값 범위 및 지표별 방향성

### predicted_value 범위 확정 필요

- `0.0~1.0` 정규화 범위인지
- `0.0~100.0` 백분율 범위인지
- 지표별 원 단위인지 확인 필요

### measured_value 범위 확인 필요

- moisture: `0~120` 계열인지 확인
- wrinkle roughness: `Ra` / `Rmax` / `Rt` 등 단위 확인
- elasticity: `R` / `Q` parameter 범위 확인
- pore: 개수 / 면적 / 픽셀값인지 확인

### 지표별 값 방향성 확인 필요

| 지표 | 방향 | 비고 |
|---|---|---|
| pore | 미정 | 값이 클수록 모공 넓음 가능성 |
| wrinkle | 미정 | roughness 계열이면 클수록 심함 가능성 |
| moisture | 미정 | 값이 클수록 좋음 가능성 |
| elasticity | 미정 | 지표 종류에 따라 다름 |
| pigmentation | 미정 | 면적 또는 강도 기반인지 확인 필요 |

> 방향성이 확정되기 전까지 severity는 기존 `grade_value` / AI 서버 응답 기반으로 유지합니다.
