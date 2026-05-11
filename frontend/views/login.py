import base64
import os

import streamlit as st

from services import auth_api, user_api, api_client
from components.common import show_error
from styles.css_loader import load_css_with_vars


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _b64(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    except Exception:
        return ""

def _icon(fn: str) -> str:
    return _b64(os.path.join("assets", "icons", fn))

def _logo(fn: str) -> str:
    return _b64(os.path.join("assets", "logo", fn))


# ── 진입점 ───────────────────────────────────────────────────────────────────

def show():
    logo2   = _logo("logo_2.png")
    illust  = _icon("background_image.png")
    ic_eml  = _icon("emali_g.png")
    ic_pw   = _icon("password_g.png")
    ic_ana  = _icon("analysis.png")
    ic_sol  = _icon("solution.png")
    ic_prot = _icon("profile.png")
    bg_wave = _icon("background_image2.png")

    _inject_css(ic_eml, ic_pw, bg_wave)

    col_L, col_C, col_R = st.columns([5, 6, 4])

    with col_L:
        _render_left(logo2, ic_ana, ic_sol, ic_prot)

    with col_C:
        _render_center()

    with col_R:
        _render_right(illust)

    _render_footer()


# ── CSS ───────────────────────────────────────────────────────────────────────

def _inject_css(ic_eml: str, ic_pw: str, bg_wave: str = ""):
    ic_eml_url = f"url('{ic_eml}')" if ic_eml else "none"
    ic_pw_url  = f"url('{ic_pw}')" if ic_pw else "none"
    bg_url     = f"url('{bg_wave}')" if bg_wave else "none"

    load_css_with_vars(
        "login.css",
        {
            "--ds-login-bg": bg_url,
            "--ds-login-email-icon": ic_eml_url,
            "--ds-login-password-icon": ic_pw_url,
        },
    )


# ── 왼쪽 패널 — 브랜드 영역 ───────────────────────────────────────────────────
# 이미지는 st.markdown 호출당 1개만 포함 (다수 base64를 합치면 HTML 렌더 실패)

def _render_left(logo2: str, ic_ana: str, ic_sol: str, ic_prot: str):

    # 1) 로고
    if logo2:
        st.markdown(
            f'<img src="{logo2}" style="height:80px;display:block;margin-bottom:40px;">',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="font-size:22px;font-weight:800;color:#0F2447;margin-bottom:40px;">'
            '🌿 Deep Skin</div>',
            unsafe_allow_html=True,
        )

    # 2) 헤드라인 + 설명 — 이미지 없음
    st.markdown("""
    <div style="margin-bottom:36px;">
        <div style="font-size:36px;font-weight:800;color:#0F2447;
                    line-height:1.3;letter-spacing:-0.02em;margin-bottom:14px;">
            AI로 더 정확하게,<br>나만을 위한 피부 케어
        </div>
        <div style="font-size:14px;color:#6B7894;line-height:1.75;">
            Deep Skin은 AI 기술로 피부 상태를 정밀 분석하여<br>
            당신에게 꼭 맞는 스킨케어 솔루션을 제공합니다.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3) 기능 아이템 — 아이콘 1개씩 별도 markdown 호출
    features = [
        (ic_ana,  "정밀 AI 피부 분석",    "딥러닝 기반으로 피부 고민을 정밀 분석"),
        (ic_sol,  "맞춤형 스킨케어 추천", "개인별 피부 타입과 고민에 맞는 솔루션 제안"),
        (ic_prot, "안전한 데이터 관리",   "개인정보는 안전하게 보호되며 분석에만 활용"),
    ]
    for ic_src, title, desc in features:
        icon_inner = (
            f'<img src="{ic_src}" width="24" height="24" style="object-fit:contain;">'
            if ic_src else "🔬"
        )
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:14px;'
            f'background:#FFFFFF;border-radius:14px;padding:14px 18px;'
            f'margin-bottom:10px;border:1px solid #EEF4FF;'
            f'box-shadow:0 2px 8px rgba(15,36,71,0.05);">'
            f'<div style="width:44px;height:44px;flex-shrink:0;border-radius:12px;'
            f'background:linear-gradient(135deg,#EEF4FF 0%,#E8EDFF 100%);'
            f'display:flex;align-items:center;justify-content:center;">'
            f'{icon_inner}</div>'
            f'<div>'
            f'<div style="font-size:13px;font-weight:700;color:#0F2447;">{title}</div>'
            f'<div style="font-size:12px;color:#6B7894;margin-top:2px;">{desc}</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── 가운데 패널 — 로그인 카드 ─────────────────────────────────────────────────

def _render_center():

    with st.container(key="login_panel"):
        with st.form("login_form", clear_on_submit=False):
            st.markdown("""
            <div style="text-align:center;margin-bottom:34px;">
                <div style="font-size:34px;font-weight:800;color:#183467;margin-bottom:16px;line-height:1.2;">로그인</div>
                <div style="font-size:14px;color:#68758E;line-height:1.65;">
                    계정에 로그인하고 피부 분석을 시작하세요.
                </div>
            </div>
            """, unsafe_allow_html=True)

            email    = st.text_input("이메일",  placeholder="이메일을 입력해주세요")
            password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력해주세요")
            st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)
            submitted = st.form_submit_button("로그인", width="stretch")

        if submitted:
            _handle_login(email, password)

        # 비밀번호 찾기 링크
        st.markdown("""
        <div style="text-align:center;margin-top:18px;">
            <span style="font-size:13px;color:#8E76E5;font-weight:800;text-decoration:underline;cursor:pointer;">
                비밀번호를 잊으셨나요?
            </span>
        </div>
        """, unsafe_allow_html=True)

        # 회원가입 안내
        st.markdown("""
        <div class="ds-login-divider"></div>
        <div class="ds-signup-inline">
            <span>계정이 없으신가요?</span>
            <a href="?page=signup" target="_self">회원가입</a>
        </div>
        """, unsafe_allow_html=True)


# ── 오른쪽 패널 — 일러스트 ────────────────────────────────────────────────────

def _render_right(illust: str):

    if illust:
        st.markdown(
            f'<div style="text-align:center;padding:8px 0;">'
            f'<img src="{illust}" style="max-width:100%;width:85%;'
            f'opacity:0.90;filter:drop-shadow(0 8px 32px rgba(75,123,255,0.15));">'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── 푸터 ─────────────────────────────────────────────────────────────────────

def _render_footer():
    st.markdown("""
    <div class="ds-login-footer">
        <span style="font-size:11px;color:#A0AABB;">© 2024 Deep Skin. All rights reserved.</span>
        <div style="display:flex;gap:16px;font-size:11px;color:#A0AABB;">
            <span style="cursor:pointer;">이용약관</span>
            <span>|</span>
            <span style="cursor:pointer;">개인정보 처리방침</span>
            <span>|</span>
            <span style="cursor:pointer;">문의하기</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── 로그인 처리 ──────────────────────────────────────────────────────────────

def _handle_login(email: str, password: str):
    if not email or not password:
        show_error("이메일과 비밀번호를 모두 입력해주세요.")
        return

    with st.spinner("로그인 중..."):
        result = auth_api.login(email, password)

    if api_client.is_error(result):
        show_error(api_client.get_error_message(result))
        return

    st.session_state["access_token"]  = result["access_token"]
    st.session_state["refresh_token"] = result["refresh_token"]
    st.session_state["is_logged_in"]  = True

    from services.storage import queue_save_tokens
    queue_save_tokens(result["access_token"], result["refresh_token"])

    _check_profile_and_route()


def _check_profile_and_route():
    token = st.session_state["access_token"]

    with st.spinner("프로필 확인 중..."):
        profile = user_api.get_profile(token)

    status = profile.get("_status")

    if status == 404:
        st.session_state["profile_edit_from_login"] = True
        st.session_state["current_page"] = "profile_edit"
    elif api_client.is_error(profile):
        st.session_state["current_page"] = "analysis"
    elif user_api.is_profile_complete(profile):
        st.session_state["profile_edit_from_login"] = False
        st.session_state["current_page"] = "analysis"
    else:
        st.session_state["profile_edit_from_login"] = True
        st.session_state["current_page"] = "profile_edit"

    st.rerun()
