import base64
import os

import streamlit as st

from styles.theme import SKIN_TYPE_OPTIONS, MAIN_CONCERN_OPTIONS


# ── 아이콘 헬퍼 ──────────────────────────────────────────────────────────────

def _b64_src(rel: str) -> str:
    path = os.path.join("assets", "icons", rel)
    try:
        with open(path, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    except Exception:
        return ""


def _img(rel: str, size: int = 20) -> str:
    src = _b64_src(rel)
    if not src:
        return ""
    return (
        f'<img src="{src}" width="{size}" height="{size}" '
        f'style="object-fit:contain;vertical-align:middle;margin-right:6px;">'
    )


# ── 공통 헬퍼 ─────────────────────────────────────────────────────────────────

def _chip(text: str, variant: str = "default") -> str:
    cls_map = {
        "concern":  "ds-chip ds-chip-concern",
        "excluded": "ds-chip ds-chip-excluded",
        "category": "ds-chip ds-chip-category",
        "green":    "ds-chip ds-chip-green",
        "default":  "ds-chip",
    }
    return f'<span class="{cls_map.get(variant, "ds-chip")}">{text}</span>'


def _info_row(label: str, value: str) -> str:
    return (
        f'<div class="ds-info-row">'
        f'<span class="ds-info-label">{label}</span>'
        f'<span class="ds-info-value">{value}</span>'
        f'</div>'
    )


# ── 프로필 요약 헤더 카드 ─────────────────────────────────────────────────────

def render_profile_summary(profile: dict):
    gender_map = {"M": "남성", "F": "여성"}
    gender     = gender_map.get(profile.get("gender", ""), "—")
    age        = profile.get("age") or "—"
    skin_label = SKIN_TYPE_OPTIONS.get(profile.get("skin_type"), "—")
    sensitive  = profile.get("sensitive")

    sensitive_badge = (
        '<span class="ds-badge ds-badge-severe" style="font-size:11px;">민감성</span>'
        if sensitive == 1 else
        '<span class="ds-badge ds-badge-normal" style="font-size:11px;">비민감성</span>'
        if sensitive == 0 else ""
    )
    skin_badge = f'<span class="ds-badge ds-badge-info" style="font-size:11px;">{skin_label}</span>'

    # 아바타: 프로필 아바타 이미지 또는 CSS 원형
    avatar_src = _b64_src("auth/profile_avatar.png")
    if avatar_src:
        avatar_html = (
            f'<img src="{avatar_src}" width="64" height="64" '
            f'style="border-radius:50%;object-fit:cover;border:3px solid #EEF4FF;">'
        )
    else:
        avatar_html = '<div class="ds-avatar">👤</div>'

    # 맞춤 분석 설정 완료 카드
    sparkle_src = _b64_src("analysis/sparkle.png")
    sparkle = (
        f'<img src="{sparkle_src}" width="18" '
        f'style="vertical-align:middle;margin-right:4px;">'
        if sparkle_src else "✦"
    )
    complete = "완료" if profile.get("skin_type") else "미완성"
    complete_color = "#15803D" if complete == "완료" else "#92400E"
    complete_bg    = "#F0FDF4" if complete == "완료" else "#FFFBEB"

    st.markdown(f"""
    <div class="ds-profile-header">
        <div style="flex-shrink:0;">{avatar_html}</div>
        <div style="flex:1;min-width:0;">
            <div style="font-size:20px;font-weight:800;color:#0F2447;margin-bottom:6px;">
                {gender} · {age}세
            </div>
            <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;">
                {skin_badge}
                {sensitive_badge}
            </div>
        </div>
        <div style="background:{complete_bg};border-radius:16px;padding:16px 20px;
                    border:1px solid {'#BBF7D0' if complete=='완료' else '#FDE68A'};
                    min-width:180px;flex-shrink:0;">
            <div style="font-size:13px;font-weight:700;color:{complete_color};
                        margin-bottom:4px;">{sparkle} 맞춤 분석 설정 {complete}</div>
            <div style="font-size:12px;color:#6B7894;line-height:1.5;">
                피부 타입·고민·알레르기 정보가<br>분석에 반영됩니다.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── 기본 정보 카드 ────────────────────────────────────────────────────────────

def render_basic_info_card(profile: dict):
    gender_map = {"M": "남성", "F": "여성"}
    age        = profile.get("age") or "—"
    birth_year = profile.get("birth_year") or "—"
    gender     = gender_map.get(profile.get("gender", ""), "—")

    rows = (
        _info_row("나이",    f"{age}세")
        + _info_row("출생연도", f"{birth_year}년" if birth_year != "—" else "—")
        + _info_row("성별",   gender)
    )
    st.markdown(f"""
    <div class="ds-card">
        <div class="ds-card-title">📋 기본 정보</div>
        {rows}
    </div>
    """, unsafe_allow_html=True)


# ── 피부 정보 카드 ────────────────────────────────────────────────────────────

def render_skin_info_card(profile: dict):
    skin_label = SKIN_TYPE_OPTIONS.get(profile.get("skin_type"), "—")
    sensitive  = profile.get("sensitive")
    if sensitive == 1:
        sens_txt, sens_color = "예", "#EF4444"
    elif sensitive == 0:
        sens_txt, sens_color = "아니요", "#10B981"
    else:
        sens_txt, sens_color = "—", "#6B7894"

    st.markdown(f"""
    <div class="ds-card">
        <div class="ds-card-title">🌿 피부 정보</div>
        {_info_row("피부 타입", skin_label)}
        <div class="ds-info-row">
            <span class="ds-info-label">민감성 피부</span>
            <span style="font-weight:700;color:{sens_color};font-size:14px;">{sens_txt}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── 주요 고민 카드 ────────────────────────────────────────────────────────────

def render_concerns_card(profile: dict):
    concerns = profile.get("main_concerns") or []
    if concerns:
        chips = " ".join(
            _chip(MAIN_CONCERN_OPTIONS.get(k, k), "concern") for k in concerns
        )
    else:
        chips = '<span style="color:#A0AABB;font-size:14px;">등록된 고민이 없습니다.</span>'

    st.markdown(f"""
    <div class="ds-card">
        <div class="ds-card-title">💡 주요 피부 고민</div>
        <div style="padding-top:4px;line-height:2;">{chips}</div>
    </div>
    """, unsafe_allow_html=True)


# ── 알레르기 성분 카드 ────────────────────────────────────────────────────────

def render_allergy_card(profile: dict):
    allergy = profile.get("allergy_ingredients") or []
    if allergy and allergy != ["없음"]:
        chips = " ".join(_chip(item, "excluded") for item in allergy)
        note  = '<div style="font-size:12px;color:#A0AABB;margin-top:10px;">추천 시 해당 성분이 자동으로 제외됩니다.</div>'
    else:
        chips = '<span style="color:#A0AABB;font-size:14px;">알레르기 성분 없음</span>'
        note  = ""

    st.markdown(f"""
    <div class="ds-card">
        <div class="ds-card-title">⚠️ 알레르기 성분</div>
        <div style="padding-top:4px;line-height:2;">{chips}</div>
        {note}
    </div>
    """, unsafe_allow_html=True)


# ── 선호 제품 타입 카드 ───────────────────────────────────────────────────────

def render_products_card(profile: dict):
    products = profile.get("preferred_product_types") or []
    if products:
        chips = " ".join(_chip(p) for p in products)
    else:
        chips = '<span style="color:#A0AABB;font-size:14px;">등록된 선호 제품이 없습니다.</span>'

    st.markdown(f"""
    <div class="ds-card">
        <div class="ds-card-title">🛍️ 선호 제품 타입</div>
        <div style="padding-top:4px;line-height:2;">{chips}</div>
    </div>
    """, unsafe_allow_html=True)


# ── 계정 및 보안 카드 ─────────────────────────────────────────────────────────

def render_account_card(profile: dict):
    email     = profile.get("email", "—")
    join_date = profile.get("created_at", "")
    join_str  = join_date[:10] if join_date else "—"

    st.markdown(f"""
    <div class="ds-card">
        <div class="ds-card-title">🔒 계정 및 보안</div>
        {_info_row("이메일",   email)}
        {_info_row("가입일",   join_str)}
    </div>
    """, unsafe_allow_html=True)
