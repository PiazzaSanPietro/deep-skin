import base64
import os

import streamlit as st

from services import analysis_api, api_client
from components.common import show_error, handle_401, empty_state
from components.layout import render_page_header
from components import report_cards


# ── 진입점 ───────────────────────────────────────────────────────────────────

def show():
    render_page_header(
        "피부 분석 리포트",
        "AI 분석 기반 맞춤 피부 케어 리포트입니다.",
    )

    session_id = st.session_state.get("current_session_id")
    if not session_id:
        empty_state("분석 결과가 없습니다. 먼저 이미지를 업로드해주세요.")
        col_btn, _ = st.columns([1, 2])
        with col_btn:
            if st.button("분석 시작으로 이동", use_container_width=True):
                st.session_state["current_page"] = "analysis"
                st.rerun()
        return

    token = st.session_state.get("access_token")
    with st.spinner("리포트를 불러오는 중..."):
        report = analysis_api.get_report(token, session_id)

    if api_client.is_error(report):
        if report.get("_status") == 401:
            handle_401()
            return
        show_error(api_client.get_error_message(report))
        return

    _render_report(report)


# ── 리포트 렌더링 ─────────────────────────────────────────────────────────────

def _render_report(report: dict):
    status = report.get("status", "")

    if status == "pending":
        st.info("분석이 아직 시작되지 않았습니다.", icon="⏳")
        return

    if status == "processing":
        st.info("AI가 피부 상태를 분석 중입니다. 잠시 후 새로고침하세요.", icon="🔄")
        if st.button("새로고침"):
            st.rerun()
        return

    if status == "failed":
        show_error("분석에 실패했습니다. 이미지를 다시 업로드해주세요.")
        if st.button("다시 시작"):
            st.session_state["current_session_id"] = None
            st.session_state["current_page"] = "analysis"
            st.rerun()
        return

    # ── completed ────────────────────────────────────────
    overall      = report.get("overall_summary") or {}
    part_reports = report.get("part_reports") or []
    analyzed_at  = report.get("analyzed_at", "")[:16].replace("T", " ") if report.get("analyzed_at") else ""

    # 우측 상단 버튼 행
    col_title, col_btns = st.columns([3, 2])
    with col_btns:
        c1, c2 = st.columns(2)
        with c1:
            dl_icon = _b64_src("nav/download.png")
            dl_label = "⬇  다운로드" if not dl_icon else "⬇  다운로드"
            if st.button(dl_label, use_container_width=True):
                st.info("다운로드 기능은 준비 중입니다.", icon="ℹ️")
        with c2:
            if st.button("🔄  새 분석", use_container_width=True):
                st.session_state["current_session_id"] = None
                st.session_state["current_page"] = "analysis"
                st.rerun()

    # 전체 점수 + 요약 카드
    score = report_cards.compute_report_score(part_reports)
    report_cards.render_overall_summary(overall, score, analyzed_at)

    if not part_reports:
        st.info("부위별 분석 데이터가 없습니다.", icon="ℹ️")
        return

    # 부위별 카드 그리드
    st.markdown(
        '<div style="font-size:17px;font-weight:700;color:#0F2447;margin:8px 0 16px;">'
        '📍 부위별 분석 결과</div>',
        unsafe_allow_html=True,
    )

    n    = len(part_reports)
    cols = st.columns(min(n, 5), gap="medium")
    for i, part in enumerate(part_reports):
        with cols[i % min(n, 5)]:
            report_cards.render_part_card_header(part)

    # 상세 expander
    st.markdown(
        '<div style="margin-top:24px;font-size:15px;font-weight:600;color:#0F2447;margin-bottom:8px;">'
        '📋 부위별 상세 분석</div>',
        unsafe_allow_html=True,
    )
    for part in part_reports:
        report_cards.render_part_detail(part)

    # 통합 추천 4카드
    report_cards.render_recommendation_cards(part_reports)


def _b64_src(rel: str) -> str:
    path = os.path.join("assets", "icons", rel)
    try:
        with open(path, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    except Exception:
        return ""
