import base64
import os

import streamlit as st

from services import auth_api, api_client
from components.common import show_error, show_success


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
    illust  = _icon("logo_image.png")
    prof    = _icon("profile.png")
    eml     = _icon("emali_g.png")
    pw      = _icon("password_g.png")
    twink   = _icon("twinkle.png")
    bg_wave = _icon("background_image2.png")
    _inject_css(prof, eml, pw, bg_wave)

    # ⚠️ 이 페이지에서 st.columns() 호출은 여기 딱 한 번만!
    #    내부에서 중첩 st.columns()를 쓰지 않아야 CSS 선택자가 정확히 동작함
    col_L, col_R = st.columns([12, 9])

    with col_L:
        _render_left(logo2, illust)

    with col_R:
        _render_right(twink)


# ── CSS ───────────────────────────────────────────────────────────────────────

def _inject_css(prof: str, eml: str, pw: str, bg_wave: str = ""):
    ic_prof = f"url('{prof}')" if prof else "none"
    ic_eml  = f"url('{eml}')" if eml else "none"
    ic_pw   = f"url('{pw}')" if pw else "none"
    bg_url  = f"url('{bg_wave}')" if bg_wave else "none"

    st.markdown(f"""
    <style>
    /* ── 페이지 ── */
    .stApp {{
        background-color: #EEF3FF !important;
        background-image: {bg_url} !important;
        background-repeat: no-repeat !important;
        background-position: bottom center !important;
        background-size: 100% auto !important;
    }}
    .block-container {{ padding: 0 !important; max-width: 100% !important; }}

    /* ── 최상위 2-열 레이아웃 (이 페이지에 stHorizontalBlock 은 이것 하나뿐) ── */
    [data-testid="stHorizontalBlock"] {{
        gap: 0 !important;
        align-items: stretch;
    }}
    /* 왼쪽 열 */
    [data-testid="stHorizontalBlock"] > div:first-child {{
        background: transparent;
        padding: 40px 48px !important;
        min-height: 100vh;
    }}
    /* 오른쪽 열 — 흰색 카드 */
    [data-testid="stHorizontalBlock"] > div:last-child {{
        background: #FFFFFF !important;
        min-height: 100vh;
        padding: 28px 44px 64px !important;
        box-shadow: -3px 0 28px rgba(75, 123, 255, 0.10);
        overflow: visible !important;
    }}

    /* ── 입력 아이콘 ── */
    input[placeholder="홍길동"] {{
        background-image: {ic_prof};
        background-repeat: no-repeat;
        background-size: 18px 18px;
        background-position: 14px center;
        padding-left: 42px !important;
    }}
    input[placeholder="이메일을 입력해주세요"] {{
        background-image: {ic_eml};
        background-repeat: no-repeat;
        background-size: 18px 18px;
        background-position: 14px center;
        padding-left: 42px !important;
    }}
    input[placeholder="4자 이상 입력"],
    input[placeholder="비밀번호를 다시 입력하세요"] {{
        background-image: {ic_pw};
        background-repeat: no-repeat;
        background-size: 18px 18px;
        background-position: 14px center;
        padding-left: 42px !important;
    }}

    /* ── 입력 필드: border는 컨테이너(div>div)에만, input·래퍼는 투명 ── */

    /* 1) 외곽 컨테이너 — border·배경 적용 */
    .stTextInput > div > div {{
        border: 1.5px solid #E4EAF5 !important;
        border-radius: 10px !important;
        background-color: #FAFBFF !important;
        box-shadow: none !important;
    }}
    .stTextInput > div > div:focus-within {{
        box-shadow: 0 0 0 3px rgba(75, 123, 255, 0.12) !important;
    }}
    /* 2) 실제 input — border 없음, 배경 투명 */
    .stTextInput > div > div > input {{
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        background: transparent !important;
        padding-top: 12px !important;
        padding-bottom: 12px !important;
        font-size: 14px !important;
        color: #0F2447 !important;
    }}
    .stTextInput > div > div > input:focus,
    .stTextInput > div > div > input:active {{
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
    }}
    /* 3) 눈 아이콘 래퍼 div — 배경·border 제거, 내부 패딩 제거 */
    .st-bz {{
        padding-right: 0 !important;
    }}
    .st-cj {{
        padding-right: 0 !important;
    }}
    .st-emotion-cache-tn0cau {{
        gap: 0 !important;
    }}
    .stTextInput > div > div > div {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}
    /* 4) 눈 아이콘 버튼 자체 */
    [data-testid="passwordInputVisibilityToggle"] {{
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        outline: none !important;
        padding: 0 8px !important;
    }}
    [data-testid="passwordInputVisibilityToggle"]:hover,
    [data-testid="passwordInputVisibilityToggle"]:focus {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
    }}
    /* "Press Enter to submit form" 힌트 숨김 */
    [data-testid="InputInstructions"] {{
        display: none !important;
    }}
    .stTextInput > label {{
        font-size: 13px !important;
        font-weight: 600 !important;
        color: #3A4A6B !important;
    }}

    /* ── 폼 컨테이너 ── */
    [data-testid="stForm"] {{
        border: 1.5px solid #E8EDF8 !important;
        border-radius: 16px !important;
        padding: 24px 24px 24px !important;
        background: #FFFFFF !important;
        overflow: visible !important;
    }}

    /* ── 회원가입 버튼 ── */
    .stForm [data-testid="stFormSubmitButton"] > button {{
        background: linear-gradient(135deg, #4B7BFF 0%, #3DD9C5 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 12px !important;
        font-size: 15px !important;
        font-weight: 700 !important;
        padding: 13px !important;
        width: 100%;
        margin-top: 6px;
        box-shadow: 0 4px 18px rgba(75, 123, 255, 0.30) !important;
        transition: box-shadow 0.2s, transform 0.15s;
    }}
    .stForm [data-testid="stFormSubmitButton"] > button:hover {{
        box-shadow: 0 6px 26px rgba(75, 123, 255, 0.45) !important;
        transform: translateY(-1px);
    }}

    /* ── 로그인 버튼 ── */
    div[data-testid="stButton"] > button {{
        border-radius: 10px !important;
        font-size: 14px !important;
        font-weight: 600 !important;
    }}
    </style>
    """, unsafe_allow_html=True)


# ── 왼쪽 패널 — st.columns 미사용, 이미지는 st.markdown 호출 분리 ─────────────
# 이유: base64 이미지를 하나의 거대한 st.markdown에 합치면 Streamlit이
#       HTML 렌더링에 실패하고 텍스트 소스를 그대로 출력한다.

def _render_left(logo2: str, illust: str):
    # 1) 로고 — 별도 markdown 호출
    if logo2:
        st.markdown(
            f'<img src="{logo2}" style="height:80px;display:block;margin-bottom:28px;">',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="font-size:20px;font-weight:800;color:#0F2447;margin-bottom:28px;">'
            '🌿 Deep Skin</div>',
            unsafe_allow_html=True,
        )

    # 2) 헤드라인 + 서브타이틀 — 이미지 없음
    st.markdown("""
    <div style="font-size:36px;font-weight:800;color:#0F2447;
                line-height:1.3;letter-spacing:-0.02em;margin-bottom:12px;">
        AI로 더 깊이,<br>피부를 더 정확하게
    </div>
    <div style="font-size:14px;color:#6B7894;line-height:1.75;margin-bottom:24px;">
        딥 스킨 AI로 지금 바로 피부 상태를 분석하고<br>
        맞춤형 스킨케어 루틴을 시작해보세요.
    </div>
    """, unsafe_allow_html=True)

    # 3) 중앙 일러스트 — 이미지 1개만 포함한 별도 markdown 호출
    if illust:
        st.markdown(
            f'<div style="text-align:center;margin:4px 0 24px;">'
            f'<img src="{illust}" style="max-width:300px;width:80%;">'
            f'</div>',
            unsafe_allow_html=True,
        )

    # 4) 하단 3열 피처 — 이미지 없음 (이모지 아이콘 사용)
    st.markdown("""
    <div style="display:flex;gap:0;
                border-top:1px solid #E8EDF5;padding-top:16px;margin-top:4px;">
        <div style="flex:1;text-align:center;padding:12px 8px;">
            <div style="font-size:28px;margin-bottom:8px;">💧</div>
            <div style="font-size:12px;font-weight:700;color:#0F2447;margin-bottom:4px;">
                정밀한 피부 분석</div>
            <div style="font-size:11px;color:#6B7894;line-height:1.55;">
                AI가 7가지 피부 지표를<br>정밀하게 측정합니다.</div>
        </div>
        <div style="flex:1;text-align:center;padding:12px 8px;">
            <div style="font-size:28px;margin-bottom:8px;">✨</div>
            <div style="font-size:12px;font-weight:700;color:#0F2447;margin-bottom:4px;">
                맞춤형 솔루션 제안</div>
            <div style="font-size:11px;color:#6B7894;line-height:1.55;">
                내 피부 고민에 맞는<br>성분과 제품을 추천합니다.</div>
        </div>
        <div style="flex:1;text-align:center;padding:12px 8px;">
            <div style="font-size:28px;margin-bottom:8px;">🛡️</div>
            <div style="font-size:12px;font-weight:700;color:#0F2447;margin-bottom:4px;">
                안전한 성분 필터링</div>
            <div style="font-size:11px;color:#6B7894;line-height:1.55;">
                알레르기 성분을<br>자동으로 제외합니다.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── 오른쪽 패널 — HTML 헤더 + st.form (st.columns 미사용) ────────────────────

def _render_right(twink: str):
    sparkle = (
        f'<img src="{twink}" width="24" style="vertical-align:middle;margin-left:4px;">'
        if twink else "✦"
    )

    # 폼 타이틀
    st.markdown(f"""
    <div style="margin-bottom:20px;">
        <div style="font-size:26px;font-weight:800;color:#0F2447;
                    display:inline-flex;align-items:center;gap:4px;">
            회원가입 {sparkle}
        </div>
        <div style="font-size:13px;color:#6B7894;margin-top:6px;line-height:1.65;">
            정보를 입력하여 무료로 시작하세요.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 입력 폼 (st.form 유지)
    with st.form("signup_form", clear_on_submit=False):
        name             = st.text_input("이름",          placeholder="홍길동")
        email            = st.text_input("이메일",        placeholder="이메일을 입력해주세요")
        password         = st.text_input("비밀번호",      type="password", placeholder="4자 이상 입력")
        password_confirm = st.text_input("비밀번호 확인", type="password",
                                         placeholder="비밀번호를 다시 입력하세요")
        st.markdown('<div style="height:2px;"></div>', unsafe_allow_html=True)
        submitted = st.form_submit_button("회원가입", use_container_width=True)

    if submitted:
        _handle_signup(name, email, password, password_confirm)

    # 로그인 링크
    st.markdown("""
    <div style="margin-top:18px;text-align:center;font-size:13px;color:#6B7894;">
        이미 계정이 있으신가요?
    </div>
    """, unsafe_allow_html=True)

    if st.button("로그인", key="go_login", use_container_width=True):
        st.session_state["current_page"] = "login"
        st.rerun()


# ── 회원가입 처리 ─────────────────────────────────────────────────────────────

def _handle_signup(name: str, email: str, password: str, password_confirm: str):
    if not all([name, email, password, password_confirm]):
        show_error("모든 항목을 입력해주세요.")
        return
    if password != password_confirm:
        show_error("비밀번호가 일치하지 않습니다.")
        return
    if len(password) < 4:
        show_error("비밀번호는 4자 이상이어야 합니다.")
        return

    with st.spinner("회원가입 중..."):
        result = auth_api.signup(email, password, name)

    if api_client.is_error(result):
        show_error(api_client.get_error_message(result))
        return

    show_success("회원가입이 완료되었습니다. 로그인해주세요.")
    st.session_state["current_page"] = "login"
    st.rerun()
