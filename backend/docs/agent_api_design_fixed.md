# Backend API Reference

이 문서는 현재 `backend/app/routers`와 `backend/app/schemas` 기준의 API 목록입니다.

## 공통 인증

인증이 필요한 API는 아래 헤더를 사용합니다.

```http
Authorization: Bearer <access_token>
```

인증은 `app/core/dependencies.py`의 `get_current_user()`가 처리합니다.

## 엔드포인트 목록

| Method | Endpoint | Auth | Router | 설명 |
|---|---|---:|---|---|
| GET | `/health` | No | `main.py` | 서버 상태 확인 |
| POST | `/auth/signup` | No | `auth.py` | 회원가입 |
| POST | `/auth/login` | No | `auth.py` | 로그인 및 access/refresh token 발급 |
| POST | `/auth/refresh` | No | `auth.py` | refresh token으로 access token 재발급 |
| POST | `/auth/logout` | Yes | `auth.py` | 현재 사용자의 미폐기 refresh token 전체 revoke |
| GET | `/users/me/profile` | Yes | `users.py` | 내 프로필 조회 |
| PUT | `/users/me/profile` | Yes | `users.py` | 내 프로필 생성/수정 |
| POST | `/analysis/sessions` | Yes | `analysis.py` | 분석 세션 생성 |
| POST | `/analysis/sessions/{session_id}/images` | Yes | `images.py` | 이미지 업로드 및 분석 |
| GET | `/analysis/metrics/trends` | Yes | `analysis.py` | 부위/지표별 측정값 추이 조회 (Phase 2-4 추가) |
| GET | `/analysis/sessions/{session_id}/metrics` | Yes | `analysis.py` | 상세 측정값 조회 (Phase 2-1 추가) |
| GET | `/analysis/sessions/{session_id}/report` | Yes | `analysis.py` | 분석 리포트 조회 |
| GET | `/analysis/reports/latest` | Yes | `analysis.py` | 현재 로그인 사용자의 최신 완료 리포트 조회 |
| GET | `/recommendations/sessions/{session_id}` | Yes | `recommendations.py` | 추천 결과 조회 |
| POST | `/dev/analysis/sessions/{session_id}/json` | Yes | `dev.py` | 개발용 AI-Hub JSON 입력 |

## Auth

### POST `/auth/signup`

Request:

```json
{
  "email": "test@example.com",
  "password": "test1234",
  "name": "테스터"
}
```

Validation:

- `email`: EmailStr
- `password`: 4자 이상
- `name`: 공백 제거 후 빈 문자열 불가

Response `201`:

```json
{
  "id": 1,
  "email": "test@example.com",
  "name": "테스터"
}
```

### POST `/auth/login`

Request:

```json
{
  "email": "test@example.com",
  "password": "test1234"
}
```

Response `200`:

```json
{
  "access_token": "<JWT access_token>",
  "refresh_token": "<JWT refresh_token>",
  "token_type": "bearer"
}
```

### POST `/auth/refresh`

Request:

```json
{
  "refresh_token": "<refresh_token>"
}
```

Response:

```json
{
  "access_token": "<new access_token>",
  "token_type": "bearer"
}
```

### POST `/auth/logout`

Authorization 필요. 현재 사용자의 아직 폐기되지 않은 refresh token을 모두 폐기합니다.

Response:

```json
{
  "message": "로그아웃되었습니다."
}
```

## Users

### GET `/users/me/profile`

프로필이 없으면 모든 필드가 `null`인 `UserProfileResponse`를 반환합니다.

Response fields:

```json
{
  "age": 28,
  "birth_year": 1998,
  "gender": "F",
  "skin_type": 3,
  "sensitive": 1,
  "main_concerns": ["wrinkle", "pore"],
  "allergy_ingredients": ["retinol"],
  "preferred_product_types": ["세럼", "크림"]
}
```

### PUT `/users/me/profile`

동일한 필드 구조로 upsert합니다.

Validation:

- `age`: 1~149
- `skin_type`: 0~9
- `sensitive`: 0 또는 1

Response:

```json
{
  "message": "프로필이 저장되었습니다.",
  "profile": { }
}
```

## Analysis

### POST `/analysis/sessions`

Request:

```json
{
  "session_name": "이미지 업로드 테스트"
}
```

Response `201`:

```json
{
  "id": 1,
  "session_name": "이미지 업로드 테스트",
  "status": "pending",
  "input_type": "image",
  "created_at": "2026-05-09T10:30:00"
}
```

### POST `/analysis/sessions/{session_id}/images`

`multipart/form-data`

| Field | Required | 설명 |
|---|---:|---|
| `file` | Yes | jpg/jpeg/png 이미지, 최대 `MAX_IMAGE_SIZE_MB` |
| `angle` | No | 개발/테스트 메타데이터 |
| `facepart` | No | 개발/테스트 메타데이터 |

Response:

```json
{
  "image_id": 1,
  "session_id": 1,
  "original_filename": "face.jpg",
  "stored_filename": "<uuid>.jpg",
  "file_path": "uploads/skin_images/1/1/<uuid>.jpg",
  "width": 1920,
  "height": 1080,
  "upload_status": "processed",
  "session_status": "completed",
  "inference_result": {
    "model_name": "mock_skin_model",
    "model_version": "0.0.1",
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
}
```

inference_result.parts[] 주요 필드:

| Field | Type | 설명 |
|---|---|---|
| `grade_value` | int | 기존 서비스 호환용 등급화된 정수값 |
| `predicted_value` | float \| null | 이미지 기반 AI 모델 예측 회귀값. 없으면 null |
| `measured_value` | float \| null | AI-Hub JSON 또는 장비 측정 기반 원본 수치. 없으면 null |
| `severity` | string | UI 표시 및 추천 로직에 사용하는 심각도 |

### GET `/analysis/metrics/trends`

현재 로그인 사용자의 특정 부위/지표에 대한 세션별 측정값 추이를 반환합니다. Phase 2-4에서 추가됐습니다.

Query parameters:

| 파라미터 | 필수 | 설명 |
|---|---|---|
| `raw_part_name` | 필수 | 부위 원본명 (예: `forehead`, `left_cheek`) |
| `metric_group` | 필수 | 지표 그룹 (예: `moisture`, `pore`, `elasticity`) |
| `metric_name` | 필수 | 지표명 (예: `moisture`, `pore_count`, `R2`) |
| `limit` | 선택 | 최대 조회 개수 (기본 10, 최대 50) |

- `status=completed` 세션만 포함합니다.
- `is_dummy=True` 지표는 제외합니다.
- 최근 `limit`개를 가져와 `analyzed_at` 오름차순으로 정렬해 반환합니다.
- 해당 데이터가 없으면 `trend=[]`를 반환합니다.

Response `200`:

```json
{
  "raw_part_name": "forehead",
  "display_part_name": "이마",
  "metric_group": "moisture",
  "metric_name": "moisture",
  "metric_key": "forehead_moisture",
  "trend": [
    {"session_id": 10, "analyzed_at": "2026-05-01T10:00:00", "value": 52.1},
    {"session_id": 18, "analyzed_at": "2026-05-08T10:00:00", "value": 55.3},
    {"session_id": 42, "analyzed_at": "2026-05-12T10:00:00", "value": 63.2}
  ]
}
```

데이터 없을 때:

```json
{
  "raw_part_name": "forehead",
  "display_part_name": null,
  "metric_group": "moisture",
  "metric_name": "moisture",
  "metric_key": null,
  "trend": []
}
```

### GET `/analysis/sessions/{session_id}/metrics`

`skin_metric_values` 상세 측정값을 부위별로 묶어 반환합니다. Phase 1-3 (multivalue 모드)에서 저장된 데이터를 조회합니다.

- mock / remote flat 모드로 분석한 세션은 `parts=[]`를 반환합니다.
- dummy 값(예: `chin_moisture`)은 `is_dummy=true`와 함께 포함됩니다.
- 다른 사용자의 세션은 404를 반환합니다.

Response `200`:

```json
{
  "session_id": 1,
  "parts": [
    {
      "raw_part_name": "forehead",
      "display_part_name": "이마",
      "facepart": 1,
      "metrics": [
        {
          "metric_group": "elasticity",
          "metric_name": "R2",
          "metric_key": "forehead_elasticity_R2",
          "value": 0.832,
          "value_type": "ratio",
          "unit": null,
          "is_dummy": false,
          "dummy_reason": null,
          "source": "multivalue_inference"
        }
      ]
    }
  ]
}
```

### GET `/analysis/sessions/{session_id}/report`

Response:

```json
{
  "session_id": 1,
  "status": "completed",
  "overall_summary": {
    "status": "집중 관리 필요",
    "main_message": "볼 부위의 모공 관리가 필요합니다.",
    "main_issues": [
      {"issue_type": "pore", "severity": "moderate"}
    ]
  },
  "part_reports": [
    {
      "display_part_name": "볼",
      "summary": "볼 부위에 모공 관리가 필요합니다.",
      "issues": [
        {
          "metric_name": "pore",
          "metric_display_name": "모공",
          "issue_type": "pore",
          "severity": "moderate",
          "grade_value": 2,
          "predicted_value": 0.62,
          "measured_value": null,
          "reason": null
        }
      ],
      "recommendation": null
    }
  ]
}
```

세션 상태가 `completed`가 아니면 `part_reports`는 빈 배열로 반환됩니다.

### GET `/analysis/reports/latest`

재로그인 등으로 프론트의 `current_session_id`가 비어 있을 때 사용하는 복구용 API입니다.
프론트가 `session_id`를 보내지 않으며, 백엔드는 access token의 현재 사용자 기준으로 가장 최근 `completed` 분석 세션을 찾아 기존 리포트 응답 구조 그대로 반환합니다.

조회 기준:

```sql
analysis_sessions.user_id = current_user.id
analysis_sessions.status = 'completed'
ORDER BY analyzed_at DESC, updated_at DESC, created_at DESC
LIMIT 1
```

Response `200`:

```json
{
  "session_id": 49,
  "status": "completed",
  "overall_summary": {
    "status": "집중 관리 필요",
    "main_message": "눈가 부위의 주름 관리가 필요합니다.",
    "main_issues": []
  },
  "part_reports": []
}
```

완료된 분석 리포트가 없으면 `404 Not Found`를 반환합니다.

```json
{
  "detail": {
    "error_code": "COMPLETED_REPORT_NOT_FOUND",
    "message": "완료된 분석 리포트가 없습니다."
  }
}
```

기존 `GET /analysis/sessions/{session_id}/report`는 분석 직후처럼 특정 `session_id`를 알고 있을 때 계속 사용합니다.

## Recommendations

### GET `/recommendations/sessions/{session_id}`

저장된 `part_recommendations`를 반환합니다. 세션이 `completed`인데 저장된 추천이 없으면 즉시 생성을 한 번 시도합니다.

```json
{
  "session_id": 1,
  "recommendations": [
    {
      "display_part_name": "볼",
      "issue_type": "pore",
      "issue_display_name": "모공",
      "severity": "moderate",
      "reason": "볼 부위의 모공 관리가 필요합니다.",
      "recommend_categories": [],
      "recommend_ingredients": [],
      "excluded_ingredients": [],
      "exclusion_reason": null,
      "care_tips": []
    }
  ]
}
```

## Dev JSON

### POST `/dev/analysis/sessions/{session_id}/json`

개발/테스트용 API입니다. AI-Hub 형식 JSON 배열을 받아 `skin_json_records`, `skin_part_results`, `part_recommendations`를 생성합니다.

```json
{
  "json_items": [
    {
      "info": {"filename": "test.jpg", "id": "0001", "gender": "F", "age": 28},
      "images": {"facepart": 5, "angle": 0, "width": 2136, "height": 3216, "bbox": [712, 676, 1835, 1139]},
      "annotations": {"l_cheek_pore": 2.73, "l_perocular_wrinkle": 3.91}
    }
  ]
}
```

Response:

```json
{
  "session_id": 1,
  "saved_json_count": 1,
  "created_result_count": 2,
  "status": "completed",
  "message": "개발용 JSON 분석 결과가 저장되었습니다."
}
```

## 공통 에러 형식

`app/core/exceptions.py` 기준으로 대부분의 명시적 에러는 아래 형식입니다.

```json
{
  "detail": {
    "error_code": "INVALID_TOKEN",
    "message": "유효하지 않은 토큰입니다."
  }
}
```
