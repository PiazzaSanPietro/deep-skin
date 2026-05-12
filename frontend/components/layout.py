import base64
import os

import streamlit as st

from services import auth_api
from components.common import _reset_session

# ── 아이콘 로드 헬퍼 ─────────────────────────────────────────────────────────

def _icon_b64(rel: str) -> str:
    path = os.path.join("assets", "icons", rel)
    try:
        with open(path, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    except Exception:
        return ""


def _logo_b64(fn: str) -> str:
    path = os.path.join("assets", "logo", fn)
    try:
        with open(path, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    except Exception:
        return ""


def _img_tag(rel: str, size: int = 22) -> str:
    src = _icon_b64(rel)
    if not src:
        return ""
    return (
        f'<img src="{src}" width="{size}" height="{size}" '
        f'style="object-fit:contain;vertical-align:middle;flex-shrink:0;">'
    )


# ── 네비게이션 정의 ──────────────────────────────────────────────────────────

_NAV_ITEMS = [
    ("분석 시작", "analysis", "analysis.png", ":material/analytics:"),
    ("리포트",   "report",   "report.png",   ":material/description:"),
    ("프로필",   "profile",  "profile.png",  ":material/person:"),
]


# ── 사이드바 렌더링 ──────────────────────────────────────────────────────────

def render_sidebar():
    if st.session_state.get("sidebar_collapsed"):
        _render_sidebar_collapsed()
        return

    current   = st.session_state.get("current_page", "")
    logo2_src = _logo_b64("logo_2.png")

    with st.container(key="ds_sidebar_expanded"):
        _render_sidebar_header(logo2_src, collapsed=False)

        st.markdown('<div class="ds-sidebar-rule"></div>', unsafe_allow_html=True)
        st.markdown('<div class="ds-nav-section">MENU</div>', unsafe_allow_html=True)

        for label, page, icon_rel, icon in _NAV_ITEMS:
            if current == page:
                icon_tag = _img_tag(icon_rel, 18)
                st.markdown(
                    f'<div class="ds-nav-active">'
                    f'{icon_tag}'
                    f'<span>{label}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            elif st.button(label, key=f"nav_{page}", icon=icon, width="stretch"):
                st.session_state["current_page"] = page
                st.rerun()

        st.markdown('<div class="ds-sidebar-rule ds-sidebar-rule-spaced"></div>', unsafe_allow_html=True)

        with st.container(key="ds_sidebar_info"):
            st.markdown(
                """
                <div class="ds-sidebar-info-card">
                    <div class="ds-sidebar-info-title">✦ Deep Skin AI</div>
                    <div class="ds-sidebar-info-text">
                        AI로 당신의 피부를<br>더 깊이 이해하세요.
                    </div>
                    <div class="ds-sidebar-quota">
                        <div class="ds-sidebar-quota-row">
                            <span>오늘의 분석 가능 횟수</span>
                            <strong>3/5</strong>
                        </div>
                        <div class="ds-sidebar-quota-track">
                            <div class="ds-sidebar-quota-fill"></div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with st.container(key="ds_sidebar_logout"):
            if st.button("로그아웃", key="nav_logout", icon=":material/logout:", width="stretch"):
                _do_logout()


def _render_sidebar_collapsed():
    current = st.session_state.get("current_page", "")

    with st.container(key="ds_sidebar_collapsed"):
        _render_sidebar_header("", collapsed=True)
        st.markdown('<div class="ds-collapsed-divider"></div>', unsafe_allow_html=True)

        for _, page, icon_rel, icon in _NAV_ITEMS:
            if current == page:
                st.markdown(
                    f'<div class="ds-collapsed-nav-active" title="{_page_help(page)}">'
                    f'{_img_tag(icon_rel, 19)}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                continue
            if st.button(" ", key=f"nav_icon_{page}", icon=icon, help=_page_help(page), width="content"):
                st.session_state["current_page"] = page
                st.rerun()

        with st.container(key="ds_sidebar_collapsed_logout"):
            if st.button(" ", key="nav_logout_collapsed", icon=":material/logout:", help="로그아웃", width="content"):
                _do_logout()


def _render_sidebar_header(logo2_src: str, collapsed: bool):
    if collapsed:
        if st.button(" ", key="sidebar_expand", icon=":material/menu:", help="메뉴 펼치기", width="content"):
            st.session_state["sidebar_collapsed"] = False
            st.rerun()
        return

    logo_html = (
        f'<img src="{logo2_src}" style="height:32px;object-fit:contain;">'
        if logo2_src else
        '<span style="font-size:17px;font-weight:800;color:#0F2447;">Deep Skin</span>'
    )

    with st.container(key="ds_sidebar_header", horizontal=True, vertical_alignment="center"):
        st.markdown(f'<div class="ds-sidebar-logo">{logo_html}</div>', unsafe_allow_html=True)
        if st.button(" ", key="sidebar_collapse", icon=":material/menu:", help="메뉴 닫기", width="content"):
            st.session_state["sidebar_collapsed"] = True
            st.rerun()


def _do_logout():
    from services.storage import queue_clear_tokens
    token = st.session_state.get("access_token")
    if token:
        auth_api.logout(token)
    queue_clear_tokens()
    _reset_session()
    st.rerun()


def _page_help(page: str) -> str:
    labels = {
        "analysis": "분석 시작",
        "report": "리포트",
        "profile": "프로필",
    }
    return labels.get(page, page)


# ── 페이지 헤더 ──────────────────────────────────────────────────────────────

def render_page_title(title: str, subtitle: str = ""):
    render_page_header(title, subtitle)


def render_page_header(title: str, subtitle: str = ""):
    st.markdown(
        f'<div class="ds-page-title">{title}</div>'
        + (
            f'<div class="ds-page-subtitle">{subtitle}</div>'
            if subtitle
            else '<div style="margin-bottom:24px;"></div>'
        ),
        unsafe_allow_html=True,
    )
