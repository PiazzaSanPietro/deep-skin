import base64
import os
import time

import streamlit as st

from services import analysis_api, api_client
from components.common import show_error, handle_401
from components import upload_panel
from styles.css_loader import load_css


_STATUS_MESSAGES = [
    "이미지를 확인하고 있어요.",
    "얼굴 영역을 감지하고 있어요.",
    "피부 상태를 분석하고 있어요.",
    "피부 고민 부위를 확인하고 있어요.",
    "맞춤 성분과 제품 타입을 추천하고 있어요.",
    "리포트를 생성하고 있어요.",
]


def show():
    _ensure_state()
    _inject_analysis_css()

    state = st.session_state.get("analysis_flow_state", "idle")

    with st.container(key="ds_analysis_page"):
        _render_header()

        if state == "analyzing":
            _hide_idle_analysis_ui()
            _render_steps("analyzing")
            _continue_analysis()
            return

        if state == "complete":
            _hide_idle_analysis_ui()
            _render_steps("complete")
            _render_complete()
            return

        if state == "error":
            _hide_idle_analysis_ui()
            _render_steps("error")
            _render_error()
            return

        _render_steps("idle")
        image_data = upload_panel.render()
        st.markdown('<div class="ds-analysis-guide-wrap"></div>', unsafe_allow_html=True)
        upload_panel.render_guide_cards()
        _render_start_button(image_data)


def _ensure_state():
    st.session_state.setdefault("analysis_flow_state", "idle")
    st.session_state.setdefault("analysis_image_data", None)
    st.session_state.setdefault("analysis_error_message", "")


def _hide_idle_analysis_ui():
    """Hide stale upload-screen DOM while Streamlit is rendering a state screen."""
    st.markdown(
        """
        <style>
        .st-key-ds_camera_card,
        .st-key-ds_upload_card,
        [data-testid="stHorizontalBlock"]:has(.st-key-ds_camera_card),
        [data-testid="stHorizontalBlock"]:has(.st-key-ds_upload_card),
        [data-testid="stHorizontalBlock"]:has(.ds-analysis-guide-card),
        [data-testid="stElementContainer"]:has(.ds-analysis-guide-wrap),
        [data-testid="stElementContainer"]:has(.ds-analysis-guide-card),
        [data-testid="stElementContainer"]:has(.ds-analysis-privacy),
        .ds-preview-frame,
        .ds-analysis-guide-wrap,
        .ds-analysis-guide-card,
        .st-key-ds_analysis_action,
        .ds-analysis-privacy {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            min-height: 0 !important;
            max-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
            pointer-events: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header():
    st.markdown(
        """
        <div class="ds-analysis-header">
            <div>
                <div class="ds-analysis-title">피부 분석 시작</div>
                <div class="ds-analysis-subtitle">
                    사진을 업로드하고 AI가 당신의 피부 상태를 정밀하게 분석해드려요.
                </div>
            </div>
            <div class="ds-security-pill">🛡 보안 인증 완료</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_steps(state: str):
    if state == "idle":
        statuses = ["active", "pending", "pending"]
        labels = ["사진 업로드", "AI 분석", "리포트 확인"]
    elif state == "analyzing":
        statuses = ["done", "active", "pending"]
        labels = ["사진 업로드", "AI 분석 중", "리포트 확인"]
    elif state == "complete":
        statuses = ["done", "done", "active"]
        labels = ["사진 업로드", "AI 분석 완료", "리포트 확인"]
    else:
        statuses = ["done", "active", "pending"]
        labels = ["사진 업로드", "AI 분석", "리포트 확인"]

    items = []
    for idx, (status, label) in enumerate(zip(statuses, labels), start=1):
        if idx > 1:
            line_cls = "ds-step-connector ds-step-connector-done" if statuses[idx - 2] == "done" else "ds-step-connector"
            items.append(f'<div class="{line_cls}"></div>')
        inner = "✓" if status == "done" else str(idx)
        items.append(
            f"""
            <div class="ds-step-item ds-step-{status}">
                <div class="ds-step-dot">{inner}</div>
                <div class="ds-step-text">{label}</div>
            </div>
            """
        )

    st.markdown('<div class="ds-analysis-steps">' + "".join(items) + "</div>", unsafe_allow_html=True)


def _render_start_button(image_data: dict | None):
    with st.container(key="ds_analysis_action"):
        if st.button("✦  분석 시작", key="analysis_start", width="stretch", disabled=False):
            if not image_data:
                show_error("분석할 이미지를 먼저 업로드해주세요.")
            else:
                st.session_state["analysis_image_data"] = image_data
                st.session_state["analysis_flow_state"] = "analyzing"
                st.session_state["analysis_error_message"] = ""
                st.rerun()
    st.markdown(
        """
        <div class="ds-analysis-privacy">
            🛡 업로드된 이미지는 분석 후 즉시 안전하게 삭제되며, 외부에 저장되지 않습니다.
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_analyzing():
    st.markdown(
        """
        <div class="ds-analysis-state-card">
            <div class="ds-state-badge">✨ AI 분석 중</div>
            <div class="ds-state-spinner"></div>
            <div class="ds-state-title">AI가 피부 상태를 분석하고 있어요</div>
            <div class="ds-state-desc">
                잠시만 기다려주세요. 업로드된 이미지를 바탕으로 피부 타입, 고민 부위,
                추천 성분을 분석 중입니다.
            </div>
            <div class="ds-state-subdesc">
                보통 10~30초 정도 소요될 수 있습니다. 분석이 완료되면 리포트 확인 버튼이 표시됩니다.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _continue_analysis():
    image_data = st.session_state.get("analysis_image_data")
    if not image_data:
        st.session_state["analysis_flow_state"] = "error"
        st.session_state["analysis_error_message"] = "분석할 이미지가 없습니다. 이미지를 다시 업로드해주세요."
        st.rerun()
        return

    progress = st.empty()
    for idx, msg in enumerate(_STATUS_MESSAGES):
        progress.markdown(_analysis_progress_markup(idx, msg), unsafe_allow_html=True)
        time.sleep(0.35)

    ok = _run_analysis(image_data)
    if ok:
        st.session_state["analysis_image_data"] = None
        st.session_state["analysis_flow_state"] = "complete"
    else:
        st.session_state["analysis_flow_state"] = "error"
    st.rerun()


def _analysis_progress_markup(active_idx: int, current_message: str) -> str:
    rows = []
    for idx, text in enumerate(_STATUS_MESSAGES):
        if idx < active_idx:
            cls = "done"
            mark = "✓"
        elif idx == active_idx:
            cls = "active"
            mark = "●"
        else:
            cls = "pending"
            mark = "○"
        rows.append(
            f'<div class="ds-ai-progress-row ds-ai-progress-{cls}">'
            f'<span class="ds-ai-progress-mark">{mark}</span>'
            f'<span>{text}</span>'
            f'</div>'
        )

    progress_rows = "".join(rows)
    return (
        '<div class="ds-analysis-state-card ds-ai-running-card">'
        '<div class="ds-state-badge ds-state-badge-running">✨ AI 분석 중</div>'
        '<div class="ds-ai-orb">'
        '<div class="ds-ai-orb-ring"></div>'
        '<div class="ds-ai-orb-core">✦</div>'
        '</div>'
        '<div class="ds-state-title">AI가 피부 상태를 분석하고 있어요</div>'
        '<div class="ds-state-desc">'
        '잠시만 기다려주세요.<br>'
        '업로드된 이미지를 바탕으로 피부 타입, 고민 부위, 추천 성분을 분석하고 있습니다.'
        '</div>'
        '<div class="ds-ai-current-box">'
        f'<div class="ds-progress-now">{current_message}</div>'
        f'<div class="ds-progress-list">{progress_rows}</div>'
        '</div>'
        '<div class="ds-state-subdesc">'
        '분석이 완료되면 리포트 확인 버튼이 표시됩니다.'
        '</div>'
        '</div>'
    )


def _render_complete():
    with st.container(key="ds_complete_card"):
        st.markdown(
            """
            <div class="ds-state-badge ds-state-badge-complete">✓ 분석 완료</div>
            <div class="ds-complete-orb">✓</div>
            <div class="ds-state-title">분석이 완료되었습니다</div>
            <div class="ds-state-desc">
                맞춤 피부 리포트가 준비되었어요.<br>
                아래 버튼을 눌러 분석 결과를 확인해주세요.
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("리포트 확인하기 →", key="go_report_after_analysis", width="stretch"):
            st.session_state["current_page"] = "report"
            st.session_state["analysis_flow_state"] = "idle"
            st.rerun()


def _render_error():
    msg = st.session_state.get("analysis_error_message") or "이미지를 다시 확인한 후 재시도해주세요."
    st.markdown(
        f"""
        <div class="ds-analysis-state-card ds-analysis-error-card">
            <div class="ds-state-badge ds-state-badge-error">분석 실패</div>
            <div class="ds-state-title">분석 중 문제가 발생했습니다</div>
            <div class="ds-state-desc">{msg}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns([1, 1], gap="medium")
    with c1:
        if st.button("다시 분석하기", key="retry_analysis", width="stretch"):
            st.session_state["analysis_flow_state"] = "analyzing"
            st.rerun()
    with c2:
        if st.button("이미지 다시 선택", key="back_to_upload", width="stretch"):
            st.session_state["analysis_flow_state"] = "idle"
            st.session_state["analysis_image_data"] = None
            st.rerun()


def _run_analysis(image_data: dict) -> bool:
    token = st.session_state.get("access_token")

    session_result = analysis_api.create_session(token, "피부 분석")
    if api_client.is_error(session_result):
        if session_result.get("_status") == 401:
            handle_401()
            return False
        st.session_state["analysis_error_message"] = api_client.get_error_message(session_result)
        return False

    session_id = session_result.get("id")
    st.session_state["current_session_id"] = session_id

    upload_result = analysis_api.upload_image(
        token, session_id, image_data["bytes"], image_data["name"]
    )
    if api_client.is_error(upload_result):
        if upload_result.get("_status") == 401:
            handle_401()
            return False
        st.session_state["analysis_error_message"] = api_client.get_error_message(upload_result)
        return False

    return True


def _b64_src(rel: str) -> str:
    path = os.path.join("assets", "icons", rel)
    try:
        with open(path, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    except Exception:
        return ""


def _inject_analysis_css():
    load_css("analysis.css")
