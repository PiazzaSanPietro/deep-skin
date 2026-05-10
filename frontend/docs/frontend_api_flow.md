
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

#### 응답 주요 구조
```json
{
  "session_id": 1,
  "status": "completed",
  "overall_summary": {
    "status": "집중 관리 필요",
    "main_message": "눈가 부위의 주름, 볼 부위의 모공 관리가 필요합니다.",
    "main_issues": []
  },
  "part_reports": []
}
```

#### 인증 실패 처리

API 응답이 401이면 다음 처리한다.
```
1. 세션 상태 초기화
2. 로그인 화면 이동
3. “로그인이 만료되었습니다. 다시 로그인해주세요.” 표시
```

### 8. 추천 결과 조회 (보조 API)

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