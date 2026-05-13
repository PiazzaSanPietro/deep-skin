
# 4. `frontend/docs/frontend_api_flow.md`


# Frontend API Flow Guide

## Backend Base URL

`.env`에서 백엔드 주소를 관리한다.

```env
BACKEND_API_URL=http://localhost:8000
```

## 전체 API 흐름

```text
회원가입
→ 로그인
→ 프로필 존재 여부 확인 (GET /users/me/profile)
    ├─ 프로필 미완성 → 프로필 수정 화면 → 저장 → 분석 화면
    └─ 프로필 완성  → 분석 화면
→ 분석 세션 생성
→ 이미지 업로드
→ 리포트 조회
```

기본 리포트 화면은 `GET /analysis/sessions/{session_id}/report` 응답을 기준으로 구성한다.
단, 로그아웃/재로그인 후처럼 `current_session_id`가 비어 있으면 먼저 `GET /analysis/reports/latest`를 호출해 현재 로그인 사용자의 최신 완료 리포트를 복구한다.

추천 결과 API(`GET /recommendations/sessions/{session_id}`)는 리포트 화면에서 별도 조회가 필요할 때만 사용하는 보조 API다.

### 1. 회원가입

#### API

```http
POST /auth/signup
```

#### 요청
```json
{
  "email": "test@example.com",
  "password": "test1234",
  "name": "테스트"
}
```

#### 성공 후 동작
- 로그인 화면으로 이동한다.
- 성공 메시지를 표시한다.

### 2. 로그인

#### API

```http
POST /auth/login
```

#### 요청

```json
{
  "email": "test@example.com",
  "password": "test1234"
}
```
#### 응답
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

#### 프론트 처리
```
access_token → st.session_state["access_token"]
refresh_token → st.session_state["refresh_token"]
is_logged_in → True
```

#### 성공 후 동작

로그인 성공 직후 `GET /users/me/profile`을 호출해 프로필 완성 여부를 확인한다.

```text
프로필 미완성 또는 없음 → views/profile_edit.py 이동
프로필 완성             → views/analysis.py 이동
```

### 3. 프로필 조회

#### API

```http
GET /users/me/profile
```

#### 헤더
```http
Authorization: Bearer <access_token>
```

#### 프로필 완성 여부 판단 기준

아래 필드 중 하나라도 비어 있으면 프로필 미완성으로 간주한다.

```text
age
gender
skin_type
sensitive
main_concerns
allergy_ingredients
preferred_product_types
```

#### 라우팅 결정

```text
404 (프로필 없음)                  → views/profile_edit.py 이동
200이지만 필수 필드 중 하나라도 없음  → views/profile_edit.py 이동
200이고 필수 필드 모두 있음          → views/analysis.py 이동
```

### 4. 프로필 저장

#### API
```http
PUT /users/me/profile
```

#### 요청 예시
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

#### 중요성

추천 생성 시 아래 값이 사용된다.
```text
sensitive
allergy_ingredients
main_concerns
preferred_product_types
```

#### 성공 후 동작

```text
프로필 저장 성공 → views/analysis.py 이동
```

### 5. 분석 세션 생성

#### API
```http
POST /analysis/sessions
```
#### 요청
```json
{
  "session_name": "이미지 업로드 테스트",
  "input_type": "image"
}
```

#### 프론트 처리

응답의 id를 session_id로 저장한다.

```
st.session_state["current_session_id"] = response["id"]
```

#### 사용자 노출 여부

분석 세션 생성은 사용자에게 직접 보이지 않는다.

사용자 화면에서는 단순히 “분석 시작” 버튼을 누르는 흐름으로 보인다.

### 6. 이미지 업로드
#### API
```http
POST /analysis/sessions/{session_id}/images
```

#### 요청
```text
multipart/form-data
file: 이미지 파일
```
#### 사용자 화면 기준

사용자는 이미지만 업로드한다.

다음 값은 사용자에게 입력받지 않는다.

angle
facepart

#### 성공 후 동작
이미지 업로드가 완료되면 리포트 화면으로 이동한다.
session_id를 유지한다.

### 7. 분석 리포트 조회
#### API
```http
GET /analysis/sessions/{session_id}/report
```

#### 재로그인 후 최신 리포트 복구 API

```http
GET /analysis/reports/latest
```

#### 호출 기준

```text
current_session_id 있음
  -> GET /analysis/sessions/{session_id}/report

current_session_id 없음
  -> GET /analysis/reports/latest
     성공: response.session_id를 current_session_id로 복구하고 last_report 저장
     404: 분석 결과 없음 상태 표시
```

`session_id`는 분석마다 새로 생성되므로 localStorage에 저장해서 복구하지 않는다. 로그아웃 후 다른 계정으로 로그인할 수 있기 때문에, 현재 로그인 사용자 기준으로 백엔드가 최신 `completed` 세션을 찾는 방식이 기준이다.

#### 응답 주요 구조
```json
{
  "session_id": 1,
  "status": "completed",
  "overall_summary": {
    "status": "집중 관리 필요",
    "main_message": "눈가 부위의 주름, 볼 부위의 모공 관리가 필요합니다.",
    "main_issues": [
      {"issue_type": "wrinkle", "severity": "severe"},
      {"issue_type": "pore", "severity": "moderate"}
    ]
  },
  "part_reports": [
    {
      "display_part_name": "볼",
      "summary": "모공 관리가 필요합니다.",
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

#### issues[] 주요 필드 설명

| Field | 설명 |
|---|---|
| `grade_value` | 기존 서비스 호환용 등급값 (0~3) |
| `severity` | UI 표시 및 추천 로직 기준 상태값. `normal` / `mild` / `moderate` / `severe` |
| `predicted_value` | 이미지 기반 AI 모델 예측 회귀값. 이미지 업로드 경로에서 사용. 없으면 `null` |
| `measured_value` | AI-Hub JSON 또는 피부 측정 장비 기반 원본 수치. dev JSON 경로에서 사용. 없으면 `null` |

- 이미지 업로드 분석 경로: `predicted_value`가 채워지고 `measured_value`는 `null`
- dev JSON / AI-Hub JSON 경로: `measured_value`가 채워지고 `predicted_value`는 `null`
- 두 값이 모두 `null`이어도 `grade_value` / `severity` 기반 기존 화면은 정상 동작

#### 인증 실패 처리

API 응답이 401이면 다음 처리한다.
```
1. 세션 상태 초기화
2. 로그인 화면 이동
3. “로그인이 만료되었습니다. 다시 로그인해주세요.” 표시
```

### 8. 상세 측정값 조회 (Phase 2-2 추가)

#### API

```http
GET /analysis/sessions/{session_id}/metrics
```

#### 헤더

```http
Authorization: Bearer <access_token>
```

#### 호출 기준

리포트 조회(7번)가 완료되어 `session_id`와 `access_token`이 있는 경우에만 호출한다.

```text
report API 성공 + session_id 확인
  → metrics API 호출 (소프트 실패 허용)
     성공 + parts 있음: 상세 측정값 영역 표시
     성공 + parts=[]  : 상세 측정값 영역 숨김 (flat 세션)
     실패(404/5xx)    : 기존 리포트는 유지, 측정값 영역만 숨김
```

#### 응답 주요 구조

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
          "is_dummy": false,
          "dummy_reason": null,
          "source": "model"
        }
      ]
    }
  ]
}
```

#### 예외 처리

| 상황 | 처리 |
|---|---|
| metrics API 404 | 상세 측정값 영역 숨김 |
| metrics API 401 | 기존 인증 처리 흐름 유지 |
| metrics API 500 | 기존 리포트 유지, 측정값 영역만 숨김 |
| `parts=[]` | 상세 측정값 없음으로 처리 (오류 메시지 없음) |

### 9. 피부 측정값 추이 조회 (Phase 2-4 추가)

#### API

```http
GET /analysis/metrics/trends?raw_part_name=...&metric_group=...&metric_name=...&limit=10
```

#### 헤더

```http
Authorization: Bearer <access_token>
```

#### 호출 기준

리포트 화면에서 "추이 그래프 보기" 토글을 켤 때 한 번 호출한다. `st.session_state`에 결과를 캐시해 재호출을 방지한다. 기본 8개 지표에 대해 각각 호출한다.

전문가 모드가 켜져 있으면 기본 8개 차트 아래에 **지표 직접 선택** 섹션이 추가로 표시된다 (Phase 3-B). "추이 조회" 버튼 클릭 시 동일 API를 사용자가 선택한 `raw_part_name` / `metric_group` / `metric_name` 조합으로 호출한다. 결과는 `st.session_state[f"expert_trend_chart_{session_id}"]`에 캐시한다.

#### 예외 처리

| 상황 | 처리 |
|---|---|
| API 실패 | 해당 지표 차트 숨김 (기존 리포트 유지) |
| `trend=[]` | "분석 데이터가 없습니다." 안내 |
| trend 1개 | 현재 측정값 표시 + "2회 이상 분석 필요" 안내 |

### 10. 추천 결과 조회 (보조 API)

> 기본 리포트 화면은 7번 API만으로 구성한다. 이 API는 추천 결과를 별도로 확인하거나 디버깅할 때만 사용한다.

#### API

```http
GET /recommendations/sessions/{session_id}
```

#### 헤더

```http
Authorization: Bearer <access_token>
```

#### 사용 시점

- 리포트 화면에서 추천 데이터를 별도로 조회해야 할 때
- 추천 결과 단독 디버깅

### 에러 처리
- 400: 사용자 입력 오류
- 401: 인증 만료
- 403: 접근 권한 없음
- 404: 리소스 없음
- 500: 서버 오류

프론트에서는 에러 메시지를 사용자 친화적으로 변환하여 표시한다.

### 문서 갱신 규칙

API 경로, 요청 필드, 응답 필드, 인증 방식이 변경되면 이 문서를 즉시 수정한다.
