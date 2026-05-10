
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
```
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
```

## 로그인 성공 처리

로그인 API 성공 시 다음을 저장한다.
```python
st.session_state["access_token"] = response["access_token"]
st.session_state["refresh_token"] = response["refresh_token"]
st.session_state["is_logged_in"] = True
st.session_state["current_page"] = "analysis"
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
2. access_token 삭제
3. refresh_token 삭제
4. is_logged_in = False
5. current_page = "login"
6. 화면 rerun
```

## 401 처리

백엔드가 401을 반환하면 다음 처리한다.
```
1. “로그인이 만료되었습니다. 다시 로그인해주세요.” 메시지 표시
2. session_state 초기화
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
analysis
report
```

로그인하지 않은 상태에서 접근하면 로그인 화면으로 이동한다.

## 문서 갱신 규칙

인증 저장 방식, token 처리 방식, session_state 키가 변경되면 이 문서를 즉시 수정한다.