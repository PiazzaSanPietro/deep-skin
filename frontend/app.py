import streamlit as st

from styles.theme import inject_css

# ── 페이지 설정 (반드시 첫 번째 Streamlit 명령) ───────────────────────────
st.set_page_config(
    page_title="Deep Skin",
    page_icon="🧴",
    layout="wide",
    initial_sidebar_state="expanded",
)

_DEFAULTS = {
    "current_page":            "login",
    "access_token":            None,
    "refresh_token":           None,
    "is_logged_in":            False,
    "current_user":            None,
    "current_session_id":      None,
    "last_report":             None,
    "profile_data":            None,
    "profile_edit_from_login": False,
    "sidebar_collapsed":       False,
}

_PROTECTED = {"profile", "profile_edit", "analysis", "report"}


# ── 세션 초기화 ───────────────────────────────────────────────────────────────

def _init_session():
    for k, v in _DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── 인증 복구 (브라우저 새로고침 후 새 세션에서 한 번만 실행) ─────────────────

def _restore_auth():
    """
    _auth_init 플래그가 없을 때만 실행 (= 브라우저 새로고침 직후 새 세션).

    흐름:
      1) read_tokens() 로 localStorage 값을 읽는다.
         첫 render 에서는 JS 가 아직 실행되지 않아 None 을 반환한다.
         "로딩 중…" 을 표시하고 st.stop() 으로 대기.
         두 번째 render(JS rerun)에서 실제 값이 들어온다.
      2) 토큰이 있으면 GET /users/me/profile 로 유효성 검사.
      3) 401 이면 refresh_token 으로 재발급 시도.
      4) 재발급 성공 시 새 토큰을 queue_save_tokens() 로 예약.
      5) st.query_params 에서 page / sid 를 복구한다.
    """
    if st.session_state.get("_auth_init"):
        return

    from services.storage import read_tokens, queue_save_tokens
    from services import auth_api, user_api, api_client

    tokens = read_tokens()

    if tokens is None:
        # 첫 render — JS 컴포넌트 실행 대기
        st.markdown(
            '<div style="display:flex;align-items:center;justify-content:center;'
            'height:80vh;"><div style="color:#6B7894;font-size:14px;">로딩 중…</div></div>',
            unsafe_allow_html=True,
        )
        st.stop()
        return

    at = tokens["access_token"]
    rt = tokens["refresh_token"]

    if at:
        st.session_state["access_token"] = at
    if rt:
        st.session_state["refresh_token"] = rt

    # query_params 에서 page / session_id 복구 (URL 에 남아 있음)
    cp  = st.query_params.get("page")
    sid = st.query_params.get("sid")
    if sid:
        st.session_state["current_session_id"] = sid

    # 토큰 유효성 확인
    if at:
        profile = user_api.get_profile(at)
        if not api_client.is_error(profile):
            st.session_state["is_logged_in"] = True
            st.session_state["profile_data"] = profile
            _restore_page(cp)
        elif profile.get("_status") == 401:
            _attempt_refresh(rt, cp, queue_save_tokens, auth_api, api_client)
        # 그 외 오류(서버 다운 등) → 로그인 유지 안 함, 로그인 페이지 표시
    elif rt:
        _attempt_refresh(rt, cp, queue_save_tokens, auth_api, api_client)

    st.session_state["_auth_init"] = True

    # refresh 성공으로 토큰 저장이 예약됐으면 flush_pending 이 실행되도록 rerun
    if "_pending_storage" in st.session_state:
        st.rerun()


def _restore_page(cp: str | None):
    """로그인 상태일 때만 query_params 의 page 값으로 이동."""
    if cp and cp in _PROTECTED and st.session_state.get("is_logged_in"):
        st.session_state["current_page"] = cp


def _attempt_refresh(rt, cp, queue_save_tokens, auth_api, api_client):
    """refresh_token 으로 access_token 재발급. 성공 시 세션·토큰 갱신."""
    if not rt:
        return
    result = auth_api.refresh(rt)
    if api_client.is_error(result):
        return
    new_at = result.get("access_token")
    new_rt = result.get("refresh_token", rt)
    if not new_at:
        return
    st.session_state["access_token"]  = new_at
    st.session_state["refresh_token"] = new_rt
    st.session_state["is_logged_in"]  = True
    queue_save_tokens(new_at, new_rt)
    _restore_page(cp)


# ── query_params 동기화 (매 render) ──────────────────────────────────────────

def _sync_query_params():
    """session_state 의 page / session_id 를 URL query_params 에 반영."""
    requested_page = st.query_params.get("page")
    if (
        requested_page in {"login", "signup"}
        and not st.session_state.get("is_logged_in")
        and st.session_state.get("current_page") != requested_page
    ):
        st.session_state["current_page"] = requested_page

    page = st.session_state.get("current_page", "login")
    if st.query_params.get("page") != page:
        st.query_params["page"] = page

    sid = st.session_state.get("current_session_id")
    if sid:
        if str(st.query_params.get("sid", "")) != str(sid):
            st.query_params["sid"] = str(sid)
    elif "sid" in st.query_params:
        del st.query_params["sid"]


# ── 라우팅 ────────────────────────────────────────────────────────────────────

def _route():
    page = st.session_state["current_page"]

    # 이미 로그인된 상태에서 login/signup 접근 → analysis 로 리다이렉트
    if page in {"login", "signup"} and st.session_state["is_logged_in"]:
        st.session_state["current_page"] = "analysis"
        st.rerun()

    # 미인증 접근 차단
    if page in _PROTECTED and not st.session_state["is_logged_in"]:
        st.session_state["current_page"] = "login"
        st.rerun()

    # 인증 후 화면은 Streamlit 네이티브 sidebar 대신 항상 보이는 앱 내 좌측 메뉴를 사용한다.
    if st.session_state["is_logged_in"]:
        from components.layout import render_sidebar

        nav_width = 0.055 if st.session_state.get("sidebar_collapsed") else 0.18
        nav_col, page_col = st.columns([nav_width, 1 - nav_width], gap="large")
        with nav_col:
            render_sidebar()
        with page_col:
            _render_page(page)
        return

    _render_page(page)


def _render_page(page: str):
    # 라우팅
    if page == "login":
        from views.login import show
        show()
    elif page == "signup":
        from views.signup import show
        show()
    elif page == "profile_edit":
        from views.profile_edit import show
        show()
    elif page == "profile":
        from views.profile import show
        show()
    elif page == "analysis":
        from views.analysis import show
        show()
    elif page == "report":
        from views.report import show
        show()
    else:
        st.session_state["current_page"] = "login"
        st.rerun()


# ── 앱 진입점 ─────────────────────────────────────────────────────────────────

inject_css()
_init_session()

from services.storage import flush_pending
flush_pending()        # 1. 이전 render 에서 예약된 localStorage 쓰기 실행
_restore_auth()        # 2. localStorage → session_state 복구 (새 세션 1회)
_sync_query_params()   # 3. URL query_params ↔ session_state 동기화
_route()               # 4. 현재 페이지 렌더링
