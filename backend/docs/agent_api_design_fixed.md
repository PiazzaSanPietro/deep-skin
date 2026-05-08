# `docs/agent_api_design.md`

**역할:** API 구현 지침서

엔드포인트, 요청/응답 예시, 인증 필요 여부를 정리한다.

---

## 공통 인증 헤더

인증이 필요한 API는 다음 헤더를 사용한다.

```http
Authorization: Bearer <access_token>
```

---

## API 목록

| 기능 | Method | Endpoint | 인증 |
|---|---|---|---|
| 회원가입 | POST | `/auth/signup` | X |
| 로그인 | POST | `/auth/login` | X |
| 내 프로필 수정 | PUT | `/users/me/profile` | O |
| 분석 세션 생성 | POST | `/analysis/sessions` | O |
| 이미지 업로드 | POST | `/analysis/sessions/{session_id}/images` | O |
| 분석 리포트 조회 | GET | `/analysis/sessions/{session_id}/report` | O |
| 추천 결과 조회 | GET | `/recommendations/sessions/{session_id}` | O |
| 개발용 JSON 업로드 | POST | `/dev/analysis/sessions/{session_id}/json` | O |

---

## issue_type / severity 응답 기준

API 응답에서 `issue_type`에는 상태를 포함하지 않는다.

### 권장

```json
{
  "issue_type": "pore",
  "severity": "moderate"
}
```

### 비권장

```json
{
  "issue_type": "pore_high"
}
```

즉, 문제 지표는 `issue_type`으로 표현하고, 상태는 `severity`로 표현한다.

| 필드 | 예시 | 설명 |
|---|---|---|
| `issue_type` | `pore`, `wrinkle`, `moisture` | 문제 지표명 |
| `severity` | `normal`, `mild`, `moderate`, `severe` | 심각도 |

---

## 회원가입

```http
POST /auth/signup
```

### 요청

```json
{
  "email": "user@test.com",
  "password": "1234",
  "name": "홍길동"
}
```

### 응답

```json
{
  "id": 1,
  "email": "user@test.com",
  "name": "홍길동"
}
```

### 예외

| 상황 | status code | error_code |
|---|---:|---|
| 이메일 중복 | 400 | EMAIL_ALREADY_EXISTS |
| 이메일 형식 오류 | 422 | INVALID_EMAIL |
| 비밀번호 길이 오류 | 422 | INVALID_PASSWORD |

---

## 로그인

```http
POST /auth/login
```

### 요청

```json
{
  "email": "user@test.com",
  "password": "1234"
}
```

### 응답

```json
{
  "access_token": "jwt-access-token",
  "refresh_token": "jwt-refresh-token",
  "token_type": "bearer"
}
```

### 예외

| 상황 | status code | error_code |
|---|---:|---|
| 로그인 실패 | 401 | INVALID_CREDENTIALS |
| 비활성 사용자 | 403 | INACTIVE_USER |

---

## 내 프로필 수정

```http
PUT /users/me/profile
```

### 인증

```http
Authorization: Bearer <access_token>
```

### 설명

로그인한 사용자의 추가 개인정보를 등록하거나 수정한다.

이 정보는 피부 분석 결과와 추천 결과를 개인화하는 데 사용한다.

JWT payload에는 나이, 성별, 피부 타입 같은 개인정보를 넣지 않고, 해당 정보는 `user_profiles` 테이블에서 관리한다.

### 요청

```json
{
  "age": 28,
  "birth_year": 1998,
  "gender": "F",
  "skin_type": 3,
  "sensitive": 1,
  "main_concerns": ["moisture", "pore", "pigmentation"],
  "allergy_ingredients": ["fragrance", "alcohol"],
  "preferred_product_types": ["세럼", "크림"]
}
```

### 요청 필드 설명

| 필드 | 타입 | 필수 여부 | 설명 |
|---|---|---|---|
| `age` | int | 선택 | 사용자 나이 |
| `birth_year` | int | 선택 | 출생연도 |
| `gender` | string | 선택 | 성별, 예: `M`, `F` |
| `skin_type` | int | 선택 | 피부 타입 코드 |
| `sensitive` | int | 선택 | 민감 여부, `0`: 아니오, `1`: 예 |
| `main_concerns` | array | 선택 | 주요 피부 고민 |
| `allergy_ingredients` | array | 선택 | 피해야 할 성분 key |
| `preferred_product_types` | array | 선택 | 선호 화장품 타입 |

### 응답

```json
{
  "message": "프로필이 저장되었습니다.",
  "profile": {
    "age": 28,
    "birth_year": 1998,
    "gender": "F",
    "skin_type": 3,
    "sensitive": 1,
    "main_concerns": ["moisture", "pore", "pigmentation"],
    "allergy_ingredients": ["fragrance", "alcohol"],
    "preferred_product_types": ["세럼", "크림"]
  }
}
```

### 예외

| 상황 | status code | error_code |
|---|---:|---|
| 토큰 없음 | 401 | NOT_AUTHENTICATED |
| 잘못된 토큰 | 401 | INVALID_TOKEN |
| 나이 범위 오류 | 422 | INVALID_PROFILE_VALUE |
| 피부 타입 범위 오류 | 422 | INVALID_SKIN_TYPE |
| 민감 여부 범위 오류 | 422 | INVALID_SENSITIVE_VALUE |

---

## 분석 세션 생성

```http
POST /analysis/sessions
```

### 인증

```http
Authorization: Bearer <access_token>
```

### 설명

피부 분석 1회를 관리하기 위한 분석 세션을 생성한다.

사용자가 이미지를 업로드하기 전 먼저 분석 세션을 생성하고, 이후 해당 `session_id`에 이미지를 업로드한다.

### 요청

```json
{
  "session_name": "2026-05-08 피부 분석",
  "input_type": "image"
}
```

### 요청 필드 설명

| 필드 | 타입 | 필수 여부 | 설명 |
|---|---|---|---|
| `session_name` | string | 필수 | 분석 세션 이름 |
| `input_type` | string | 필수 | 입력 타입, `image`, `dev_json`, `mixed` |

### 응답

```json
{
  "session_id": 1,
  "session_name": "2026-05-08 피부 분석",
  "input_type": "image",
  "status": "pending",
  "created_at": "2026-05-08T13:00:00"
}
```

### 상태값

| status | 설명 |
|---|---|
| `pending` | 분석 세션 생성 직후 |
| `processing` | 이미지 업로드 후 분석 진행 중 |
| `completed` | 분석 및 추천 생성 완료 |
| `failed` | 분석 실패 |

### 예외

| 상황 | status code | error_code |
|---|---:|---|
| 토큰 없음 | 401 | NOT_AUTHENTICATED |
| 잘못된 토큰 | 401 | INVALID_TOKEN |
| 세션 이름 누락 | 422 | REQUIRED_FIELD_MISSING |
| input_type 오류 | 422 | INVALID_INPUT_TYPE |

---

## 이미지 업로드

```http
POST /analysis/sessions/{session_id}/images
```

### 인증

```http
Authorization: Bearer <access_token>
```

### Content-Type

```http
Content-Type: multipart/form-data
```

### 설명

사용자가 얼굴 이미지를 업로드한다.

백엔드는 이미지를 검증하고 파일 시스템에 저장한 뒤, 모델 추론 서비스를 호출하여 피부 분석 결과를 생성한다.

모델 추론 결과는 `skin_part_results` 테이블에 저장하고, 이후 부위별 리포트와 추천 결과 생성에 사용한다.

### 요청 필드

| 필드 | 타입 | 필수 여부 | 설명 |
|---|---|---|---|
| `file` | File | 필수 | 업로드할 얼굴 이미지 |
| `angle` | int | 선택 | 촬영 각도 |
| `facepart` | int | 선택 | 얼굴 부위 코드 |

### 요청 예시

```text
file: face.jpg
angle: 0
facepart: 0
```

### 응답

```json
{
  "image_id": 1,
  "session_id": 1,
  "status": "processed",
  "message": "이미지 분석이 완료되었습니다."
}
```

### 처리 결과 저장 예시

```json
{
  "uploaded_image": {
    "original_filename": "face.jpg",
    "stored_filename": "550e8400-e29b-41d4-a716-446655440000.jpg",
    "file_path": "uploads/skin_images/1/1/550e8400-e29b-41d4-a716-446655440000.jpg",
    "content_type": "image/jpeg",
    "file_size": 2048000,
    "width": 1080,
    "height": 1440,
    "upload_status": "processed"
  }
}
```

### 예외

| 상황 | status code | error_code |
|---|---:|---|
| 토큰 없음 | 401 | NOT_AUTHENTICATED |
| 세션 없음 | 404 | SESSION_NOT_FOUND |
| 다른 사용자 세션 접근 | 403 | SESSION_ACCESS_DENIED |
| 파일 없음 | 400 | IMAGE_FILE_REQUIRED |
| 확장자 오류 | 400 | INVALID_IMAGE_EXTENSION |
| MIME type 오류 | 400 | INVALID_IMAGE_TYPE |
| 파일 용량 초과 | 400 | IMAGE_TOO_LARGE |
| 손상된 이미지 | 400 | INVALID_IMAGE_FILE |
| 모델 추론 실패 | 500 | INFERENCE_FAILED |

---

## 분석 리포트 조회

```http
GET /analysis/sessions/{session_id}/report
```

### 인증

```http
Authorization: Bearer <access_token>
```

### 설명

분석 리포트 조회 API는 사용자 화면에 보여줄 수 있는 **부위별 리포트 구조**로 반환한다.

DB에 저장된 세부 분석 결과를 그대로 반환하지 않고, 볼, 눈가, 입술, 턱 등 부위별로 묶어서 반환한다.

정상 또는 평균 상태인 지표도 `normal`, `mild` 상태로 반환할 수 있다.

### 응답 예시

```json
{
  "session_id": 1,
  "status": "completed",
  "overall_summary": {
    "status": "주의",
    "main_message": "볼 부위의 모공과 눈가 주름 관리가 필요합니다.",
    "main_issues": [
      {
        "issue_type": "pore",
        "severity": "moderate"
      },
      {
        "issue_type": "wrinkle",
        "severity": "severe"
      }
    ]
  },
  "part_reports": [
    {
      "display_part_name": "볼",
      "summary": "볼 부위에서 모공 관리가 필요합니다.",
      "issues": [
        {
          "metric_name": "pore",
          "metric_display_name": "모공",
          "issue_type": "pore",
          "severity": "moderate",
          "grade_value": 3,
          "reason": "볼 부위의 모공 등급이 보통 이상으로 분석되었습니다."
        }
      ],
      "recommendation": {
        "categories": ["모공 케어 토너", "피지 조절 세럼"],
        "ingredients": [
          {
            "key": "bha",
            "name": "BHA"
          },
          {
            "key": "niacinamide",
            "name": "나이아신아마이드"
          }
        ],
        "excluded_ingredients": [],
        "exclusion_reason": null,
        "care_tips": [
          "피지 조절과 모공 케어 중심의 제품을 사용하는 것이 좋습니다."
        ]
      }
    },
    {
      "display_part_name": "입술",
      "summary": "입술 건조 상태가 양호하게 분석되었습니다.",
      "issues": [
        {
          "metric_name": "dryness",
          "metric_display_name": "건조",
          "issue_type": "dryness",
          "severity": "normal",
          "grade_value": 0,
          "reason": "입술 건조 상태가 양호하게 분석되었습니다."
        }
      ],
      "recommendation": {
        "categories": ["데일리 립밤", "보습 립 케어 제품"],
        "ingredients": [
          {
            "key": "panthenol",
            "name": "판테놀"
          },
          {
            "key": "ceramide",
            "name": "세라마이드"
          }
        ],
        "excluded_ingredients": [],
        "exclusion_reason": null,
        "care_tips": [
          "입술이 건조하지 않아도 수시로 립밤을 사용해 보습을 유지하는 것이 좋습니다."
        ]
      }
    }
  ]
}
```

### 예외

| 상황 | status code | error_code |
|---|---:|---|
| 토큰 없음 | 401 | NOT_AUTHENTICATED |
| 세션 없음 | 404 | SESSION_NOT_FOUND |
| 다른 사용자 세션 접근 | 403 | SESSION_ACCESS_DENIED |
| 리포트 없음 | 404 | REPORT_NOT_FOUND |
| 리포트 생성 실패 | 500 | REPORT_GENERATION_FAILED |

---

## 추천 결과 조회

```http
GET /recommendations/sessions/{session_id}
```

### 인증

```http
Authorization: Bearer <access_token>
```

### 설명

분석 세션에 생성된 부위별 추천 결과를 조회한다.

추천은 세션 전체 기준이 아니라, 눈가, 볼, 이마, 입술, 턱 등 부위별 문제 지표를 기준으로 생성한다.

추천 결과는 `issue_type`과 `severity`를 함께 내려준다.

예:

```json
{
  "issue_type": "pore",
  "severity": "moderate"
}
```

### 응답

```json
{
  "session_id": 1,
  "recommendations": [
    {
      "display_part_name": "볼",
      "issue_type": "pore",
      "issue_display_name": "모공",
      "severity": "moderate",
      "reason": "볼 부위의 모공 등급이 보통 이상으로 분석되어 모공 관리가 필요합니다.",
      "recommend_categories": ["모공 케어 토너", "피지 조절 세럼", "클레이 마스크"],
      "recommend_ingredients": [
        {
          "key": "bha",
          "name": "BHA"
        },
        {
          "key": "niacinamide",
          "name": "나이아신아마이드"
        },
        {
          "key": "zinc_pca",
          "name": "징크 PCA"
        }
      ],
      "excluded_ingredients": [
        {
          "key": "fragrance",
          "name": "향료"
        }
      ],
      "exclusion_reason": "사용자가 피해야 할 성분으로 등록한 향료는 추천 성분에서 제외했습니다.",
      "care_tips": [
        "피지 조절과 모공 케어 중심의 제품을 사용하는 것이 좋습니다.",
        "자극이 강한 필링 제품은 주 1~2회 이하로 사용하는 것이 좋습니다."
      ]
    },
    {
      "display_part_name": "눈가",
      "issue_type": "wrinkle",
      "issue_display_name": "주름",
      "severity": "severe",
      "reason": "눈가 주름 깊이가 높게 분석되어 집중적인 주름 개선 관리가 필요합니다.",
      "recommend_categories": ["고기능 아이크림", "주름 개선 세럼", "탄력 크림"],
      "recommend_ingredients": [
        {
          "key": "peptide",
          "name": "펩타이드"
        },
        {
          "key": "adenosine",
          "name": "아데노신"
        }
      ],
      "excluded_ingredients": [
        {
          "key": "retinol",
          "name": "레티놀"
        }
      ],
      "exclusion_reason": "사용자가 피해야 할 성분으로 등록한 레티놀은 추천 성분에서 제외했습니다.",
      "care_tips": [
        "눈가 전용 제품을 사용하는 것이 좋습니다.",
        "민감 피부라면 레티놀 대신 펩타이드나 아데노신 중심 제품을 우선 고려하는 것이 좋습니다."
      ]
    },
    {
      "display_part_name": "입술",
      "issue_type": "dryness",
      "issue_display_name": "건조",
      "severity": "normal",
      "reason": "입술 건조 상태가 양호하게 분석되었습니다. 현재 보습 관리를 유지하는 것이 좋습니다.",
      "recommend_categories": ["데일리 립밤", "보습 립 케어 제품"],
      "recommend_ingredients": [
        {
          "key": "shea_butter",
          "name": "시어버터"
        },
        {
          "key": "panthenol",
          "name": "판테놀"
        },
        {
          "key": "ceramide",
          "name": "세라마이드"
        }
      ],
      "excluded_ingredients": [],
      "exclusion_reason": null,
      "care_tips": [
        "입술이 건조하지 않아도 수시로 립밤을 사용해 보습을 유지하는 것이 좋습니다.",
        "입술을 자주 핥는 습관은 건조함을 유발할 수 있어 주의하는 것이 좋습니다."
      ]
    }
  ]
}
```

### 예외

| 상황 | status code | error_code |
|---|---:|---|
| 토큰 없음 | 401 | NOT_AUTHENTICATED |
| 세션 없음 | 404 | SESSION_NOT_FOUND |
| 다른 사용자 세션 접근 | 403 | SESSION_ACCESS_DENIED |
| 추천 결과 없음 | 404 | RECOMMENDATION_NOT_FOUND |
| 추천 생성 실패 | 500 | RECOMMENDATION_FAILED |

---

## 개발용 JSON 업로드

```http
POST /dev/analysis/sessions/{session_id}/json
```

### 인증

```http
Authorization: Bearer <access_token>
```

### 설명

AI-Hub 라벨링 JSON을 업로드하여 모델 추론 없이 백엔드 흐름을 검증한다.

이 API는 실제 사용자 서비스 기능이 아니라 개발/테스트용 기능이다.

사용 목적:

- 모델 추론 없이 DB 저장 흐름 테스트
- AI-Hub JSON 파싱 테스트
- `skin_part_results` 저장 테스트
- 부위별 리포트 생성 테스트
- 부위별 추천 로직 테스트

### 요청

```json
{
  "json_items": [
    {
      "info": {
        "filename": "0001_01_R15.jpg",
        "id": "0001",
        "gender": "F",
        "age": 28,
        "date": "2023-08-17",
        "skin_type": 0,
        "sensitive": 0
      },
      "images": {
        "device": 0,
        "width": 2136,
        "height": 3216,
        "angle": 5,
        "facepart": 5,
        "bbox": [712, 676, 1835, 1139]
      },
      "annotations": {
        "l_cheek_pigmentation": 2,
        "l_cheek_pore": 3
      },
      "equipment": {
        "l_cheek_moisture": 43.0,
        "pore_count_l_cheek": 152
      }
    }
  ]
}
```

### 요청 필드 설명

| 필드 | 필수 여부 | 설명 |
|---|---|---|
| `json_items` | 필수 | 업로드할 JSON 배열 |
| `info` | 필수 | 파일명, 원본 ID, 성별, 나이 등 |
| `images` | 필수 | 촬영 장비, 이미지 크기, 각도, 부위, bbox |
| `annotations` | 필수 | 전문가 진단 등급 |
| `equipment` | 선택 | 장비 측정값 |

### 응답

```json
{
  "session_id": 1,
  "saved_json_count": 1,
  "created_result_count": 2,
  "status": "completed",
  "message": "개발용 JSON 분석 결과가 저장되었습니다."
}
```

### 저장 결과 예시

```json
{
  "skin_part_results": [
    {
      "display_part_name": "볼",
      "raw_part_name": "left_cheek",
      "metric_name": "pigmentation",
      "metric_display_name": "색소침착",
      "grade_value": 2,
      "severity": "moderate",
      "issue_type": "pigmentation"
    },
    {
      "display_part_name": "볼",
      "raw_part_name": "left_cheek",
      "metric_name": "pore",
      "metric_display_name": "모공",
      "grade_value": 3,
      "severity": "severe",
      "issue_type": "pore"
    }
  ]
}
```



### 예외

| 상황 | status code | error_code |
|---|---:|---|
| 토큰 없음 | 401 | NOT_AUTHENTICATED |
| 세션 없음 | 404 | SESSION_NOT_FOUND |
| 다른 사용자 세션 접근 | 403 | SESSION_ACCESS_DENIED |
| json_items 누락 | 422 | REQUIRED_FIELD_MISSING |
| info 누락 | 422 | INVALID_JSON_SCHEMA |
| images 누락 | 422 | INVALID_JSON_SCHEMA |
| annotations 누락 | 422 | INVALID_JSON_SCHEMA |
| bbox 형식 오류 | 422 | INVALID_BBOX |
| facepart 범위 오류 | 422 | INVALID_FACEPART |
| JSON 파싱 실패 | 422 | INVALID_JSON_SCHEMA |
