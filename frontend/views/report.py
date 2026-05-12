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

# ── 표시명 매핑 ──────────────────────────────────────────────────────────────

_PART_DISPLAY: dict[str, str] = {
    "forehead": "이마",
    "left_cheek": "왼쪽 볼",
    "right_cheek": "오른쪽 볼",
    "left_eye": "왼쪽 눈가",
    "right_eye": "오른쪽 눈가",
    "chin": "턱",
    "glabella": "미간",
    "nose": "코",
    "lips": "입술",
}

_GROUP_DISPLAY: dict[str, str] = {
    "moisture": "수분",
    "elasticity": "탄력",
    "wrinkle": "주름",
    "pore": "모공",
    "pigmentation": "색소침착",
    "acne": "여드름",
}

# 전문가 모드 추이 선택 가능 지표 구성: raw_part_name → metric_group → metric_name 리스트
_TREND_METRIC_OPTIONS: dict[str, dict[str, list[str]]] = {
    "forehead": {
        "moisture": ["moisture"],
        "elasticity": [
            "R2", "R7", "R0", "R1", "R3", "R4", "R5", "R6", "R8", "R9",
            "Ra", "Rmax", "Rt", "Rz", "Rp", "Rv", "Rq", "R3z",
            "Q0", "Q1", "Q2", "Q3",
        ],
        "wrinkle": ["Ra", "Rmax", "Rt", "Rz", "Rp", "Rv", "Rq", "R3z"],
    },
    "left_cheek": {
        "moisture": ["moisture"],
        "pore": ["pore_count"],
        "pigmentation": ["pigmentation_count"],
        "acne": ["acne_count"],
        "elasticity": ["R2", "R7", "Ra", "Rmax"],
    },
    "right_cheek": {
        "moisture": ["moisture"],
        "pore": ["pore_count"],
        "pigmentation": ["pigmentation_count"],
        "acne": ["acne_count"],
        "elasticity": ["R2", "R7", "Ra", "Rmax"],
    },
    "left_eye": {
        "wrinkle": ["Ra", "Rmax", "Rt", "Rz", "Rp", "Rv", "Rq", "R3z"],
        "elasticity": ["R2", "R7"],
    },
    "right_eye": {
        "wrinkle": ["Ra", "Rmax", "Rt", "Rz", "Rp", "Rv", "Rq", "R3z"],
        "elasticity": ["R2", "R7"],
    },
    "chin": {
        "moisture": ["moisture"],
        "wrinkle": ["Ra", "Rmax"],
        "elasticity": ["R2", "R7"],
    },
    "glabella": {
        "moisture": ["moisture"],
        "elasticity": ["R2", "R7"],
        "wrinkle": ["Ra", "Rmax"],
    },
}

# 기본 모드에서 추이 그래프를 표시할 지표 목록
# (raw_part_name, metric_group, metric_name, 한국어 레이블)
_TREND_METRICS: list[tuple[str, str, str, str]] = [
    ("forehead", "moisture", "moisture", "이마 수분"),
    ("left_cheek", "pore", "pore_count", "왼쪽 볼 모공 개수"),
    ("right_cheek", "pore", "pore_count", "오른쪽 볼 모공 개수"),
    ("left_eye", "wrinkle", "Ra", "왼쪽 눈가 주름 Ra"),
    ("right_eye", "wrinkle", "Ra", "오른쪽 눈가 주름 Ra"),
    ("forehead", "elasticity", "R2", "이마 탄력 R2"),
    ("left_cheek", "elasticity", "R2", "왼쪽 볼 탄력 R2"),
    ("right_cheek", "elasticity", "R2", "오른쪽 볼 탄력 R2"),
]

# 기본 모드에서 표시할 (metric_group, metric_name) 집합
_BASIC_METRICS: set[tuple[str, str]] = {
    ("moisture", "moisture"),
    ("pore", "pore_count"),
    ("pigmentation", "pigmentation_count"),
    ("acne", "acne_count"),
    ("wrinkle", "Ra"),
    ("wrinkle", "Rmax"),
    ("elasticity", "R2"),
    ("elasticity", "R7"),
}

# (metric_group_metric_name) → 한국어 표시명
_METRIC_DISPLAY: dict[str, str] = {
    "moisture_moisture": "수분",
    "pore_pore_count": "모공 개수",
    "pigmentation_pigmentation_count": "색소침착 개수",
    "acne_acne_count": "여드름 개수",
    "elasticity_R0": "탄력 R0",  "elasticity_R1": "탄력 R1",
    "elasticity_R2": "탄력 R2",  "elasticity_R3": "탄력 R3",
    "elasticity_R4": "탄력 R4",  "elasticity_R5": "탄력 R5",
    "elasticity_R6": "탄력 R6",  "elasticity_R7": "탄력 R7",
    "elasticity_R8": "탄력 R8",  "elasticity_R9": "탄력 R9",
    "elasticity_Q0": "탄력 Q0",  "elasticity_Q1": "탄력 Q1",
    "elasticity_Q2": "탄력 Q2",  "elasticity_Q3": "탄력 Q3",
    "elasticity_Ra": "탄력 Ra",  "elasticity_Rmax": "탄력 Rmax",
    "elasticity_Rt": "탄력 Rt",  "elasticity_Rz": "탄력 Rz",
    "elasticity_Rp": "탄력 Rp",  "elasticity_Rv": "탄력 Rv",
    "elasticity_Rq": "탄력 Rq",  "elasticity_R3z": "탄력 R3z",
    "wrinkle_Ra": "주름 Ra",     "wrinkle_Rmax": "주름 Rmax",
    "wrinkle_Rt": "주름 Rt",     "wrinkle_Rz": "주름 Rz",
    "wrinkle_Rp": "주름 Rp",     "wrinkle_Rv": "주름 Rv",
    "wrinkle_Rq": "주름 Rq",     "wrinkle_R3z": "주름 R3z",
}


def _metric_name_display(group: str, name: str) -> str:
    return _METRIC_DISPLAY.get(f"{group}_{name}") or name


def show():
    _inject_report_css()
    _prepare_report_page_state()
    st.markdown('<div id="ds-report-page-sentinel"></div>', unsafe_allow_html=True)
    _render_report_header()

    token = st.session_state.get("access_token")
    session_id = st.session_state.get("current_session_id")
    if not session_id:
        report = _load_latest_report(token)
        if report is not None:
            _render_report(report)
            return

        empty_state("분석 결과가 없습니다. 먼저 이미지를 업로드해주세요.")
        col_btn, _ = st.columns([1, 2])
        with col_btn:
            if st.button("분석 시작으로 이동", width="stretch"):
                st.session_state["current_page"] = "analysis"
                st.rerun()
        return

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

    st.session_state["last_report"] = report
    _render_report(report)


def _load_latest_report(token: str | None) -> dict | None:
    loading_slot = st.empty()
    loading_slot.markdown(_report_loading_markup(), unsafe_allow_html=True)
    report = analysis_api.get_latest_report(token)
    loading_slot.empty()

    if api_client.is_error(report):
        if report.get("_status") == 401:
            handle_401()
            return None
        if report.get("_status") == 404:
            return None
        show_error(api_client.get_error_message(report))
        st.stop()

    session_id = report.get("session_id")
    if session_id:
        st.session_state["current_session_id"] = session_id
    st.session_state["last_report"] = report
    return report


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
    _render_part_grid_with_selection(part_reports)

    metrics_parts = _load_metrics(
        st.session_state.get("access_token"),
        report.get("session_id"),
    )
    metrics_by_part = _build_metrics_map(metrics_parts)

    _render_selected_part_detail(part_reports, metrics_by_part)

    tab1, tab2, tab3 = st.tabs(["📊 지표 요약", "🔬 전문가 분석", "📈 측정 추이"])
    with tab1:
        _render_radar_section(part_reports, metrics_by_part)
    with tab2:
        _render_expert_panel(part_reports, metrics_by_part)
    with tab3:
        _tok = st.session_state.get("access_token")
        _sid = report.get("session_id")
        if _tok and _sid:
            _render_expert_trend_selector(_tok, _sid)
            st.markdown('<div class="ds-exp-trend-divider"></div>', unsafe_allow_html=True)
        _render_trends_content(_tok, _sid)

    st.markdown(
        '<div class="ds-report-section-title ds-report-section-spaced">맞춤 추천 결과</div>'
        '<div class="ds-report-section-sub">피부 분석 결과와 등록된 추천 기준을 바탕으로 제안된 결과입니다.</div>',
        unsafe_allow_html=True,
    )
    _render_recommendation_grid(part_reports, metrics_by_part)

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
    max_cols = 6
    for start in range(0, len(parts), max_cols):
        row = parts[start:start + max_cols]
        cols = st.columns(len(row), gap="medium")
        for col, part in zip(cols, row):
            with col:
                st.markdown(_part_card_html(part), unsafe_allow_html=True)


def _render_part_grid_with_selection(part_reports: list[dict]):
    parts = _sort_parts(part_reports)
    selected = st.session_state.get("selected_part_name")
    max_cols = 6
    for start in range(0, len(parts), max_cols):
        row = parts[start:start + max_cols]
        cols = st.columns(len(row), gap="medium")
        for idx, (col, part) in enumerate(zip(cols, row)):
            name = part.get("display_part_name", "부위")
            is_selected = name == selected
            issues = part.get("issues") or []
            worst = _worst_severity(issues)
            concerns = [_issue_label(issue) for issue in issues if _issue_label(issue)]
            concern_text = ", ".join(concerns[:2]) if concerns else "특이 고민 없음"
            cls = "ds-report-part-card"
            if worst in {"severe", "moderate"}:
                cls += " ds-part-card-focus"
            if is_selected:
                cls += " ds-part-card-selected"
            dots = _severity_dots(worst)
            with col:
                with st.container(key=f"ds_pcard_{start + idx}"):
                    st.markdown(
                        f'<div class="{cls}">'
                        f'<div class="ds-part-icon">{_part_icon(name)}</div>'
                        f'<div class="ds-part-name">{html.escape(name)}</div>'
                        f'<div class="ds-part-line"><span>주요 고민</span><strong>{html.escape(concern_text)}</strong></div>'
                        f'<div class="ds-part-line"><span>심각도</span><div>{dots}</div></div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    btn_label = "✓ 선택됨" if is_selected else "상세 보기"
                    if st.button(btn_label, key=f"sel_part_{name}", use_container_width=True):
                        if is_selected:
                            st.session_state.pop("selected_part_name", None)
                        else:
                            st.session_state["selected_part_name"] = name
                        st.rerun()


def _render_selected_part_detail(
    part_reports: list[dict],
    metrics_by_part: dict | None = None,
):
    selected = st.session_state.get("selected_part_name")
    if not selected:
        return
    part = next((p for p in part_reports if p.get("display_part_name") == selected), None)
    if not part:
        return

    issues = part.get("issues") or []
    worst = _worst_severity(issues)
    summary = part.get("summary") or _part_summary(worst)
    metrics_map = metrics_by_part or {}
    part_metrics = metrics_map.get(selected, [])
    color, sev_label = _SEV_COLOR.get(worst, ("#10B981", "양호"))
    icon_html = _part_icon(selected)

    issues_html = ""
    if issues:
        cards = "".join(_detail_issue_card_html(iss) for iss in issues)
        issues_html = (
            f'<div class="ds-dpanel-sec-label">피부 고민</div>'
            f'<div class="ds-dpanel-issue-grid">{cards}</div>'
        )

    metrics_html = ""
    if part_metrics:
        visible = [m for m in part_metrics if _is_basic_metric(m) and not m.get("is_dummy")]
        if visible:
            raw_names = {m.get("_raw_part_name", "") for m in visible}
            bilateral = any("left" in r for r in raw_names) and any("right" in r for r in raw_names)
            body = _detail_bilateral_metrics_html(visible) if bilateral else _detail_single_metrics_html(visible)
            metrics_html = (
                f'<div class="ds-dpanel-sec-label">주요 측정 지표</div>'
                f'{body}'
            )

    st.markdown(
        f'<div class="ds-dpanel">'
        f'<div class="ds-dpanel-head">'
        f'<div class="ds-dpanel-icon">{icon_html}</div>'
        f'<div class="ds-dpanel-head-text">'
        f'<div class="ds-dpanel-name-row">'
        f'<span class="ds-dpanel-name">{html.escape(selected)}</span>'
        f'<span class="ds-dpanel-sev" style="color:{color};background:{color}1A;">{sev_label}</span>'
        f'</div>'
        f'<div class="ds-dpanel-summary">{html.escape(summary)}</div>'
        f'</div>'
        f'</div>'
        f'{issues_html}'
        f'{metrics_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _detail_issue_card_html(issue: dict) -> str:
    label = issue.get("metric_display_name") or _issue_label(issue) or "분석 항목"
    severity = issue.get("severity", "normal")
    grade = issue.get("grade_value")
    grade_text = f"등급 {grade}" if grade is not None else ""
    color, sev_label = _SEV_COLOR.get(severity, ("#10B981", "양호"))
    return (
        f'<div class="ds-dpanel-ic" style="border-left:3px solid {color};">'
        f'<div class="ds-dpanel-ic-name">{html.escape(label)}</div>'
        f'<div class="ds-dpanel-ic-row">'
        f'<span class="ds-dpanel-ic-grade">{html.escape(grade_text)}</span>'
        f'<span class="ds-dpanel-ic-badge" style="color:{color};background:{color}1A;">{sev_label}</span>'
        f'</div>'
        f'</div>'
    )


def _detail_bilateral_metrics_html(metrics: list[dict]) -> str:
    from collections import OrderedDict
    groups: dict[str, dict] = OrderedDict()
    for m in metrics:
        raw = m.get("_raw_part_name", "")
        key = f"{m.get('metric_group', '')}_{m.get('metric_name', '')}"
        base = _METRIC_DISPLAY.get(key) or key.replace("_", " ").strip()
        if base not in groups:
            groups[base] = {"left": None, "right": None, "vtype": m.get("value_type", "reg")}
        if "left" in raw:
            groups[base]["left"] = m.get("value", 0.0)
        elif "right" in raw:
            groups[base]["right"] = m.get("value", 0.0)

    rows = []
    for base, sides in groups.items():
        lv = sides["left"] or 0.0
        rv = sides["right"] or 0.0
        max_v = max(lv, rv, 0.001)
        lp = min(lv / max_v * 100, 100)
        rp = min(rv / max_v * 100, 100)
        fmt = (lambda v: str(int(round(v)))) if sides["vtype"] == "count" else (lambda v: f"{v:.3f}")
        rows.append(
            f'<div class="ds-dpanel-mrow">'
            f'<span class="ds-dpanel-mrow-label">{html.escape(base)}</span>'
            f'<div class="ds-dpanel-mrow-bi">'
            f'<div class="ds-dpanel-mrow-side">'
            f'<span class="ds-dpanel-mrow-tag">좌</span>'
            f'<div class="ds-dpanel-mrow-track"><div class="ds-dpanel-mrow-fill" style="width:{lp:.0f}%"></div></div>'
            f'<span class="ds-dpanel-mrow-val">{html.escape(fmt(lv))}</span>'
            f'</div>'
            f'<div class="ds-dpanel-mrow-side">'
            f'<span class="ds-dpanel-mrow-tag">우</span>'
            f'<div class="ds-dpanel-mrow-track"><div class="ds-dpanel-mrow-fill" style="width:{rp:.0f}%"></div></div>'
            f'<span class="ds-dpanel-mrow-val">{html.escape(fmt(rv))}</span>'
            f'</div>'
            f'</div>'
            f'</div>'
        )
    return f'<div class="ds-dpanel-metrics">' + "".join(rows) + '</div>'


def _detail_single_metrics_html(metrics: list[dict]) -> str:
    max_v = max((m.get("value", 0.0) for m in metrics), default=0.001) or 0.001
    rows = []
    for m in metrics:
        val = m.get("value", 0.0)
        pct = min(val / max_v * 100, 100)
        value_type = m.get("value_type", "reg")
        formatted = str(int(round(val))) if value_type == "count" else f"{val:.3f}"
        label = html.escape(_metric_label(m, bilateral=False))
        rows.append(
            f'<div class="ds-dpanel-mrow">'
            f'<span class="ds-dpanel-mrow-label">{label}</span>'
            f'<div class="ds-dpanel-mrow-track"><div class="ds-dpanel-mrow-fill" style="width:{pct:.0f}%"></div></div>'
            f'<span class="ds-dpanel-mrow-val">{html.escape(formatted)}</span>'
            f'</div>'
        )
    return f'<div class="ds-dpanel-metrics">' + "".join(rows) + '</div>'


def _compute_radar_scores(part_reports: list[dict]) -> dict[str, float]:
    groups = ["moisture", "elasticity", "wrinkle", "pore", "pigmentation", "acne"]
    sev_score = {"normal": 88.0, "mild": 66.0, "moderate": 40.0, "severe": 18.0}
    group_vals: dict[str, list[float]] = {g: [] for g in groups}
    for part in part_reports:
        for issue in (part.get("issues") or []):
            issue_type = issue.get("issue_type", "")
            if issue_type in group_vals:
                sev = issue.get("severity", "normal")
                group_vals[issue_type].append(sev_score.get(sev, 70.0))
    return {
        g: (sum(vals) / len(vals) if vals else 80.0)
        for g, vals in group_vals.items()
    }


def _radar_chart_svg(scores: dict[str, float]) -> str:
    keys = ["moisture", "elasticity", "wrinkle", "pore", "pigmentation", "acne"]
    labels = ["수분", "탄력", "주름", "모공", "색소침착", "여드름"]
    n = len(keys)
    cx, cy, r = 160, 155, 100
    w, h = 320, 310

    def pt(angle_deg: float, radius: float) -> tuple[float, float]:
        rad = math.radians(angle_deg - 90)
        return cx + radius * math.cos(rad), cy + radius * math.sin(rad)

    angles = [i * 360 / n for i in range(n)]
    parts: list[str] = []

    for pct in (0.2, 0.4, 0.6, 0.8, 1.0):
        ring = [pt(a, r * pct) for a in angles]
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in ring)
        opacity = "0.5" if pct < 1.0 else "0.9"
        parts.append(f'<polygon points="{pts}" fill="none" stroke="#CBD5E1" stroke-width="1" opacity="{opacity}"/>')

    for a in angles:
        x2, y2 = pt(a, r)
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#CBD5E1" stroke-width="1"/>')

    data_pts_list: list[tuple[float, float]] = []
    for i, key in enumerate(keys):
        v = max(0.0, min(100.0, scores.get(key, 80.0))) / 100
        data_pts_list.append(pt(angles[i], r * v))
    data_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in data_pts_list)
    parts.append(f'<polygon points="{data_pts}" fill="rgba(94,123,211,0.22)" stroke="#5E7BD3" stroke-width="2"/>')

    for px, py in data_pts_list:
        parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="#5E7BD3" stroke="white" stroke-width="1.5"/>')

    for i, (label, a) in enumerate(zip(labels, angles)):
        lx, ly = pt(a, r + 26)
        parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" dominant-baseline="middle" '
            f'font-size="11" fill="#334155" font-weight="600">{label}</text>'
        )

    return (
        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">'
        + "".join(parts)
        + "</svg>"
    )


def _render_radar_section(
    part_reports: list[dict],
    metrics_by_part: dict | None = None,
) -> None:
    scores = _compute_radar_scores(part_reports)
    keys = ["moisture", "elasticity", "wrinkle", "pore", "pigmentation", "acne"]
    labels = ["수분", "탄력", "주름", "모공", "색소침착", "여드름"]

    col_chart, col_bars = st.columns([1, 1], gap="large")
    with col_chart:
        st.markdown(
            f'<div class="ds-radar-wrap">{_radar_chart_svg(scores)}</div>',
            unsafe_allow_html=True,
        )
    with col_bars:
        bar_rows = []
        for key, label in zip(keys, labels):
            score = int(round(scores.get(key, 80.0)))
            color_cls = "good" if score >= 70 else ("moderate" if score >= 45 else "poor")
            bar_rows.append(
                f'<div class="ds-radar-bar-row">'
                f'<div class="ds-radar-bar-label">{label}</div>'
                f'<div class="ds-radar-bar-track">'
                f'<div class="ds-radar-bar-fill ds-radar-bar-{color_cls}" style="width:{score}%"></div>'
                f'</div>'
                f'<div class="ds-radar-bar-score">{score}</div>'
                f'</div>'
            )
        st.markdown(
            f'<div class="ds-radar-bars">{"".join(bar_rows)}</div>',
            unsafe_allow_html=True,
        )


def _sparkline_svg(values: list[float], w: int = 280, h: int = 60) -> str:
    """SVG area sparkline — smooth bezier curves, fixed padding, consistent scale."""
    if len(values) < 2:
        return ""
    min_v = min(values)
    max_v = max(values)
    rng = max_v - min_v if max_v != min_v else 1.0
    # add 15% vertical padding so a flat line sits in the middle
    pad_y, pad_x = 10, 4

    def xy(i: int, v: float) -> tuple[float, float]:
        x = pad_x + i * (w - 2 * pad_x) / (len(values) - 1)
        norm = (v - min_v) / rng
        # invert + add 15% breathing room top & bottom
        y = h - pad_y - norm * (h - 2 * pad_y)
        return x, y

    pts = [xy(i, v) for i, v in enumerate(values)]

    # catmull-rom → cubic bezier tangent approximation
    def bezier_d(points: list[tuple[float, float]]) -> str:
        d = f"M {points[0][0]:.1f},{points[0][1]:.1f}"
        for k in range(1, len(points)):
            x0, y0 = points[k - 1]
            x1, y1 = points[k]
            cp = (x0 + x1) / 2
            d += f" C {cp:.1f},{y0:.1f} {cp:.1f},{y1:.1f} {x1:.1f},{y1:.1f}"
        return d

    line_d = bezier_d(pts)
    area_d = f"{line_d} L {pts[-1][0]:.1f},{h} L {pts[0][0]:.1f},{h} Z"

    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" fill="#4B7BFF" opacity="0.35"/>'
        for x, y in pts[:-1]
    )
    lx, ly = pts[-1]
    return (
        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">'
        f'<path d="{area_d}" fill="rgba(75,123,255,0.07)"/>'
        f'<path d="{line_d}" fill="none" stroke="#4B7BFF" stroke-width="2" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
        f'{dots}'
        f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="3.5" fill="#4B7BFF" stroke="white" stroke-width="2"/>'
        f'</svg>'
    )


def _trend_card_html(label: str, trend: list[dict] | None) -> str:
    """Full HTML for one trend metric card."""
    is_count = "개수" in label

    if not trend:
        return (
            f'<div class="ds-tcard ds-tcard-empty">'
            f'<div class="ds-tcard-label">{html.escape(label)}</div>'
            f'<div class="ds-tcard-nodata">데이터 없음</div>'
            f'</div>'
        )

    sorted_pts = sorted(trend, key=lambda p: p.get("analyzed_at", ""))
    values = [p["value"] for p in sorted_pts]
    latest = values[-1]
    latest_date = sorted_pts[-1]["analyzed_at"][:10]
    formatted = str(int(round(latest))) if is_count else f"{latest:.3f}"

    delta_html = ""
    if len(values) >= 2:
        delta = latest - values[-2]
        if is_count:
            ds = f"+{int(round(delta))}" if delta > 0 else str(int(round(delta)))
        else:
            ds = f"+{delta:.3f}" if delta > 0 else f"{delta:.3f}"
        if delta > 0.0001:
            delta_html = f'<span class="ds-tcard-delta ds-tcard-up">▲ {html.escape(ds)}</span>'
        elif delta < -0.0001:
            delta_html = f'<span class="ds-tcard-delta ds-tcard-dn">▼ {html.escape(ds)}</span>'
        else:
            delta_html = '<span class="ds-tcard-delta ds-tcard-flat">─</span>'

    if len(values) >= 2:
        chart_html = f'<div class="ds-tcard-spark">{_sparkline_svg(values)}</div>'
    else:
        chart_html = (
            f'<div class="ds-tcard-single-date">{html.escape(latest_date)}</div>'
            f'<div class="ds-tcard-hint">2회 이상 분석 시 추이 그래프를 표시합니다.</div>'
        )

    return (
        f'<div class="ds-tcard">'
        f'<div class="ds-tcard-label">{html.escape(label)}</div>'
        f'<div class="ds-tcard-val-row">'
        f'<span class="ds-tcard-val">{html.escape(formatted)}</span>'
        f'{delta_html}'
        f'</div>'
        f'{chart_html}'
        f'</div>'
    )


def _render_trends_grid(trends_data: list[tuple[str, list[dict] | None]]) -> None:
    if not any(t for _, t in trends_data):
        st.markdown(
            '<div class="ds-trend-empty-state">'
            '<div class="ds-trend-empty-icon">📊</div>'
            '<div class="ds-trend-empty-text">추이 데이터를 불러올 수 없습니다.<br>잠시 후 다시 시도해주세요.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return
    for i in range(0, len(trends_data), 3):
        row = trends_data[i:i + 3]
        cols = st.columns(len(row), gap="medium")
        for col, (label, trend) in zip(cols, row):
            with col:
                st.markdown(_trend_card_html(label, trend), unsafe_allow_html=True)


def _render_trends_content(token: str | None, session_id: int | None) -> None:
    if not token or not session_id:
        st.markdown(
            '<div class="ds-trend-empty-state">'
            '<div class="ds-trend-empty-icon">📊</div>'
            '<div class="ds-trend-empty-text">로그인 후 추이 데이터를 확인할 수 있습니다.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    cache_key = f"trends_{session_id}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = _fetch_all_trends(token)

    st.markdown('<div class="ds-trend-section-title">기본 추이 지표</div>', unsafe_allow_html=True)
    _render_trends_grid(st.session_state[cache_key])


_SEV_COLOR: dict[str, tuple[str, str]] = {
    "normal":   ("#10B981", "양호"),
    "mild":     ("#F59E0B", "경미"),
    "moderate": ("#F97316", "관리 필요"),
    "severe":   ("#EF4444", "집중 관리"),
}
_GROUP_ORDER_EXP = ["moisture", "pore", "pigmentation", "acne", "elasticity", "wrinkle"]


def _metric_bar_row(m: dict) -> str:
    """Single metric bar row HTML."""
    lbl = html.escape(_metric_label(m))
    value = m.get("value", 0.0)
    vtype = m.get("value_type", "reg")
    is_dummy = m.get("is_dummy", False)
    formatted = str(int(round(value))) if vtype == "count" else f"{value:.3f}"
    bar_pct = (
        min(100.0, max(0.0, float(value) * 100))
        if vtype == "reg"
        else min(100.0, max(0.0, float(value) / 5.0))
    )
    bar_cls = "ds-exp-bar-dim" if is_dummy else "ds-exp-bar-fill"
    dummy_badge = '<span class="ds-metric-dummy-badge">미학습</span>' if is_dummy else ""
    return (
        f'<div class="ds-exp-metric-row">'
        f'<div class="ds-exp-metric-top">'
        f'<span class="ds-exp-metric-label">{lbl}{dummy_badge}</span>'
        f'<span class="ds-exp-metric-val">{html.escape(formatted)}</span>'
        f'</div>'
        f'<div class="ds-exp-bar-track">'
        f'<div class="ds-exp-bar {bar_cls}" style="width:{bar_pct:.1f}%"></div>'
        f'</div>'
        f'</div>'
    )


def _metric_groups_html(metrics: list[dict]) -> str:
    """Grouped metric bar rows HTML for one side (no bilateral awareness)."""
    groups: dict[str, list[dict]] = {}
    for m in metrics:
        groups.setdefault(m.get("metric_group", "기타"), []).append(m)
    sorted_keys = sorted(
        groups,
        key=lambda g: _GROUP_ORDER_EXP.index(g) if g in _GROUP_ORDER_EXP else 99,
    )
    out = ""
    for group_key in sorted_keys:
        group_label = _GROUP_DISPLAY.get(group_key, group_key)
        rows = "".join(_metric_bar_row(m) for m in groups[group_key])
        out += (
            f'<div class="ds-exp-group">'
            f'<div class="ds-exp-group-label">{html.escape(group_label)}</div>'
            f'{rows}'
            f'</div>'
        )
    return out or '<div class="ds-exp-no-data">측정 데이터가 없습니다.</div>'


def _expert_metrics_html(part_metrics: list[dict]) -> str:
    """Metric bars HTML — auto-splits into 왼쪽/오른쪽 columns when raw_part_name has both sides."""
    if not part_metrics:
        return '<div class="ds-exp-no-data">측정 데이터가 없습니다.</div>'

    raw_names = {m.get("_raw_part_name", "") for m in part_metrics}
    has_left = any("left" in r for r in raw_names)
    has_right = any("right" in r for r in raw_names)

    if has_left and has_right:
        left_m = [m for m in part_metrics if "left" in m.get("_raw_part_name", "")]
        right_m = [m for m in part_metrics if "right" in m.get("_raw_part_name", "")]
        return (
            f'<div class="ds-exp-bilateral-cols">'
            f'<div class="ds-exp-bilateral-side">'
            f'<div class="ds-exp-bilateral-label">왼쪽</div>'
            f'{_metric_groups_html(left_m)}'
            f'</div>'
            f'<div class="ds-exp-bilateral-divider"></div>'
            f'<div class="ds-exp-bilateral-side">'
            f'<div class="ds-exp-bilateral-label">오른쪽</div>'
            f'{_metric_groups_html(right_m)}'
            f'</div>'
            f'</div>'
        )
    return _metric_groups_html(part_metrics)


def _expert_part_inner_html(part: dict, metrics_map: dict) -> str:
    """Summary + chips + metric section HTML for one part (no outer card wrapper)."""
    summary = part.get("summary") or "요약 정보가 없습니다."
    issues = part.get("issues") or []
    chips = ""
    for issue in issues:
        lbl = _issue_label(issue)
        if not lbl:
            continue
        sev = issue.get("severity", "normal")
        ic, _ = _SEV_COLOR.get(sev, ("#10B981", "양호"))
        chips += f'<span class="ds-exp-chip" style="border-color:{ic}44;color:{ic};">{html.escape(lbl)}</span>'
    chips_html = f'<div class="ds-exp-chips">{chips}</div>' if chips else ""
    name = part.get("display_part_name", "부위")
    metrics_html = _expert_metrics_html(metrics_map.get(name, []))
    return (
        f'<div class="ds-exp-summary">{html.escape(summary)}</div>'
        f'{chips_html}'
        f'<div class="ds-exp-metrics">{metrics_html}</div>'
    )


def _render_expert_panel(
    part_reports: list[dict],
    metrics_by_part: dict | None = None,
) -> None:
    metrics_map = metrics_by_part or {}
    # Deduplicate by display_part_name — keep the entry with worst severity
    seen: dict[str, dict] = {}
    for part in _sort_parts(part_reports):
        name = part.get("display_part_name", "")
        if name not in seen:
            seen[name] = part
        else:
            # Replace if this entry has a worse severity
            existing_worst = _worst_severity(seen[name].get("issues") or [])
            new_worst = _worst_severity(part.get("issues") or [])
            if _SEVERITY_ORDER.get(new_worst, 0) > _SEVERITY_ORDER.get(existing_worst, 0):
                seen[name] = part
    unique_parts = list(seen.values())

    st.markdown('<div class="ds-exp-panel-header">부위별 상세 지표</div>', unsafe_allow_html=True)

    with st.container(key="ds_expert_panel"):
        for i in range(0, len(unique_parts), 2):
            row = unique_parts[i:i + 2]
            cols = st.columns(len(row), gap="medium")
            for col, part in zip(cols, row):
                with col:
                    _render_expert_part_card(part, metrics_map)


def _render_expert_part_card(part: dict, metrics_map: dict) -> None:
    name = part.get("display_part_name", "부위")
    worst = _worst_severity(part.get("issues") or [])
    color, sev_label = _SEV_COLOR.get(worst, ("#10B981", "양호"))
    inner = _expert_part_inner_html(part, metrics_map)
    st.markdown(
        f'<details class="ds-exp-det" open>'
        f'<summary class="ds-exp-det-sum">'
        f'<div class="ds-exp-det-left">'
        f'<span class="ds-exp-card-name">{html.escape(name)}</span>'
        f'<span class="ds-exp-sev-badge" style="color:{color};background:{color}18;">{sev_label}</span>'
        f'</div>'
        f'</summary>'
        f'<div class="ds-exp-det-body">{inner}</div>'
        f'</details>',
        unsafe_allow_html=True,
    )


def _render_detail_expanders(
    part_reports: list[dict],
    metrics_by_part: dict | None = None,
    expert_mode: bool = False,
):
    metrics_map = metrics_by_part or {}
    for part in _sort_parts(part_reports):
        part_name = part.get("display_part_name", "부위")
        summary = part.get("summary") or "요약 정보가 없습니다."
        issues = part.get("issues") or []
        part_metrics = metrics_map.get(part_name, [])
        with st.expander(f"{part_name} 상세 보기", expanded=False):
            st.markdown(f'<div class="ds-detail-summary">{html.escape(summary)}</div>', unsafe_allow_html=True)
            if issues:
                rows = "".join(_issue_row_html(issue) for issue in issues)
                st.markdown(f'<div class="ds-detail-issues">{rows}</div>', unsafe_allow_html=True)
            if part_metrics:
                _render_metrics_section(part_metrics, expert_mode)


def _render_recommendation_grid(part_reports: list[dict], metrics_by_part: dict | None = None):
    concern_groups = _build_concern_groups(part_reports, metrics_by_part or {})
    data = _collect_recommendations(part_reports)

    # ── 피부 고민별 성분 추천 ─────────────────────────────────────────
    if concern_groups:
        st.markdown('<div class="ds-rec-concern-header">피부 고민별 성분 추천</div>', unsafe_allow_html=True)
        for i in range(0, len(concern_groups), 2):
            row = concern_groups[i:i + 2]
            cols = st.columns(len(row), gap="medium")
            for col, grp in zip(cols, row):
                with col:
                    st.markdown(_concern_group_card_html(grp), unsafe_allow_html=True)

    # ── 하단 3열: 카테고리 / 주의 성분 / 관리 팁 ─────────────────────
    st.markdown('<div class="ds-rec-bottom-header">추가 케어 정보</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2, 1, 2], gap="medium")
    with c1:
        chips = "".join(_tag_html(item, "category") for item in data["categories"][:8]) or _tag_html("추천 정보 없음", "category")
        st.markdown(
            f'<div class="ds-rec-mini-card">'
            f'<div class="ds-rec-mini-title">추천 카테고리</div>'
            f'<div class="ds-rec-mini-body">{chips}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c2:
        chips = "".join(_tag_html(item, "excluded") for item in data["excluded"][:6]) or _tag_html("없음", "excluded")
        st.markdown(
            f'<div class="ds-rec-mini-card">'
            f'<div class="ds-rec-mini-title">주의 성분</div>'
            f'<div class="ds-rec-mini-body">{chips}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c3:
        items = data["tips"][:4] or ["꾸준한 보습과 자외선 차단을 유지하세요."]
        tips_html = "".join(f'<div class="ds-rec-tip-item">{html.escape(t)}</div>' for t in items)
        st.markdown(
            f'<div class="ds-rec-mini-card">'
            f'<div class="ds-rec-mini-title">관리 팁</div>'
            f'<div class="ds-rec-mini-body">{tips_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


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


def _get_detail_value_label(issue: dict) -> tuple[str | None, float | None]:
    measured = issue.get("measured_value")
    predicted = issue.get("predicted_value")
    if measured is not None:
        return "측정값", float(measured)
    if predicted is not None:
        return "예측값", float(predicted)
    return None, None


def _issue_row_html(issue: dict) -> str:
    label = issue.get("metric_display_name") or _issue_label(issue) or "분석 항목"
    severity = issue.get("severity", "normal")
    grade = issue.get("grade_value")
    grade_text = f"등급 {grade}" if grade is not None else SEVERITY_LABEL.get(severity, severity)
    value_label, value = _get_detail_value_label(issue)
    detail_html = (
        f'<span class="ds-detail-value">{html.escape(value_label)}: {value:.2f}</span>'
        if value_label is not None
        else ""
    )
    return (
        '<div class="ds-detail-issue-row">'
        f'<div><strong>{html.escape(label)}</strong><span>{html.escape(grade_text)}</span>{detail_html}</div>'
        f'{_badge_html(SEVERITY_LABEL.get(severity, severity), severity)}'
        '</div>'
    )


_CONCERN_META: dict[str, tuple[str, str, str]] = {
    # key: (한글명, 아이콘, 색상)
    "wrinkle":      ("주름",        "📏", "#7C3AED"),
    "pore":         ("모공",        "🔬", "#0891B2"),
    "moisture":     ("수분 부족",   "💧", "#2563EB"),
    "dryness":      ("건조",        "🌵", "#D97706"),
    "sagging":      ("처짐",        "✨", "#059669"),
    "elasticity":   ("탄력",        "✨", "#059669"),
    "pigmentation": ("색소침착",    "🌑", "#D97706"),
    "acne":         ("여드름",      "🔴", "#DC2626"),
}

# concern issue_type → 관련 metric_group 목록
# 예) 처짐(sagging) 이슈는 탄력(elasticity) 측정값을 보여줌
_CONCERN_TO_METRIC_GROUPS: dict[str, list[str]] = {
    "wrinkle":      ["wrinkle"],
    "pore":         ["pore"],
    "moisture":     ["moisture"],
    "dryness":      ["moisture"],
    "sagging":      ["elasticity"],
    "elasticity":   ["elasticity"],
    "pigmentation": ["pigmentation"],
    "acne":         ["acne"],
}


def _build_concern_groups(
    part_reports: list[dict],
    metrics_by_part: dict,
) -> list[dict]:
    groups: dict[str, dict] = {}

    # 전체 얼굴 메트릭 (pigmentation_count, acne_count 등) — 모든 파트에서 공유
    full_face_metrics = [
        {**m, "_raw_part_name": "full_face"}
        for m in metrics_by_part.get("전체 얼굴", [])
        if _is_basic_metric(m) and not m.get("is_dummy")
    ]

    for part in part_reports:
        part_name = part.get("display_part_name", "")
        issues = part.get("issues") or []
        rec = part.get("recommendation") or {}
        part_ings = [i.get("name", "") for i in (rec.get("ingredients") or [])]
        own_metrics = [
            m for m in metrics_by_part.get(part_name, [])
            if _is_basic_metric(m) and not m.get("is_dummy")
        ]
        # 파트 자체 메트릭 + 전체 얼굴 메트릭 합산
        part_metrics = own_metrics + full_face_metrics

        for issue in issues:
            itype = issue.get("issue_type", "")
            sev = issue.get("severity", "normal")
            if not itype:
                continue
            if itype not in groups:
                label, icon, color = _CONCERN_META.get(itype, (itype, "◌", "#64748B"))
                groups[itype] = {
                    "label": label,
                    "icon": icon,
                    "color": color,
                    "worst": sev,
                    "ingredients": [],
                    "metrics": [],
                }
            g = groups[itype]
            if _SEVERITY_ORDER.get(sev, 0) > _SEVERITY_ORDER.get(g["worst"], 0):
                g["worst"] = sev

            for ing in part_ings:
                if ing and ing not in g["ingredients"]:
                    g["ingredients"].append(ing)

            allowed_groups = _CONCERN_TO_METRIC_GROUPS.get(itype, [itype])
            raw_names = {m.get("_raw_part_name", "") for m in own_metrics}
            bilateral = any("left" in r for r in raw_names) and any("right" in r for r in raw_names)
            for m in part_metrics:
                if m.get("metric_group", "") not in allowed_groups:
                    continue
                raw = m.get("_raw_part_name", "")
                if raw == "full_face":
                    lbl = f"전체 얼굴 {_metric_label(m, bilateral=False)}"
                else:
                    lbl = f"{part_name} {_metric_label(m, bilateral=bilateral)}"
                val = m.get("value", 0.0)
                vtype = m.get("value_type", "reg")
                fmt = str(int(round(val))) if vtype == "count" else f"{val:.3f}"
                entry = {"label": lbl, "formatted": fmt, "value": val}
                if not any(e["label"] == lbl for e in g["metrics"]):
                    g["metrics"].append(entry)

    return sorted(
        groups.values(),
        key=lambda g: _SEVERITY_ORDER.get(g["worst"], 0),
        reverse=True,
    )


def _concern_group_card_html(grp: dict) -> str:
    color = grp["color"]
    icon = grp.get("icon", "◌")
    sev_color, sev_label = _SEV_COLOR.get(grp["worst"], ("#64748B", "양호"))
    has_metrics = bool(grp["metrics"])

    metric_chips = "".join(
        f'<span class="ds-cg-metric-chip">'
        f'<span class="ds-cg-metric-label">{html.escape(e["label"])}</span>'
        f'<span class="ds-cg-metric-val">{html.escape(e["formatted"])}</span>'
        f'</span>'
        for e in grp["metrics"][:6]
    ) if has_metrics else '<span class="ds-cg-no-metric">측정값 없음</span>'

    ing_chips = "".join(
        f'<span class="ds-cg-ing-chip" style="color:{color};background:{color}14;border:1px solid {color}30;">'
        f'{html.escape(ing)}</span>'
        for ing in grp["ingredients"][:8]
    ) if grp["ingredients"] else '<span class="ds-cg-no-ing">추천 성분 없음</span>'

    # 성분 추천이 있으면 측정값 없어도 정상 카드로 표시
    dim_cls = " ds-cg-card-dim" if not has_metrics and not grp["ingredients"] else ""

    metric_section = (
        f'<div class="ds-cg-section-lbl">측정값</div>'
        f'<div class="ds-cg-metrics">{metric_chips}</div>'
    ) if has_metrics else ""

    return (
        f'<div class="ds-cg-card{dim_cls}" style="border-top:3px solid {color};">'
        f'<div class="ds-cg-head">'
        f'<span class="ds-cg-icon" style="background:{color}14;color:{color};">{icon}</span>'
        f'<span class="ds-cg-name" style="color:{color};">{html.escape(grp["label"])}</span>'
        f'<span class="ds-cg-sev" style="color:{sev_color};background:{sev_color}18;">{sev_label}</span>'
        f'</div>'
        f'{metric_section}'
        f'<div class="ds-cg-divider"></div>'
        f'<div class="ds-cg-section-lbl">추천 성분</div>'
        f'<div class="ds-cg-ings">{ing_chips}</div>'
        f'</div>'
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
    order = ["눈가", "볼", "턱", "입술", "이마", "미간", "전체 얼굴"]

    def key(part: dict):
        name = part.get("display_part_name", "")
        for idx, label in enumerate(order):
            if label in name:
                return idx
        return len(order)

    return sorted(part_reports, key=key)


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
        "미간": "Glabella.png",
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
    frontend_root = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(frontend_root, "assets", "icons", filename)
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


def _load_metrics(token: str | None, session_id: int | None) -> list[dict]:
    if not token or not session_id:
        return []
    resp = analysis_api.get_session_metrics(token, session_id)
    if api_client.is_error(resp):
        return []
    return resp.get("parts") or []


def _build_metrics_map(parts: list[dict]) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for part in parts:
        dpn = part.get("display_part_name") or ""
        rpn = part.get("raw_part_name") or ""
        if not dpn:
            continue
        if dpn not in result:
            result[dpn] = []
        for m in (part.get("metrics") or []):
            result[dpn].append({**m, "_raw_part_name": rpn})
    return result


def _metric_label(metric: dict, bilateral: bool = False) -> str:
    group = metric.get("metric_group", "")
    name = metric.get("metric_name", "")
    key = f"{group}_{name}"
    base = _METRIC_DISPLAY.get(key) or (f"{group} {name}".strip() if name and name != group else group)
    if bilateral:
        raw = metric.get("_raw_part_name", "")
        if "left" in raw:
            return f"{base} (좌)"
        if "right" in raw:
            return f"{base} (우)"
    return base


def _is_basic_metric(metric: dict) -> bool:
    return (metric.get("metric_group"), metric.get("metric_name")) in _BASIC_METRICS


def _render_metrics_section(metrics: list[dict], expert_mode: bool) -> None:
    if expert_mode:
        visible = metrics
    else:
        visible = [m for m in metrics if _is_basic_metric(m) and not m.get("is_dummy")]
    if not visible:
        return

    raw_names = {m.get("_raw_part_name", "") for m in visible}
    bilateral = any("left" in r for r in raw_names) and any("right" in r for r in raw_names)

    def _make_row(m: dict) -> str:
        label = html.escape(_metric_label(m, bilateral=bilateral))
        value = m.get("value", 0.0)
        value_type = m.get("value_type", "reg")
        is_dummy = m.get("is_dummy", False)
        formatted = str(int(round(value))) if value_type == "count" else f"{value:.3f}"
        dummy_badge = (
            ' <span class="ds-metric-dummy-badge">미학습</span>'
            if is_dummy and expert_mode
            else ""
        )
        return (
            f'<div class="ds-metric-row">'
            f'<span class="ds-metric-name">{label}{dummy_badge}</span>'
            f'<span class="ds-metric-value">{html.escape(formatted)}</span>'
            f'</div>'
        )

    if not expert_mode:
        rows_html = [_make_row(m) for m in visible]
        st.markdown(
            '<div class="ds-metrics-header">주요 측정 지표</div>'
            f'<div class="ds-metrics-list">{"".join(rows_html)}</div>',
            unsafe_allow_html=True,
        )
        return

    # 전문가 모드: metric_group별로 묶어서 표시
    _GROUP_ORDER = ["moisture", "pore", "pigmentation", "acne", "elasticity", "wrinkle"]
    groups: dict[str, list[dict]] = {}
    for m in visible:
        g = m.get("metric_group", "기타")
        groups.setdefault(g, []).append(m)
    sorted_keys = sorted(
        groups.keys(),
        key=lambda g: _GROUP_ORDER.index(g) if g in _GROUP_ORDER else 99,
    )

    st.markdown('<div class="ds-metrics-header">상세 측정값 (전문가)</div>', unsafe_allow_html=True)
    for group_key in sorted_keys:
        group_label = html.escape(_GROUP_DISPLAY.get(group_key, group_key))
        rows_html = [_make_row(m) for m in groups[group_key]]
        st.markdown(
            f'<div class="ds-metrics-group-block">'
            f'<div class="ds-metrics-group-label">{group_label}</div>'
            f'<div class="ds-metrics-list">{"".join(rows_html)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_trends_section(
    token: str | None, session_id: int | None, expert_mode: bool = False
) -> None:
    if not token or not session_id:
        return

    st.markdown(
        '<div class="ds-report-section-title ds-report-section-spaced">피부 측정 추이</div>',
        unsafe_allow_html=True,
    )

    show_trends = st.toggle("추이 그래프 보기", key="show_trends")
    if not show_trends:
        return

    cache_key = f"trends_{session_id}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = _fetch_all_trends(token)

    trends_data = st.session_state[cache_key]
    has_any = any(trend is not None for _, trend in trends_data)

    st.markdown('<div class="ds-trend-charts-container">', unsafe_allow_html=True)
    if has_any:
        for label, trend in trends_data:
            if trend is not None:
                _render_trend_chart(label, trend)
    else:
        st.markdown(
            '<div class="ds-trend-empty-state">'
            '<div class="ds-trend-empty-icon">📊</div>'
            '<div class="ds-trend-empty-text">추이 데이터를 불러올 수 없습니다.<br>잠시 후 다시 시도해주세요.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    if expert_mode:
        _render_expert_trend_selector(token, session_id)


def _fetch_all_trends(token: str) -> list[tuple[str, list[dict] | None]]:
    """기본 지표 목록의 추이 데이터를 가져온다. API 실패 시 해당 항목은 None으로 처리."""
    results = []
    for raw_part, group, name, label in _TREND_METRICS:
        try:
            resp = analysis_api.get_metric_trends(token, raw_part, group, name, limit=10)
            if api_client.is_error(resp):
                results.append((label, None))
            else:
                results.append((label, resp.get("trend") or []))
        except Exception:
            results.append((label, None))
    return results


def _render_trend_chart(label: str, trend: list[dict]) -> None:
    with st.expander(label, expanded=False):
        if trend is None:
            st.markdown(
                '<div class="ds-trend-no-data">데이터를 불러오지 못했습니다.</div>',
                unsafe_allow_html=True,
            )
            return

        if len(trend) == 0:
            st.markdown(
                '<div class="ds-trend-no-data">분석 데이터가 없습니다.</div>',
                unsafe_allow_html=True,
            )
            return

        if len(trend) == 1:
            value = trend[0]["value"]
            date_str = trend[0]["analyzed_at"][:10]
            st.markdown(
                f'<div class="ds-trend-single-value">'
                f'<div class="ds-trend-single-num">{value:.3f}</div>'
                f'<div class="ds-trend-single-date">{html.escape(date_str)}</div>'
                f'<div class="ds-trend-single-hint">추이를 표시하려면 2회 이상 분석이 필요합니다.</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            return

        dates = [point["analyzed_at"][:10] for point in trend]
        values = [point["value"] for point in trend]
        st.line_chart({"날짜": dates, "값": values}, x="날짜", y="값")


def _render_expert_trend_selector(token: str, session_id: int) -> None:
    st.markdown(
        '<div class="ds-trends-expert-header">지표 직접 선택</div>',
        unsafe_allow_html=True,
    )

    parts = list(_TREND_METRIC_OPTIONS.keys())
    part_labels = [_PART_DISPLAY.get(p, p) for p in parts]

    col1, col2, col3 = st.columns(3, gap="small")
    with col1:
        sel_part_label = st.selectbox("부위", options=part_labels, key="expert_sel_part")
    sel_part = parts[part_labels.index(sel_part_label)]

    prev_part = st.session_state.get("_expert_prev_part")
    if prev_part != sel_part:
        st.session_state.pop("expert_sel_group", None)
        st.session_state.pop("expert_sel_name", None)
        st.session_state["_expert_prev_part"] = sel_part

    groups = list(_TREND_METRIC_OPTIONS[sel_part].keys())
    group_labels = [_GROUP_DISPLAY.get(g, g) for g in groups]

    with col2:
        sel_group_label = st.selectbox("지표 그룹", options=group_labels, key="expert_sel_group")
    sel_group = groups[group_labels.index(sel_group_label)]

    prev_group = st.session_state.get("_expert_prev_group")
    if prev_group != sel_group:
        st.session_state.pop("expert_sel_name", None)
        st.session_state["_expert_prev_group"] = sel_group

    names = _TREND_METRIC_OPTIONS[sel_part][sel_group]
    with col3:
        sel_name = st.selectbox("세부 지표", options=names, key="expert_sel_name")

    chart_key = f"expert_trend_chart_{session_id}"
    if st.button("추이 조회", key="expert_trend_query"):
        chart_label = (
            f"{_PART_DISPLAY.get(sel_part, sel_part)} "
            f"{_metric_name_display(sel_group, sel_name)}"
        )
        try:
            resp = analysis_api.get_metric_trends(token, sel_part, sel_group, sel_name, limit=10)
            if api_client.is_error(resp):
                st.session_state[chart_key] = {"ok": False, "label": chart_label, "trend": None}
            else:
                st.session_state[chart_key] = {
                    "ok": True,
                    "label": chart_label,
                    "trend": resp.get("trend") or [],
                }
        except Exception:
            st.session_state[chart_key] = {"ok": False, "label": chart_label, "trend": None}

    cached = st.session_state.get(chart_key)
    if cached is not None:
        if not cached["ok"]:
            st.warning("데이터를 불러오지 못했습니다.")
        else:
            _render_trend_chart(cached["label"], cached["trend"])


def _inject_report_css():
    load_css("report.css")
