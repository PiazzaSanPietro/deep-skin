import base64
import os

import streamlit as st

from services import analysis_api, api_client
from components.common import show_error, handle_401
from components.layout import render_page_header
from components import upload_panel


# ── 진입점 ───────────────────────────────────────────────────────────────────

def show():
    # 상단 행: 제목 + 보안 pill
    col_hdr, col_pill = st.columns([4, 1])
    with col_hdr:
        render_page_header(
            "피부 분석 시작",
            "사진을 업로드하고 AI가 당신의 피부 상태를 정밀하게 분석해드려요.",
        )
    with col_pill:
        st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
        sec_src = _b64_src("analysis/security.png")
        sec_img = (
            f'<img src="{sec_src}" width="16" style="vertical-align:middle;margin-right:4px;">'
            if sec_src else "🛡️"
        )
        st.markdown(
            f'<div class="ds-security-pill">{sec_img} 보안 인증 완료</div>',
            unsafe_allow_html=True,
        )

    # 단계 표시
    _render_steps(active=1)

    # 업로드 패널 (탭 없이 1열 구조)
    image_data = upload_panel.render()

    # 가이드 카드
    st.markdown('<div style="margin-top:24px;"></div>', unsafe_allow_html=True)
    upload_panel.render_guide_cards()

    # 분석 버튼
    st.markdown('<hr style="border:none;border-top:1px solid #E4EAF5;margin:20px 0 16px;">', unsafe_allow_html=True)
    col_btn, _ = st.columns([2, 3])
    with col_btn:
        if st.button("✦  분석 시작", use_container_width=True):
            if not image_data:
                show_error("분석할 이미지를 먼저 업로드해주세요.")
            else:
                _run_analysis(image_data)

    st.markdown("""
    <div style="font-size:12px;color:#A0AABB;margin-top:8px;">
        ※ 분석 결과는 의료 진단을 대체하지 않으며, 참고용으로만 활용하세요.
    </div>
    """, unsafe_allow_html=True)


# ── 단계 표시 ─────────────────────────────────────────────────────────────────

def _render_steps(active: int):
    steps = [
        ("사진 업로드", 1, "analysis/step_1.png"),
        ("AI 분석",    2, "analysis/step_2.png"),
        ("리포트 확인", 3, "analysis/step_3.png"),
    ]
    parts = []
    for label, step, icon_rel in steps:
        if step < active:
            circle_cls = "ds-step-circle ds-step-circle-done"
            label_cls  = "ds-step-label-done"
            line_cls   = "ds-step-line ds-step-line-done"
        elif step == active:
            circle_cls = "ds-step-circle ds-step-circle-active"
            label_cls  = "ds-step-label-active"
            line_cls   = "ds-step-line"
        else:
            circle_cls = "ds-step-circle ds-step-circle-pending"
            label_cls  = "ds-step-label-pending"
            line_cls   = "ds-step-line"

        if step > 1:
            parts.append(f'<div class="{line_cls}"></div>')

        # 아이콘 이미지 사용 시도; 없으면 숫자
        icon_src = _b64_src(icon_rel)
        inner = (
            f'<img src="{icon_src}" width="20" height="20" style="object-fit:contain;">'
            if icon_src else str(step)
        )
        parts.append(f"""
        <div style="text-align:center;min-width:90px;">
            <div class="{circle_cls}" style="margin:0 auto 6px;">{inner}</div>
            <div class="{label_cls}">{label}</div>
        </div>
        """)

    st.markdown(
        '<div style="display:flex;align-items:center;margin-bottom:24px;max-width:420px;">'
        + "".join(parts)
        + "</div>",
        unsafe_allow_html=True,
    )


# ── 분석 실행 ─────────────────────────────────────────────────────────────────

def _run_analysis(image_data: dict):
    token = st.session_state.get("access_token")

    with st.spinner("분석 세션을 생성하는 중..."):
        session_result = analysis_api.create_session(token, "피부 분석")

    if api_client.is_error(session_result):
        if session_result.get("_status") == 401:
            handle_401()
            return
        show_error(api_client.get_error_message(session_result))
        return

    session_id = session_result.get("id")
    st.session_state["current_session_id"] = session_id

    with st.spinner("이미지를 업로드하고 AI가 분석 중입니다..."):
        upload_result = analysis_api.upload_image(
            token, session_id, image_data["bytes"], image_data["name"]
        )

    if api_client.is_error(upload_result):
        if upload_result.get("_status") == 401:
            handle_401()
            return
        show_error(api_client.get_error_message(upload_result))
        return

    st.session_state["current_page"] = "report"
    st.rerun()


def _b64_src(rel: str) -> str:
    path = os.path.join("assets", "icons", rel)
    try:
        with open(path, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    except Exception:
        return ""
