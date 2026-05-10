import streamlit as st

from services import user_api, api_client
from components.common import show_error, handle_401
from components.layout import render_page_header
from components import profile_cards


# ── 진입점 ───────────────────────────────────────────────────────────────────

def show():
    render_page_header(
        "내 프로필",
        "개인 정보를 확인하고 피부 분석 맞춤 설정을 관리하세요.",
    )

    token = st.session_state.get("access_token")
    with st.spinner("프로필을 불러오는 중..."):
        profile = user_api.get_profile(token)

    if api_client.is_error(profile):
        if profile.get("_status") == 401:
            handle_401()
            return
        show_error(api_client.get_error_message(profile))
        return

    if not user_api.is_profile_complete(profile):
        st.info("프로필이 완성되지 않았습니다. 프로필을 먼저 입력해주세요.", icon="💡")

    _render_profile(profile)


# ── 프로필 렌더링 ─────────────────────────────────────────────────────────────

def _render_profile(profile: dict):
    # 상단 프로필 헤더 카드 (전체 너비)
    profile_cards.render_profile_summary(profile)

    # 카드 그리드: 좌(기본·피부·선호제품·계정) / 우(고민·알레르기·분석힌트)
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        profile_cards.render_basic_info_card(profile)
        profile_cards.render_skin_info_card(profile)
        profile_cards.render_products_card(profile)
        profile_cards.render_account_card(profile)

    with col_right:
        profile_cards.render_concerns_card(profile)
        profile_cards.render_allergy_card(profile)
        _render_analysis_hint()

    # 하단 버튼
    st.markdown(
        '<hr style="border:none;border-top:1px solid #E4EAF5;margin:8px 0 20px;">',
        unsafe_allow_html=True,
    )
    col_edit, col_analysis, _ = st.columns([1, 1, 2])
    with col_edit:
        if st.button("✏️  프로필 수정", use_container_width=True):
            if "profile_form_data" in st.session_state:
                del st.session_state["profile_form_data"]
            st.session_state["profile_edit_from_login"] = False
            st.session_state["current_page"] = "profile_edit"
            st.rerun()
    with col_analysis:
        if st.button("🔬  리포트 바로가기", use_container_width=True):
            st.session_state["current_page"] = "report"
            st.rerun()


def _render_analysis_hint():
    session_id = st.session_state.get("current_session_id")
    if session_id:
        st.markdown(f"""
        <div class="ds-card-gradient">
            <div class="ds-card-title" style="margin-bottom:10px;">📊 최근 분석 요약</div>
            <div style="font-size:13px;color:#6B7894;line-height:1.7;">
                세션 ID
                <code style="background:#EEF4FF;padding:2px 6px;border-radius:4px;
                             font-size:12px;color:#4B7BFF;">#{session_id}</code>
                에 대한 분석 리포트가 있습니다.
            </div>
            <div style="margin-top:10px;font-size:12px;color:#A0AABB;">
                리포트 메뉴에서 확인하세요.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="ds-card-gradient">
            <div class="ds-card-title" style="margin-bottom:10px;">🔬 분석을 시작해보세요</div>
            <div style="font-size:13px;color:#6B7894;line-height:1.7;">
                얼굴 이미지를 업로드하면 AI가 7가지<br>
                피부 지표를 분석하고 맞춤 성분을 추천합니다.
            </div>
        </div>
        """, unsafe_allow_html=True)
