import streamlit as st

from styles.theme import SEVERITY_LABEL, SEVERITY_COLOR


# ── 알림 ────────────────────────────────────────────────────────────────────

def show_error(msg: str):
    st.error(msg, icon="🚫")


def show_success(msg: str):
    st.success(msg, icon="✅")


def show_info(msg: str):
    st.info(msg, icon="ℹ️")


def handle_401():
    """
    401 수신 시 refresh_token 으로 access_token 재발급을 시도한다.
    성공: 새 토큰으로 세션 갱신 후 현재 페이지 재시도.
    실패: localStorage 삭제 예약 후 로그인 페이지로 이동.
    """
    from services import auth_api, api_client
    from services.storage import queue_save_tokens, queue_clear_tokens

    rt = st.session_state.get("refresh_token")
    if rt:
        result = auth_api.refresh(rt)
        if not api_client.is_error(result):
            new_at = result.get("access_token")
            new_rt = result.get("refresh_token", rt)
            if new_at:
                st.session_state["access_token"]  = new_at
                st.session_state["refresh_token"] = new_rt
                queue_save_tokens(new_at, new_rt)
                st.rerun()
                return

    # refresh 실패 또는 refresh_token 없음
    queue_clear_tokens()
    _reset_session()
    st.warning("로그인이 만료되었습니다. 다시 로그인해주세요.")
    st.rerun()


def _reset_session():
    keys = [
        "access_token", "refresh_token", "is_logged_in",
        "current_user", "current_session_id", "last_report",
        "profile_edit_from_login", "profile_data", "profile_form_data",
    ]
    for k in keys:
        st.session_state[k] = (
            None if ("token" in k or "user" in k or "report" in k or "session_id" in k)
            else False
        )
    st.session_state["profile_data"] = None
    st.session_state["profile_form_data"] = None
    st.session_state["is_logged_in"] = False
    st.session_state["profile_edit_from_login"] = False
    st.session_state["current_page"] = "login"
    try:
        st.query_params.clear()
    except Exception:
        pass


# ── 배지 / 칩 HTML ──────────────────────────────────────────────────────────

def severity_badge_html(severity: str) -> str:
    label = SEVERITY_LABEL.get(severity, severity)
    css_class = f"ds-badge ds-badge-{severity}"
    return f'<span class="{css_class}">{label}</span>'


def ingredient_chip_html(name: str, excluded: bool = False, reason_type: str | None = None) -> str:
    extra_class = "ds-chip-excluded" if excluded else ""
    tooltip = ""
    if reason_type == "allergy":
        tooltip = " title='알레르기 등록 성분'"
    elif reason_type == "sensitive":
        tooltip = " title='민감 피부 주의 성분'"
    return f'<span class="ds-chip {extra_class}"{tooltip}>{name}</span>'


def category_chip_html(name: str) -> str:
    return f'<span class="ds-chip ds-chip-category">{name}</span>'


def chips_row(items: list[str], excluded: bool = False) -> str:
    return " ".join(ingredient_chip_html(i, excluded=excluded) for i in items)


# ── 빈 상태 ──────────────────────────────────────────────────────────────────

def empty_state(message: str = "표시할 데이터가 없습니다."):
    st.markdown(f"""
    <div style="text-align:center; padding:48px 24px; color:#6B7280;">
        <div style="font-size:40px; margin-bottom:12px;">📭</div>
        <p style="font-size:15px;">{message}</p>
    </div>
    """, unsafe_allow_html=True)


render_empty_state = empty_state


# ── 인라인 카드 / 오류 박스 HTML ─────────────────────────────────────────────

def render_error_box(message: str):
    """st.error 대신 디자인 시스템 스타일의 인라인 오류 박스를 렌더링한다."""
    st.markdown(f"""
    <div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:10px;
                padding:12px 16px;color:#B91C1C;font-size:14px;
                display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        <span style="font-size:16px;">🚫</span>
        <span>{message}</span>
    </div>
    """, unsafe_allow_html=True)


def card_html(title: str, body_html: str, extra_class: str = "") -> str:
    """ds-card HTML 문자열을 반환한다. st.markdown(unsafe_allow_html=True)과 함께 사용."""
    cls = f"ds-card {extra_class}".strip()
    return f"""
    <div class="{cls}">
        <div class="ds-card-title">{title}</div>
        <div>{body_html}</div>
    </div>
    """
