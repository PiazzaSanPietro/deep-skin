
# Frontend State & Auth Guide

## 목적

Streamlit에서 로그인 상태와 사용자 세션을 관리하기 위한 기준을 정의한다.  
브라우저 새로고침(F5) 후에도 로그인 상태를 복구하기 위해 토큰을 localStorage에 저장한다.

---

## session_state 키

```python
st.session_state["access_token"]            # str | None
st.session_state["refresh_token"]           # str | None
st.session_state["is_logged_in"]            # bool
st.session_state["current_user"]            # dict | None
st.session_state["current_session_id"]      # str | None
st.session_state["last_report"]             # dict | None
st.session_state["current_page"]            # str  (기본값: "login")
st.session_state["profile_edit_from_login"] # bool
```

`profile_edit_from_login`: 로그인 직후 프로필 미완성으로 profile_edit에 강제 진입한 경우 `True`.  
이 경우 profile_edit 화면에서 취소 버튼을 숨긴다.

---

## 토큰 영속성 (localStorage)

토큰은 `services/storage.py`를 통해 브라우저 localStorage에 저장된다.

| localStorage key | 내용 |
|---|---|
| `ds_at` | access_token |
| `ds_rt` | refresh_token |

### 읽기 (`read_tokens`)

`streamlit_js_eval`을 사용해 localStorage 값을 Python으로 읽는다.  
access_token과 refresh_token은 하나의 hidden component에서 함께 읽고, component iframe 높이는 0으로 유지한다.
첫 번째 render에서는 JS가 아직 실행되지 않아 `None`을 반환한다.  
두 번째 render(JS rerun 후)에서 실제 값이 반환된다.

```python
from services.storage import read_tokens
tokens = read_tokens()
# None → 첫 render (JS 대기 중)
# {"access_token": str|None, "refresh_token": str|None} → 두 번째 render
```

### 쓰기 (큐 방식)

`st.components.v1.html`로 JS를 주입하는 방식은 `st.rerun()` 직전에 호출하면 component가 폐기된다.  
따라서 쓰기 작업은 큐에 등록하고, 다음 render 시작 시점(flush_pending)에 실제 실행한다.

```python
from services.storage import queue_save_tokens, queue_clear_tokens
queue_save_tokens(access_token, refresh_token)  # 저장 예약
queue_clear_tokens()                             # 삭제 예약
```

`app.py`의 `flush_pending()`이 각 render 최초에 호출되어 예약된 작업을 실행한다.

---

## 앱 진입점 실행 순서 (app.py)

```python
inject_css()          # 1. 스타일 주입
_init_session()       # 2. session_state 기본값 설정
flush_pending()       # 3. 예약된 localStorage 쓰기 실행
_restore_auth()       # 4. localStorage → session_state 복구 (새 세션 1회)
_sync_query_params()  # 5. URL query_params ↔ session_state 동기화
_route()              # 6. 현재 페이지 렌더링
```

---

## 브라우저 새로고침 후 인증 복구 (_restore_auth)

`_auth_init` 플래그로 세션당 1회만 실행된다.

```
1. read_tokens() 호출
   - None 반환 (첫 render) → "로딩 중…" 표시 후 st.stop()
   - 두 번째 render에서 실제 값 반환
2. at 토큰 있으면 GET /users/me/profile 호출
   - 성공(200) → is_logged_in=True, query_params["page"]로 페이지 복구
   - 401 → refresh_token으로 재발급 시도 (_attempt_refresh)
3. at 없고 rt 있으면 바로 _attempt_refresh 시도
4. _auth_init = True 설정 (이후 render에서 재실행 방지)
5. refresh 성공으로 _pending_storage 있으면 st.rerun()
```

---

## 페이지 / 세션 ID 복구 (query_params)

민감하지 않은 상태(현재 페이지, 세션 ID)는 URL query_params에 저장한다.  
localStorage 대신 query_params를 사용하므로 JS 없이 동기적으로 접근 가능하다.

| query_params 키 | 내용 |
|---|---|
| `page` | 현재 페이지 이름 |
| `sid` | current_session_id |

`sid`는 현재 브라우저 세션에서 편의상 유지하는 값이며, 로그아웃 후 다른 계정으로 로그인할 수 있으므로 localStorage에 영구 저장하지 않는다. 재로그인 후 `current_session_id`가 비어 있는 상태에서 리포트 화면에 들어가면 `GET /analysis/reports/latest`로 현재 로그인 사용자의 최신 완료 리포트를 복구한다.

`_sync_query_params()`가 매 render 마다 session_state 값으로 동기화한다.

---

## 로그인 성공 처리

```python
# views/login.py → _handle_login()
st.session_state["access_token"]  = result["access_token"]
st.session_state["refresh_token"] = result["refresh_token"]
st.session_state["is_logged_in"]  = True
queue_save_tokens(result["access_token"], result["refresh_token"])  # localStorage 저장 예약
```

이후 `GET /users/me/profile`로 프로필 완성 여부를 확인하고 화면을 결정한다.

```
404 (프로필 없음)
  → profile_edit_from_login = True
  → current_page = "profile_edit"

200이지만 필수 필드 미완성
  (age, gender, skin_type, sensitive,
   main_concerns, allergy_ingredients, preferred_product_types)
  → profile_edit_from_login = True
  → current_page = "profile_edit"

200이고 필수 필드 모두 존재
  → profile_edit_from_login = False
  → current_page = "analysis"
```

---

## 로그아웃 처리

```python
# components/layout.py → _do_logout()
auth_api.logout(token)   # POST /auth/logout
queue_clear_tokens()     # localStorage 삭제 예약
_reset_session()         # session_state 초기화 + query_params.clear()
st.rerun()
```

로그아웃 시 `current_session_id`와 `last_report`도 초기화된다. 이후 같은 계정으로 다시 로그인해 리포트 메뉴에 들어가면 프론트는 기존 `session_id`를 저장소에서 찾지 않고, 백엔드 최신 리포트 API를 호출해 아래 값을 다시 채운다.

```python
st.session_state["current_session_id"] = latest_report["session_id"]
st.session_state["last_report"] = latest_report
```

---

## 401 처리 (handle_401)

API 응답 401 수신 시 `components/common.py`의 `handle_401()`을 호출한다.

```
1. refresh_token 있으면 POST /auth/refresh 시도
   - 성공 → 새 토큰으로 session_state 갱신 + queue_save_tokens + st.rerun()
   - 실패 또는 refresh_token 없음 →
       queue_clear_tokens()
       _reset_session()  (session_state 초기화 + query_params.clear())
       경고 메시지 표시
       st.rerun() → 로그인 화면
```

---

## 인증 헤더 생성

모든 인증 API 호출 시 다음 헤더를 붙인다.

```python
headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
```

---

## 페이지 접근 제한

로그인이 필요한 페이지 (`_PROTECTED`):

```
profile, profile_edit, analysis, report
```

미인증 상태에서 접근하면 로그인 화면으로 리다이렉트한다.  
이미 로그인된 상태에서 login/signup 접근하면 analysis로 리다이렉트한다.

---

## 문서 갱신 규칙

인증 저장 방식, token 처리 방식, session_state 키, localStorage 키가 변경되면 이 문서를 즉시 수정한다.
