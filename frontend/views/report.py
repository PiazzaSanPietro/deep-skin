import base64
import html
import math
import os

import streamlit as st

from components import report_cards
from components.common import show_error, handle_401, empty_state
from services import analysis_api, api_client
from styles.css_loader import load_css
from styles.theme import MAIN_CONCERN_OPTIONS, SEVERITY_LABEL


_SEVERITY_ORDER = {"normal": 1, "mild": 2, "moderate": 3, "severe": 4}


def show():
    _inject_report_css()
    _prepare_report_page_state()
    st.markdown('<div id="ds-report-page-sentinel"></div>', unsafe_allow_html=True)
    _render_report_header()

    session_id = st.session_state.get("current_session_id")
    if not session_id:
        empty_state("분석 결과가 없습니다. 먼저 이미지를 업로드해주세요.")
        col_btn, _ = st.columns([1, 2])
        with col_btn:
            if st.button("분석 시작으로 이동", width="stretch"):
                st.session_state["current_page"] = "analysis"
                st.rerun()
        return

    token = st.session_state.get("access_token")
    loading_slot = st.empty()
    loading_slot.markdown(_report_loading_markup(), unsafe_allow_html=True)
    report = analysis_api.get_report(token, session_id)
    loading_slot.empty()

    if api_client.is_error(report):
        if report.get("_status") == 401:
            handle_401()
            return
        show_error(api_client.get_error_message(report))
        return

    _render_report(report)


def _prepare_report_page_state():
    """Keep the report page independent from the analysis completion screen."""
    if st.session_state.get("analysis_flow_state") == "complete":
        st.session_state["analysis_flow_state"] = "idle"
    st.session_state["analysis_image_data"] = None


def _render_report_header():
    col_title, col_actions = st.columns([1.8, 0.45], vertical_alignment="center")
    with col_title:
        st.markdown(
            """
            <div class="ds-report-page-title">피부 분석 리포트</div>
            <div class="ds-report-page-subtitle">
                AI가 분석한 당신의 피부 상태와 맞춤 솔루션을 확인하세요.
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_actions:
        if st.button("✦ 새 분석 시작", key="report_new_analysis", width="stretch"):
            st.session_state["current_session_id"] = None
            st.session_state["current_page"] = "analysis"
            st.rerun()


def _render_report(report: dict):
    status = report.get("status", "")

    if status == "pending":
        _render_status_card("분석이 아직 시작되지 않았습니다", "잠시 후 다시 확인해주세요.", "⏳")
        return

    if status == "processing":
        _render_status_card("AI가 피부 상태를 분석 중입니다", "잠시 후 새로고침해주세요.", "🔄")
        if st.button("새로고침", key="report_refresh_processing"):
            st.rerun()
        return

    if status == "failed":
        show_error("분석에 실패했습니다. 이미지를 다시 업로드해주세요.")
        if st.button("다시 시작", key="report_restart_failed"):
            st.session_state["current_session_id"] = None
            st.session_state["current_page"] = "analysis"
            st.rerun()
        return

    overall = report.get("overall_summary") or {}
    part_reports = report.get("part_reports") or []
    analyzed_at = _format_date(report.get("analyzed_at"))
    score = report_cards.compute_report_score(part_reports)

    _render_summary_card(overall, score, analyzed_at)

    if not part_reports:
        st.info("부위별 분석 데이터가 없습니다.", icon="ℹ️")
        return

    st.markdown('<div class="ds-report-section-title">부위별 분석 결과</div>', unsafe_allow_html=True)
    _render_part_grid(part_reports)
    _render_detail_expanders(part_reports)

    st.markdown('<div class="ds-report-section-title ds-report-section-spaced">맞춤 추천 결과</div>', unsafe_allow_html=True)
    _render_recommendation_grid(part_reports)

    st.markdown(
        """
        <div class="ds-report-footnote">
            ※ 본 분석 결과는 AI 기반 분석이며, 실제 피부 상태는 다를 수 있습니다. 전문가 상담을 권장합니다.
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_status_card(title: str, desc: str, icon: str):
    st.markdown(
        f"""
        <div class="ds-report-status-card">
            <div class="ds-report-status-icon">{html.escape(icon)}</div>
            <div class="ds-report-status-title">{html.escape(title)}</div>
            <div class="ds-report-status-desc">{html.escape(desc)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_summary_card(overall: dict, score: int, analyzed_at: str):
    status = overall.get("status") or _status_from_score(score)
    message = overall.get("main_message") or "피부 상태에 맞춘 집중 관리와 보습 루틴을 권장합니다."
    severity = _overall_severity(status)
    badge = _badge_html(status, severity)
    main_issues = overall.get("main_issues") or []
    issue_tags = "".join(
        _tag_html(_issue_label(issue), "concern")
        for issue in main_issues[:5]
        if _issue_label(issue)
    )

    st.markdown(
        f"""
        <div class="ds-report-summary-card">
            <div class="ds-report-summary-left">
                <div class="ds-report-card-kicker">전체 분석 결과</div>
                <div class="ds-report-meta">분석 일시 {html.escape(analyzed_at or "—")}</div>
                <div class="ds-report-summary-status">{badge}</div>
                <div class="ds-report-summary-title">{html.escape(message)}</div>
                <div class="ds-report-summary-desc">
                    피부 장벽과 보습 균형을 중심으로 관리하고, 고민 부위에 맞는 성분을 단계적으로 적용해보세요.
                </div>
                <div class="ds-report-tag-row">{issue_tags or _tag_html("맞춤 관리 필요", "concern")}</div>
            </div>
            <div class="ds-report-score-panel">
                {_gauge_html(score)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_part_grid(part_reports: list[dict]):
    parts = _sort_parts(part_reports)
    cols = st.columns(min(len(parts), 5), gap="medium")
    for col, part in zip(cols, parts):
        with col:
            st.markdown(_part_card_html(part), unsafe_allow_html=True)


def _render_detail_expanders(part_reports: list[dict]):
    st.markdown('<div class="ds-report-detail-title">상세 분석</div>', unsafe_allow_html=True)
    for part in _sort_parts(part_reports):
        part_name = part.get("display_part_name", "부위")
        summary = part.get("summary") or "요약 정보가 없습니다."
        issues = part.get("issues") or []
        with st.expander(f"{part_name} 상세 보기", expanded=False):
            st.markdown(f'<div class="ds-detail-summary">{html.escape(summary)}</div>', unsafe_allow_html=True)
            if issues:
                rows = "".join(_issue_row_html(issue) for issue in issues)
                st.markdown(f'<div class="ds-detail-issues">{rows}</div>', unsafe_allow_html=True)


def _render_recommendation_grid(part_reports: list[dict]):
    data = _collect_recommendations(part_reports)
    cards = [
        (
            "추천 카테고리",
            "이런 제품을 추천해요",
            data["categories"],
            "category",
            "🧴",
        ),
        (
            "추천 성분",
            "도움이 되는 성분이에요",
            data["ingredients"],
            "ingredient",
            "💧",
        ),
        (
            "제외 성분",
            "주의가 필요한 성분이에요",
            data["excluded"],
            "excluded",
            "⚠",
        ),
        (
            "관리 팁",
            "일상에서 실천해보세요",
            data["tips"],
            "tip",
            "✓",
        ),
    ]
    cols = st.columns(4, gap="medium")
    for col, (title, subtitle, items, kind, icon) in zip(cols, cards):
        with col:
            st.markdown(_recommendation_card_html(title, subtitle, items, kind, icon), unsafe_allow_html=True)


def _part_card_html(part: dict) -> str:
    name = part.get("display_part_name") or "부위"
    issues = part.get("issues") or []
    worst = _worst_severity(issues)
    concerns = [_issue_label(issue) for issue in issues if _issue_label(issue)]
    concern_text = ", ".join(concerns[:2]) if concerns else "특이 고민 없음"
    summary = part.get("summary") or _part_summary(worst)
    highlighted = " ds-part-card-focus" if worst in {"severe", "moderate"} else ""
    dots = _severity_dots(worst)

    return (
        f'<div class="ds-report-part-card{highlighted}">'
        f'<div class="ds-part-icon">{_part_icon(name)}</div>'
        f'<div class="ds-part-name">{html.escape(name)}</div>'
        f'<div class="ds-part-line"><span>주요 고민</span><strong>{html.escape(concern_text)}</strong></div>'
        f'<div class="ds-part-line"><span>심각도</span><div>{dots}</div></div>'
        f'<div class="ds-part-summary">{html.escape(summary)}</div>'
        f'</div>'
    )


def _recommendation_card_html(title: str, subtitle: str, items: list[str], kind: str, icon: str) -> str:
    if kind == "tip":
        body = "".join(f'<li>{html.escape(item)}</li>' for item in items[:5]) or "<li>꾸준한 보습과 자외선 차단을 유지하세요.</li>"
        body_html = f'<ul class="ds-tip-list">{body}</ul>'
    else:
        body_html = "".join(_tag_html(item, kind) for item in items[:8]) or _tag_html("추천 정보 없음", kind)

    return (
        f'<div class="ds-report-rec-card ds-rec-{kind}">'
        f'<div class="ds-rec-icon">{html.escape(icon)}</div>'
        f'<div class="ds-rec-title">{html.escape(title)}</div>'
        f'<div class="ds-rec-subtitle">{html.escape(subtitle)}</div>'
        f'<div class="ds-rec-body">{body_html}</div>'
        f'</div>'
    )


def _issue_row_html(issue: dict) -> str:
    label = issue.get("metric_display_name") or _issue_label(issue) or "분석 항목"
    severity = issue.get("severity", "normal")
    grade = issue.get("grade_value")
    grade_text = f"등급 {grade}" if grade is not None else SEVERITY_LABEL.get(severity, severity)
    return (
        '<div class="ds-detail-issue-row">'
        f'<div><strong>{html.escape(label)}</strong><span>{html.escape(grade_text)}</span></div>'
        f'{_badge_html(SEVERITY_LABEL.get(severity, severity), severity)}'
        '</div>'
    )


def _collect_recommendations(part_reports: list[dict]) -> dict[str, list[str]]:
    categories: list[str] = []
    ingredients: list[str] = []
    excluded: list[str] = []
    tips: list[str] = []

    for part in part_reports:
        rec = part.get("recommendation") or {}
        _extend_unique(categories, rec.get("categories") or [])
        _extend_unique(ingredients, [i.get("name", "") for i in rec.get("ingredients") or []])
        _extend_unique(excluded, [i.get("name", "") for i in rec.get("excluded_ingredients") or []])
        _extend_unique(tips, rec.get("care_tips") or [])

    return {
        "categories": categories,
        "ingredients": ingredients,
        "excluded": excluded or ["자극 성분", "과한 향료"],
        "tips": tips,
    }


def _extend_unique(target: list[str], items: list[str]):
    for item in items:
        if item and item not in target:
            target.append(item)


def _sort_parts(part_reports: list[dict]) -> list[dict]:
    order = ["볼", "눈가", "입술", "턱", "이마"]

    def key(part: dict):
        name = part.get("display_part_name", "")
        for idx, label in enumerate(order):
            if label in name:
                return idx
        return len(order)

    return sorted(part_reports, key=key)[:5]


def _worst_severity(issues: list[dict]) -> str:
    return max(
        (issue.get("severity", "normal") for issue in issues),
        key=lambda sev: _SEVERITY_ORDER.get(sev, 0),
        default="normal",
    )


def _overall_severity(status: str) -> str:
    if "집중" in status or "심각" in status:
        return "severe"
    if "관리 필요" in status and "약한" not in status:
        return "moderate"
    if "약한" in status:
        return "mild"
    return "normal"


def _status_from_score(score: int) -> str:
    if score >= 75:
        return "양호"
    if score >= 50:
        return "관리 필요"
    return "집중 관리 필요"


def _issue_label(issue: dict) -> str:
    issue_type = issue.get("issue_type", "")
    return (
        issue.get("metric_display_name")
        or MAIN_CONCERN_OPTIONS.get(issue_type, issue_type)
        or ""
    )


def _part_summary(severity: str) -> str:
    if severity in {"severe", "moderate"}:
        return "집중적인 진정 및 장벽 관리가 필요해요."
    if severity == "mild":
        return "꾸준한 보습과 예방 관리가 도움이 돼요."
    return "현재 상태를 유지하는 기본 관리가 좋아요."


def _part_icon(name: str) -> str:
    icon_map = {
        "볼": "cheek.png",
        "눈": "eye_rim.png",
        "입": "lips.png",
        "턱": "chin.png",
        "이마": "forehead.png",
    }
    for keyword, filename in icon_map.items():
        if keyword in name:
            src = _icon_src(filename)
            if src:
                return f'<img src="{src}" alt="{html.escape(name)}" class="ds-part-icon-img">'
    return "◌"


def _icon_src(filename: str) -> str:
    path = os.path.join("assets", "icons", filename)
    try:
        with open(path, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    except Exception:
        return ""


def _badge_html(label: str, severity: str) -> str:
    return f'<span class="ds-report-badge ds-report-badge-{html.escape(severity)}">{html.escape(label)}</span>'


def _tag_html(label: str, kind: str) -> str:
    return f'<span class="ds-report-tag ds-report-tag-{html.escape(kind)}">{html.escape(label)}</span>'


def _severity_dots(severity: str) -> str:
    active = {"normal": 1, "mild": 2, "moderate": 3, "severe": 4}.get(severity, 1)
    return "".join(
        f'<span class="ds-severity-dot {"is-active" if idx < active else ""}"></span>'
        for idx in range(5)
    )


def _gauge_html(score: int) -> str:
    score = max(0, min(100, int(score)))
    deg = score * 3.6
    return (
        f'<div class="ds-score-gauge" style="--score-deg:{deg:.1f}deg;">'
        '<div class="ds-score-gauge-inner">'
        f'<div class="ds-score-number">{score}<span>/100</span></div>'
        '<div class="ds-score-label">피부 점수</div>'
        '</div>'
        '</div>'
    )


def _format_date(value: str | None) -> str:
    if not value:
        return ""
    return value[:16].replace("T", " ")


def _report_loading_markup() -> str:
    return """
        <div class="ds-report-loading-card">
            <div class="ds-report-loading-badge">리포트 확인 준비 중</div>
            <div class="ds-report-loading-orb">
                <div class="ds-report-loading-ring"></div>
                <div class="ds-report-loading-core">↗</div>
            </div>
            <div class="ds-report-loading-title">리포트를 불러오고 있어요</div>
            <div class="ds-report-loading-desc">
                분석 결과를 정리하고 화면에 표시할 준비를 하고 있습니다.<br>
                잠시만 기다려주세요.
            </div>
        </div>
        """


def _inject_report_css():
    load_css("report.css")
