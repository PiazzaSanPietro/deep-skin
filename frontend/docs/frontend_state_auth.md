
# 6. `frontend/docs/frontend_state_auth.md`

# Frontend State & Auth Guide

## 목적

Streamlit에서 로그인 상태와 사용자 세션을 관리하기 위한 기준을 정의한다.

## session_state 키

사용할 주요 키는 다음과 같다.

```python
st.session_state["access_token"]
st.session_state["refresh_token"]
st.session_state["is_logged_in"]
st.session_state["current_user"]
st.session_state["current_session_id"]
st.session_state["last_report"]
st.session_state["current_page"]
st.session_state["profile_edit_from_login"]
```

`profile_edit_from_login`: 로그인 직후 프로필 미완성으로 profile_edit에 강제 진입한 경우 `True`로 설정한다. 이 경우 profile_edit 화면에서 취소 버튼을 숨긴다.

## 초기화 기준

앱 시작 시 키가 없으면 기본값을 설정한다.

```python
access_token = None
refresh_token = None
is_logged_in = False
current_user = None
current_session_id = None
last_report = None
current_page = "login"
profile_edit_from_login = False
```

## 로그인 성공 처리

로그인 API 성공 시 토큰을 저장한 뒤, 바로 analysis로 이동하지 않는다.
먼저 `GET /users/me/profile`을 호출해 프로필 완성 여부를 확인하고 이동 화면을 결정한다.

```python
st.session_state["access_token"] = response["access_token"]
st.session_state["refresh_token"] = response["refresh_token"]
st.session_state["is_logged_in"] = True
```

#### 프로필 완성 여부 확인 및 분기

로그인 직후 `GET /users/me/profile`을 호출하고 아래 기준으로 분기한다.

```text
404 (프로필 없음)
  → profile_edit_from_login = True
  → current_page = "profile_edit"

200이지만 아래 필수 필드 중 하나라도 None 또는 빈 값
  (age, gender, skin_type, sensitive,
   main_concerns, allergy_ingredients, preferred_product_types)
  → profile_edit_from_login = True
  → current_page = "profile_edit"

200이고 필수 필드 모두 존재
  → profile_edit_from_login = False
  → current_page = "analysis"
```

## 인증 헤더 생성

모든 인증 API 호출 시 다음 헤더를 붙인다.
```python
headers = {
    "Authorization": f"Bearer {st.session_state['access_token']}"
}
```

## 로그아웃 처리

로그아웃 버튼 클릭 시 다음 순서로 처리한다.
```
1. POST /auth/logout 호출
2. access_token = None
3. refresh_token = None
4. is_logged_in = False
5. current_user = None
6. current_session_id = None
7. last_report = None
8. profile_edit_from_login = False
9. current_page = “login”
10. 화면 rerun
```

## 401 처리

백엔드가 401을 반환하면 다음 처리한다.
```
1. “로그인이 만료되었습니다. 다시 로그인해주세요.” 메시지 표시
2. session_state 전체 초기화 (profile_edit_from_login 포함)
3. 로그인 화면으로 이동
```

## refresh token 처리

초기 MVP에서는 access token 만료 시 로그인 화면으로 이동한다.

추후 개선 시 다음 흐름을 추가할 수 있다.
```
401 발생
→ POST /auth/refresh 호출
→ 새 access_token 저장
→ 실패 시 로그인 화면 이동
```

## 페이지 접근 제한

로그인이 필요한 페이지:
```
profile
profile_edit
analysis
report
```

로그인하지 않은 상태에서 접근하면 로그인 화면으로 이동한다.

## 문서 갱신 규칙

인증 저장 방식, token 처리 방식, session_state 키가 변경되면 이 문서를 즉시 수정한다.