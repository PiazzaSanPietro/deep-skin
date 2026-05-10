import base64
import os

import streamlit as st

from services import user_api, api_client
from components.common import show_error, show_success, handle_401
from components.layout import render_page_header
from styles.theme import SKIN_TYPE_OPTIONS, MAIN_CONCERN_OPTIONS, PREFERRED_PRODUCT_OPTIONS


# ── 진입점 ───────────────────────────────────────────────────────────────────

def show():
    render_page_header(
        "프로필 수정",
        "개인 정보와 피부 맞춤 설정을 수정하세요.",
    )
    _ensure_profile_loaded()
    _render_form()


# ── 기존 프로필 로드 ──────────────────────────────────────────────────────────

def _ensure_profile_loaded():
    if "profile_form_data" not in st.session_state:
        token  = st.session_state.get("access_token")
        result = user_api.get_profile(token)
        if not api_client.is_error(result):
            st.session_state["profile_form_data"] = result
        else:
            st.session_state["profile_form_data"] = {}


# ── 폼 렌더링 ─────────────────────────────────────────────────────────────────

def _render_form():
    existing:   dict = st.session_state.get("profile_form_data", {})
    from_login: bool = st.session_state.get("profile_edit_from_login", False)

    if from_login:
        st.info("피부 분석 추천을 위해 프로필을 먼저 입력해주세요.", icon="💡")

    # 2열: 폼(좌 3) + 안내 카드(우 1)
    col_form, col_guide = st.columns([3, 1], gap="large")

    with col_guide:
        _render_guide_card()

    with col_form:
        with st.form("profile_edit_form"):

            # ── 기본 정보 ─────────────────────────────
            st.markdown("#### 기본 정보")
            c1, c2, c3 = st.columns([2, 2, 2])

            with c1:
                age = st.number_input(
                    "나이 *",
                    min_value=1, max_value=149,
                    value=existing.get("age") or 25,
                    step=1,
                )
            with c2:
                birth_year = st.number_input(
                    "출생연도",
                    min_value=1900, max_value=2025,
                    value=existing.get("birth_year") or 1999,
                    step=1,
                )
            with c3:
                gender_map     = {"M": "남성", "F": "여성"}
                gender_options = list(gender_map.values())
                existing_gender_label = gender_map.get(existing.get("gender", ""), "남성")
                gender_label = st.selectbox(
                    "성별 *",
                    options=gender_options,
                    index=gender_options.index(existing_gender_label),
                )
                gender = "M" if gender_label == "남성" else "F"

            # ── 피부 정보 ─────────────────────────────
            st.markdown("#### 피부 정보")
            c4, c5 = st.columns([2, 2])

            with c4:
                skin_type_labels = list(SKIN_TYPE_OPTIONS.values())
                skin_type_codes  = list(SKIN_TYPE_OPTIONS.keys())
                existing_skin    = existing.get("skin_type") or 1
                skin_idx = skin_type_codes.index(existing_skin) if existing_skin in skin_type_codes else 0
                skin_type_label = st.selectbox(
                    "피부 타입 *",
                    options=skin_type_labels,
                    index=skin_idx,
                )
                skin_type = skin_type_codes[skin_type_labels.index(skin_type_label)]

            with c5:
                sensitive_options = ["아니요", "예"]
                existing_sensitive = existing.get("sensitive")
                sensitive_idx = 1 if existing_sensitive == 1 else 0
                sensitive_label = st.selectbox(
                    "민감성 피부 *",
                    options=sensitive_options,
                    index=sensitive_idx,
                )
                sensitive = 1 if sensitive_label == "예" else 0

            # ── 주요 고민 ─────────────────────────────
            st.markdown("#### 주요 피부 고민 *")
            concern_labels = list(MAIN_CONCERN_OPTIONS.values())
            concern_keys   = list(MAIN_CONCERN_OPTIONS.keys())
            existing_concerns = existing.get("main_concerns") or []
            existing_concern_labels = [
                MAIN_CONCERN_OPTIONS[k] for k in existing_concerns
                if k in MAIN_CONCERN_OPTIONS
            ]
            selected_concern_labels = st.multiselect(
                "주요 피부 고민을 선택하세요 (최소 1개)",
                options=concern_labels,
                default=existing_concern_labels,
            )
            main_concerns = [
                concern_keys[concern_labels.index(lbl)]
                for lbl in selected_concern_labels
            ]

            # ── 알러지 성분 ───────────────────────────
            st.markdown("#### 알러지 성분 *")
            existing_allergy = existing.get("allergy_ingredients") or []
            allergy_input = st.text_area(
                "알러지가 있는 성분을 쉼표로 구분하여 입력하세요",
                value=", ".join(existing_allergy),
                placeholder="예: retinol, BHA, 알코올",
                height=80,
            )
            st.caption("알러지 성분이 없으면 '없음' 또는 '해당없음'을 입력하세요.")

            # ── 선호 제품 타입 ────────────────────────
            st.markdown("#### 선호 제품 타입 *")
            existing_products = existing.get("preferred_product_types") or []
            selected_products = st.multiselect(
                "선호하는 제품 타입을 선택하세요 (최소 1개)",
                options=PREFERRED_PRODUCT_OPTIONS,
                default=[p for p in existing_products if p in PREFERRED_PRODUCT_OPTIONS],
            )

            st.markdown("---")

            # ── 버튼 ──────────────────────────────────
            if from_login:
                submitted = st.form_submit_button(
                    "저장하고 분석 시작 →", use_container_width=True
                )
                cancelled = False
            else:
                col_save, col_cancel = st.columns([3, 1])
                with col_save:
                    submitted = st.form_submit_button("저장하기", use_container_width=True)
                with col_cancel:
                    cancelled = st.form_submit_button("취소", use_container_width=True)

    # form 밖에서 취소 처리
    if cancelled:
        if "profile_form_data" in st.session_state:
            del st.session_state["profile_form_data"]
        st.session_state["current_page"] = "profile"
        st.rerun()

    if submitted:
        _handle_save(
            age=age,
            birth_year=birth_year,
            gender=gender,
            skin_type=skin_type,
            sensitive=sensitive,
            main_concerns=main_concerns,
            allergy_input=allergy_input,
            selected_products=selected_products,
        )


# ── 우측 안내 카드 — Streamlit 네이티브 컴포넌트로 구현 ──────────────────────

def _render_guide_card():
    """
    HTML 노출 버그 방지를 위해 st.markdown + unsafe_allow_html 대신
    Streamlit 네이티브 컴포넌트로 안내 카드를 렌더링한다.
    """
    # 카드 헤더
    st.markdown(
        '<div style="background:linear-gradient(160deg,#EEF4FF 0%,#F0EDFF 100%);">'
        '<div style="font-size:15px;font-weight:700;color:#0F2447;margin-bottom:18px;">'
        "✨ 맞춤 추천 반영 항목"
        "</div></div>",
        unsafe_allow_html=True,
    )

    for icon, title, desc in [
        ("🔬", "피부 분석 설정",   "피부 타입과 민감성 정보를 기반으로 AI 분석 결과를 해석합니다."),
        ("💡", "개인화 추천 반영", "주요 고민과 알레르기 성분 기반으로 맞춤 성분을 제안합니다."),
        ("🛍️", "선호 제품 맞춤",  "선호 제품 타입에 맞춘 추천 카테고리를 제공합니다."),
        ("🚫", "알레르기 성분 제외", "민감 피부 및 알레르기 성분은 추천에서 자동으로 제외됩니다."),
    ]:
        st.markdown(
            f'<div style="display:flex;gap:10px;margin-bottom:14px;align-items:flex-start;">'
            f'<span style="font-size:18px;flex-shrink:0;line-height:1.5;">{icon}</span>'
            f'<div>'
            f'<div style="font-size:13px;font-weight:700;color:#0F2447;">{title}</div>'
            f'<div style="font-size:12px;color:#6B7894;margin-top:2px;line-height:1.5;">{desc}</div>'
            f"</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div style="margin-top:16px;padding-top:14px;border-top:1px solid #DBEAFE;">'
        '<div style="font-size:11px;color:#93C5FD;font-weight:700;letter-spacing:0.05em;">TIP</div>'
        '<div style="font-size:12px;color:#6B7894;margin-top:4px;line-height:1.6;">'
        "프로필 정보가 정확할수록 AI 추천의 정확도가 높아집니다."
        "</div></div>",
        unsafe_allow_html=True,
    )


# ── 저장 처리 ─────────────────────────────────────────────────────────────────

def _handle_save(
    age: int,
    birth_year: int,
    gender: str,
    skin_type: int,
    sensitive: int,
    main_concerns: list[str],
    allergy_input: str,
    selected_products: list[str],
):
    allergy_raw = allergy_input.strip()
    if allergy_raw.lower() in ("없음", "해당없음", "none", "-", ""):
        allergy_ingredients = ["없음"]
    else:
        allergy_ingredients = [
            item.strip() for item in allergy_raw.replace(",", ",").split(",")
            if item.strip()
        ]

    errors = []
    if not main_concerns:
        errors.append("주요 피부 고민을 1개 이상 선택해주세요.")
    if not allergy_ingredients:
        errors.append("알러지 성분을 입력하거나 '없음'으로 입력해주세요.")
    if not selected_products:
        errors.append("선호 제품 타입을 1개 이상 선택해주세요.")

    if errors:
        for e in errors:
            show_error(e)
        return

    payload = {
        "age":                    age,
        "birth_year":             birth_year,
        "gender":                 gender,
        "skin_type":              skin_type,
        "sensitive":              sensitive,
        "main_concerns":          main_concerns,
        "allergy_ingredients":    allergy_ingredients,
        "preferred_product_types": selected_products,
    }

    token = st.session_state.get("access_token")
    with st.spinner("저장 중..."):
        result = user_api.update_profile(token, payload)

    if api_client.is_error(result):
        if result.get("_status") == 401:
            handle_401()
            return
        show_error(api_client.get_error_message(result))
        return

    show_success("프로필이 저장되었습니다.")
    st.session_state["profile_edit_from_login"] = False

    if "profile_form_data" in st.session_state:
        del st.session_state["profile_form_data"]

    st.session_state["current_page"] = "analysis"
    st.rerun()
