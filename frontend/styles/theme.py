import streamlit as st

# ── 컬러 팔레트 ────────────────────────────────────────────────────────────────
COLORS = {
    "navy":           "#0F2447",
    "blue":           "#4B7BFF",
    "teal":           "#3DD9C5",
    "lavender":       "#8B7CF6",
    "light_blue":     "#EEF4FF",
    "light_lavender": "#F3F0FF",
    "bg":             "#F7FAFF",
    "card":           "#FFFFFF",
    "text_main":      "#0F2447",
    "text_sub":       "#6B7894",
    "danger":         "#EF4444",
    "warning":        "#F59E0B",
    "success":        "#10B981",
    "border":         "#E4EAF5",
}

# ── severity 매핑 ─────────────────────────────────────────────────────────────
SEVERITY_LABEL = {
    "normal":   "양호",
    "mild":     "약한 관리 필요",
    "moderate": "관리 필요",
    "severe":   "집중 관리 필요",
}

SEVERITY_COLOR = {
    "normal":   ("#D1FAE5", "#065F46"),
    "mild":     ("#FEF3C7", "#92400E"),
    "moderate": ("#FED7AA", "#9A3412"),
    "severe":   ("#FEE2E2", "#991B1B"),
}

SEVERITY_SCORE = {
    "normal":   88,
    "mild":     68,
    "moderate": 45,
    "severe":   20,
}

# ── 도메인 상수 ───────────────────────────────────────────────────────────────
SKIN_TYPE_OPTIONS = {
    1: "건성",
    2: "지성",
    3: "복합성",
    4: "민감성",
    5: "정상",
}

MAIN_CONCERN_OPTIONS = {
    "pore":          "모공",
    "wrinkle":       "주름",
    "pigmentation":  "색소침착",
    "moisture":      "수분 부족",
    "dryness":       "건조",
    "sagging":       "처짐/탄력 저하",
    "acne":          "여드름",
}

PREFERRED_PRODUCT_OPTIONS = [
    "토너/스킨", "세럼/에센스", "에멀전/로션",
    "크림/모이스처라이저", "선크림", "마스크팩",
    "아이크림", "클렌징",
]

ALLERGY_INGREDIENT_OPTIONS: dict[str, str] = {
    "aha":              "AHA",
    "bha":              "BHA",
    "pha":              "PHA",
    "licorice_root":    "감초추출물",
    "glycerin":         "글리세린",
    "niacinamide":      "나이아신아마이드",
    "green_tea":        "녹차추출물",
    "retinol":          "레티놀",
    "madecassoside":    "마데카소사이드",
    "bakuchiol":        "바쿠치올",
    "beta_glucan":      "베타글루칸",
    "centella_asiatica":"병풀추출물",
    "bisabolol":        "비사보롤",
    "vitamin_c":        "비타민C",
    "vitamin_e":        "비타민E",
    "sulfur":           "설퍼",
    "ceramide":         "세라마이드",
    "squalane":         "스쿠알란",
    "shea_butter":      "시어버터",
    "adenosine":        "아데노신",
    "azelaic_acid":     "아젤라익애씨드",
    "allantoin":        "알란토인",
    "arbutin":          "알부틴",
    "alcohol":          "알코올",
    "houttuynia":       "어성초추출물",
    "urea":             "우레아",
    "fatty_acid":       "지방산",
    "zinc_pca":         "징크 PCA",
    "zinc_oxide":       "징크옥사이드",
    "calamine":         "칼라민",
    "coenzyme_q10":     "코엔자임Q10",
    "collagen":         "콜라겐",
    "cholesterol":      "콜레스테롤",
    "tranexamic_acid":  "트라넥사민산",
    "titanium_dioxide": "티타늄디옥사이드",
    "tea_tree":         "티트리",
    "panthenol":        "판테놀",
    "peptide":          "펩타이드",
    "fragrance":        "향료",
    "hyaluronic_acid":  "히알루론산",
}


def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800&display=swap');

    /* ══════════════════════════════════════════
       전체 기반
    ══════════════════════════════════════════ */
    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', 'Apple SD Gothic Neo', sans-serif;
    }
    .stApp {
        background-color: #F7FAFF !important;
    }
    #MainMenu { visibility: hidden; }
    footer    { visibility: hidden; }
    header[data-testid="stHeader"],
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"] {
        display: none !important;
        height: 0 !important;
    }
    .st-key-_ls_tokens,
    .st-key-_ls_tokens iframe,
    .st-key-_ls_r_at,
    .st-key-_ls_r_at iframe,
    .st-key-_ls_r_rt,
    .st-key-_ls_r_rt iframe {
        height: 0 !important;
        min-height: 0 !important;
        max-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
        border: 0 !important;
    }

    /* ══════════════════════════════════════════
       사이드바
    ══════════════════════════════════════════ */
    /* 앱 자체 좌측 메뉴를 사용하므로 Streamlit 네이티브 sidebar 토글은 숨긴다. */
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapseButton"] {
        display: none !important;
    }

    section[data-testid="stSidebar"] {
        background: #FFFFFF !important;
        border-right: 1px solid #E4EAF5 !important;
        min-width: 260px !important;
        max-width: 260px !important;
        box-shadow: 2px 0 12px rgba(15,36,71,0.06) !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        padding: 0 !important;
        overflow-y: auto;
    }

    /* 사이드바 버튼 — 투명 nav 스타일 */
    section[data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        color: #374151 !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        text-align: left !important;
        box-shadow: none !important;
        padding: 10px 16px !important;
        width: 100% !important;
        transition: background 0.15s, color 0.15s !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #F0F4FF !important;
        color: #4B7BFF !important;
    }

    /* 앱 내 좌측 메뉴: expanded / collapsed 상태를 분리해서 첫 렌더부터 안정적으로 적용 */
    .st-key-ds_sidebar_expanded,
    .st-key-ds_sidebar_collapsed {
        background:
            linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(247,250,255,0.96) 100%) !important;
        border: 1px solid rgba(196,211,242,0.82) !important;
        border-radius: 24px !important;
        box-shadow: 0 18px 46px rgba(31,54,94,0.10) !important;
        min-height: calc(100vh - 4rem) !important;
        position: sticky !important;
        top: 2rem !important;
        overflow: hidden !important;
        box-sizing: border-box !important;
    }
    .st-key-ds_sidebar_expanded {
        padding: 20px 20px 22px !important;
        display: flex !important;
        flex-direction: column !important;
    }
    .st-key-ds_sidebar_collapsed {
        padding: 14px 10px !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
    }
    .st-key-ds_sidebar_header {
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 12px !important;
        min-height: 50px !important;
    }
    .ds-sidebar-logo {
        height: 50px;
        display: flex;
        align-items: center;
    }
    .ds-sidebar-logo img {
        height: 38px !important;
        max-width: 166px !important;
    }
    .ds-sidebar-rule {
        height: 1px;
        background: #E9EFFB;
        margin: 12px 0 16px;
    }
    .ds-sidebar-rule-spaced {
        margin: 22px 0 18px;
    }
    .ds-sidebar-info-card {
        margin: 0 0 18px;
        background: linear-gradient(145deg, rgba(238,244,255,0.88) 0%, rgba(243,240,255,0.88) 100%);
        border-radius: 18px;
        padding: 18px 17px;
        border: 1px solid rgba(185,203,255,0.72);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.80);
    }
    .ds-sidebar-info-title {
        font-size: 13px;
        font-weight: 800;
        color: #4B7BFF;
        margin-bottom: 8px;
    }
    .ds-sidebar-info-text {
        font-size: 12px;
        color: #6B7894;
        line-height: 1.7;
    }
    .ds-sidebar-quota {
        margin-top: 16px;
        padding-top: 14px;
        border-top: 1px solid rgba(185,203,255,0.45);
    }
    .ds-sidebar-quota-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        color: #6B7894;
        font-size: 11px;
        font-weight: 700;
        margin-bottom: 9px;
    }
    .ds-sidebar-quota-row strong {
        color: #4B7BFF;
        font-size: 12px;
    }
    .ds-sidebar-quota-track {
        height: 7px;
        border-radius: 999px;
        background: #E6EEFF;
        overflow: hidden;
    }
    .ds-sidebar-quota-fill {
        width: 60%;
        height: 100%;
        border-radius: inherit;
        background: linear-gradient(90deg, #4B7BFF 0%, #3DD9C5 100%);
    }
    .ds-collapsed-divider {
        height: 1px;
        background: #E9EFFB;
        margin: 4px 2px 10px;
        width: 38px;
    }
    .st-key-ds_sidebar_logout {
        margin-top: auto !important;
        width: 100% !important;
    }
    .st-key-ds_sidebar_info {
        width: 100% !important;
    }
    .st-key-ds_sidebar_collapsed_logout {
        margin-top: auto !important;
    }

    /* ══════════════════════════════════════════
       메인 영역 — 여백 조정
    ══════════════════════════════════════════ */
    .block-container {
        padding-top: 2rem !important;
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
        max-width: none !important;
    }

    /* ══════════════════════════════════════════
       메인 영역 버튼 — gradient
    ══════════════════════════════════════════ */
    [data-testid="stMain"] .stButton > button,
    [data-testid="stForm"]  .stButton > button {
        background: linear-gradient(90deg, #4B7BFF 0%, #3DD9C5 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        padding: 11px 24px !important;
        box-shadow: 0 4px 16px rgba(75,123,255,0.28) !important;
        transition: opacity 0.2s !important;
    }
    [data-testid="stMain"] .stButton > button:hover,
    [data-testid="stForm"]  .stButton > button:hover {
        opacity: 0.88 !important;
        color: #FFFFFF !important;
    }

    .st-key-ds_sidebar_expanded .stButton > button {
        background: transparent !important;
        color: #5D6C86 !important;
        border: none !important;
        border-radius: 14px !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        text-align: left !important;
        box-shadow: none !important;
        padding: 12px 16px !important;
        width: 100% !important;
        min-height: 48px !important;
        transition: background 0.15s, color 0.15s, transform 0.15s !important;
    }
    .st-key-ds_sidebar_expanded .stButton > button:hover {
        background: rgba(238,244,255,0.90) !important;
        color: #4B7BFF !important;
        opacity: 1 !important;
        transform: translateX(2px);
    }
    .st-key-ds_sidebar_header .stButton > button,
    .st-key-ds_sidebar_collapsed > div:first-child .stButton > button {
        width: 38px !important;
        min-width: 38px !important;
        height: 38px !important;
        min-height: 38px !important;
        padding: 0 !important;
        border-radius: 14px !important;
        background: #F3F7FF !important;
        color: #7190FF !important;
        border: 1px solid #E0E8FF !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        transform: none !important;
    }
    .st-key-ds_sidebar_header .stButton > button:hover,
    .st-key-ds_sidebar_collapsed > div:first-child .stButton > button:hover {
        background: #EAF1FF !important;
        color: #3E6BFF !important;
        transform: none !important;
    }
    .st-key-ds_sidebar_collapsed .stButton > button {
        width: 44px !important;
        min-width: 44px !important;
        height: 44px !important;
        min-height: 44px !important;
        padding: 0 !important;
        border-radius: 16px !important;
        background: transparent !important;
        color: #6F80A0 !important;
        border: 1px solid transparent !important;
        box-shadow: none !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    .st-key-ds_sidebar_collapsed .stButton > button:hover {
        background: #EEF4FF !important;
        color: #4B7BFF !important;
        border-color: #D7E3FF !important;
        opacity: 1 !important;
    }

    /* outline 버튼 (취소 등) — ds-outline-btn 클래스 옆 */
    .ds-outline-btn button {
        background: #FFFFFF !important;
        color: #6B7894 !important;
        border: 1.5px solid #E4EAF5 !important;
        box-shadow: none !important;
    }
    .ds-outline-btn button:hover {
        background: #F7FAFF !important;
        color: #4B7BFF !important;
        border-color: #B8CAFF !important;
    }

    /* form submit */
    [data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(90deg, #4B7BFF 0%, #3DD9C5 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        font-size: 15px !important;
        box-shadow: 0 4px 16px rgba(75,123,255,0.28) !important;
        transition: opacity 0.2s !important;
    }
    [data-testid="stFormSubmitButton"] > button:hover { opacity: 0.88 !important; }

    /* ══════════════════════════════════════════
       폼 카드
    ══════════════════════════════════════════ */
    [data-testid="stForm"] {
        background: #FFFFFF !important;
        border-radius: 22px !important;
        border: 1px solid #E4EAF5 !important;
        box-shadow: 0 4px 32px rgba(75,123,255,0.10) !important;
        padding: 36px 32px !important;
    }

    /* ══════════════════════════════════════════
       입력 필드
    ══════════════════════════════════════════ */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        border-radius: 12px !important;
        border: 1.5px solid #E4EAF5 !important;
        padding: 11px 16px !important;
        background: #F9FBFF !important;
        font-size: 14px !important;
        color: #0F2447 !important;
        transition: border-color 0.15s, box-shadow 0.15s !important;
        height: 46px !important;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #4B7BFF !important;
        box-shadow: 0 0 0 3px rgba(75,123,255,0.13) !important;
        background: #FFFFFF !important;
    }
    .stTextInput > label,
    .stNumberInput > label,
    .stSelectbox > label,
    .stTextArea > label,
    .stMultiSelect > label {
        font-size: 13px !important;
        font-weight: 600 !important;
        color: #374151 !important;
        margin-bottom: 4px !important;
    }
    .stSelectbox > div > div {
        border-radius: 12px !important;
        border: 1.5px solid #E4EAF5 !important;
        background: #F9FBFF !important;
        font-size: 14px !important;
        min-height: 46px !important;
    }
    .stTextArea > div > div > textarea {
        border-radius: 12px !important;
        border: 1.5px solid #E4EAF5 !important;
        background: #F9FBFF !important;
        font-size: 14px !important;
    }
    .stTextArea > div > div > textarea:focus {
        border-color: #4B7BFF !important;
        box-shadow: 0 0 0 3px rgba(75,123,255,0.13) !important;
    }
    .stMultiSelect > div > div {
        border-radius: 12px !important;
        border: 1.5px solid #E4EAF5 !important;
        background: #F9FBFF !important;
    }

    /* ══════════════════════════════════════════
       탭 스타일
    ══════════════════════════════════════════ */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #EEF4FF;
        border-radius: 14px;
        padding: 5px;
        border-bottom: none !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px !important;
        font-weight: 500;
        font-size: 14px;
        color: #6B7894;
        border: none !important;
        background: transparent !important;
        padding: 9px 20px !important;
    }
    .stTabs [aria-selected="true"] {
        background: #FFFFFF !important;
        color: #4B7BFF !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 8px rgba(75,123,255,0.15) !important;
    }
    .stTabs [data-baseweb="tab-panel"] {
        padding: 20px 0 0 !important;
    }

    /* ══════════════════════════════════════════
       카드 공통 클래스
    ══════════════════════════════════════════ */
    .ds-card {
        background: #FFFFFF;
        border-radius: 20px;
        border: 1px solid #E4EAF5;
        box-shadow: 0 2px 16px rgba(15,36,71,0.07);
        padding: 24px;
        margin-bottom: 16px;
    }
    .ds-card-sm {
        background: #FFFFFF;
        border-radius: 16px;
        border: 1px solid #E4EAF5;
        box-shadow: 0 1px 8px rgba(15,36,71,0.05);
        padding: 18px 20px;
        margin-bottom: 12px;
    }
    .ds-card-gradient {
        background: linear-gradient(135deg, #EEF4FF 0%, #F3F0FF 100%);
        border-radius: 20px;
        border: 1px solid #D6E4FF;
        padding: 24px;
        margin-bottom: 16px;
    }
    .ds-card-title {
        font-size: 15px;
        font-weight: 700;
        color: #0F2447;
        margin-bottom: 14px;
    }

    /* ══════════════════════════════════════════
       severity 배지
    ══════════════════════════════════════════ */
    .ds-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.01em;
    }
    .ds-badge-normal   { background: #D1FAE5; color: #065F46; }
    .ds-badge-mild     { background: #FEF3C7; color: #92400E; }
    .ds-badge-moderate { background: #FED7AA; color: #9A3412; }
    .ds-badge-severe   { background: #FEE2E2; color: #991B1B; }
    .ds-badge-info     { background: #EEF4FF; color: #1D4ED8; }
    .ds-badge-success  { background: #D1FAE5; color: #065F46; }

    /* ══════════════════════════════════════════
       칩 (성분/카테고리/고민)
    ══════════════════════════════════════════ */
    .ds-chip {
        display: inline-block;
        padding: 5px 14px;
        background: #EEF4FF;
        border: 1px solid #BFCFFF;
        color: #3558CC;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 500;
        margin: 3px 2px;
        white-space: nowrap;
    }
    .ds-chip-excluded {
        background: #FEE2E2 !important;
        border-color: #FECACA !important;
        color: #991B1B !important;
    }
    .ds-chip-category {
        background: #F3F0FF !important;
        border-color: #DDD6FE !important;
        color: #5B21B6 !important;
    }
    .ds-chip-concern {
        background: #F3F0FF !important;
        border-color: #C4B5FD !important;
        color: #6D28D9 !important;
        font-weight: 600 !important;
    }
    .ds-chip-green {
        background: #D1FAE5 !important;
        border-color: #A7F3D0 !important;
        color: #065F46 !important;
    }

    /* ══════════════════════════════════════════
       페이지 제목
    ══════════════════════════════════════════ */
    .ds-page-title {
        font-size: 26px;
        font-weight: 800;
        color: #0F2447;
        margin: 0 0 6px;
        line-height: 1.3;
    }
    .ds-page-subtitle {
        font-size: 14px;
        color: #6B7894;
        margin: 0 0 28px;
        line-height: 1.6;
    }

    /* ══════════════════════════════════════════
       사이드바 active nav
    ══════════════════════════════════════════ */
    .ds-nav-active {
        background: linear-gradient(90deg, rgba(75,123,255,0.18) 0%, rgba(61,217,197,0.18) 100%);
        color: #4B7BFF !important;
        border-radius: 16px;
        padding: 13px 16px;
        font-size: 14px;
        font-weight: 800;
        min-height: 48px;
        margin: 5px 0;
        cursor: default;
        display: flex;
        align-items: center;
        gap: 10px;
        border: 1px solid rgba(123,156,255,0.48);
        box-shadow: inset 3px 0 0 #4B7BFF, 0 10px 22px rgba(75,123,255,0.13);
    }
    .ds-nav-section {
        font-size: 11px;
        font-weight: 700;
        color: #9BA9C0;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        padding: 14px 5px 9px;
    }
    .ds-collapsed-nav-active {
        width: 44px;
        height: 44px;
        border-radius: 16px;
        background: linear-gradient(135deg, #4B7BFF 0%, #3DD9C5 100%);
        color: #FFFFFF !important;
        box-shadow: 0 10px 24px rgba(75,123,255,0.24);
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 0 10px;
    }

    /* ══════════════════════════════════════════
       업로드 카드
    ══════════════════════════════════════════ */
    .ds-upload-zone {
        background: #FAFCFF;
        border-radius: 18px;
        border: 2px dashed #B8CAFF;
        padding: 28px 20px;
        text-align: center;
        transition: border-color 0.2s, background 0.2s;
    }
    .ds-upload-zone:hover {
        border-color: #4B7BFF;
        background: #EEF4FF;
    }
    /* 미리보기 이미지 최대 높이 제한 */
    .ds-preview-img img {
        max-height: 340px !important;
        object-fit: contain !important;
        border-radius: 16px !important;
        display: block !important;
        margin: 0 auto !important;
    }
    /* st.image 컨테이너에도 적용 */
    [data-testid="stImage"] img {
        max-height: 340px;
        object-fit: contain;
        border-radius: 14px;
    }

    /* ══════════════════════════════════════════
       단계 표시 (step indicator)
    ══════════════════════════════════════════ */
    .ds-step-wrap {
        display: flex;
        align-items: center;
        margin-bottom: 28px;
    }
    .ds-step-circle {
        width: 34px; height: 34px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center; justify-content: center;
        font-size: 14px; font-weight: 700;
        flex-shrink: 0;
    }
    .ds-step-circle-active  { background: #4B7BFF; color: #FFFFFF; }
    .ds-step-circle-done    { background: #3DD9C5; color: #FFFFFF; }
    .ds-step-circle-pending { background: #F0F4FF; color: #A0AABB; border: 2px solid #E4EAF5; }
    .ds-step-label-active   { color: #4B7BFF; font-weight: 700; font-size: 13px; }
    .ds-step-label-done     { color: #3DD9C5; font-weight: 600; font-size: 13px; }
    .ds-step-label-pending  { color: #A0AABB; font-size: 13px; }
    .ds-step-line           { flex: 1; height: 2px; background: #E4EAF5; margin: 0 8px; }
    .ds-step-line-done      { background: #3DD9C5; }

    /* ══════════════════════════════════════════
       리포트 카드
    ══════════════════════════════════════════ */
    .ds-score-card {
        background: linear-gradient(135deg, #EEF4FF 0%, #F0EDFF 100%);
        border-radius: 22px;
        border: 1px solid #D6E4FF;
        padding: 28px 32px;
        margin-bottom: 24px;
    }
    .ds-part-card {
        background: #FFFFFF;
        border-radius: 18px;
        border: 1px solid #E4EAF5;
        box-shadow: 0 2px 10px rgba(15,36,71,0.06);
        padding: 18px 14px;
        text-align: center;
        height: 100%;
        margin-bottom: 0;
    }
    .ds-rec-card {
        background: #FFFFFF;
        border-radius: 18px;
        border: 1px solid #E4EAF5;
        box-shadow: 0 2px 10px rgba(15,36,71,0.06);
        padding: 20px 22px;
        margin-bottom: 0;
    }
    .ds-rec-label {
        font-size: 12px;
        font-weight: 700;
        color: #A0AABB;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 10px;
    }
    .ds-rec-section-title {
        font-size: 16px;
        font-weight: 700;
        color: #0F2447;
        margin: 20px 0 14px;
    }

    /* ══════════════════════════════════════════
       프로필 아바타 / 헤더
    ══════════════════════════════════════════ */
    .ds-avatar {
        width: 64px; height: 64px;
        border-radius: 50%;
        background: linear-gradient(135deg, #4B7BFF 0%, #3DD9C5 100%);
        display: inline-flex;
        align-items: center; justify-content: center;
        font-size: 28px;
        color: #FFFFFF;
        flex-shrink: 0;
    }
    .ds-profile-header {
        background: #FFFFFF;
        border-radius: 22px;
        border: 1px solid #E4EAF5;
        box-shadow: 0 2px 16px rgba(15,36,71,0.07);
        padding: 28px 32px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 24px;
    }

    /* ══════════════════════════════════════════
       가이드 카드 (프로필 수정 우측)
    ══════════════════════════════════════════ */
    .ds-guide-card {
        background: linear-gradient(160deg, #EEF4FF 0%, #F0EDFF 100%);
        border-radius: 20px;
        border: 1px solid #D6E4FF;
        padding: 24px 20px;
        position: sticky;
        top: 24px;
    }
    .ds-guide-item {
        display: flex;
        gap: 12px;
        margin-bottom: 16px;
        align-items: flex-start;
    }
    .ds-guide-icon {
        font-size: 20px;
        flex-shrink: 0;
        line-height: 1.4;
    }

    /* ══════════════════════════════════════════
       info 행 (라벨:값)
    ══════════════════════════════════════════ */
    .ds-info-row {
        display: flex;
        padding: 8px 0;
        border-bottom: 1px solid #F5F7FF;
        font-size: 14px;
        align-items: center;
    }
    .ds-info-label { color: #6B7894; width: 40%; flex-shrink: 0; }
    .ds-info-value { color: #0F2447; font-weight: 600; }

    /* ══════════════════════════════════════════
       로그인 / 회원가입 레이아웃
    ══════════════════════════════════════════ */
    .ds-auth-wrapper {
        min-height: 100vh;
        display: flex;
        align-items: stretch;
        background: linear-gradient(135deg, #EEF4FF 0%, #F3F0FF 100%);
    }
    .ds-auth-brand {
        flex: 1;
        padding: 60px 48px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        position: relative;
        overflow: hidden;
    }
    .ds-auth-form-area {
        width: 520px;
        min-width: 380px;
        background: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 48px 56px;
        box-shadow: -4px 0 32px rgba(15,36,71,0.10);
    }

    /* 로그인 카드 내 pill 태그 */
    .ds-feature-pill {
        display: flex;
        align-items: center;
        gap: 10px;
        background: rgba(255,255,255,0.80);
        backdrop-filter: blur(4px);
        border-radius: 40px;
        padding: 10px 18px;
        margin-bottom: 10px;
        font-size: 13px;
        color: #0F2447;
        font-weight: 500;
        border: 1px solid rgba(75,123,255,0.15);
    }

    /* ══════════════════════════════════════════
       expander 스타일
    ══════════════════════════════════════════ */
    [data-testid="stExpander"] {
        border: 1px solid #E4EAF5 !important;
        border-radius: 16px !important;
        background: #FFFFFF !important;
        margin-bottom: 10px !important;
        box-shadow: 0 1px 6px rgba(15,36,71,0.05) !important;
    }
    [data-testid="stExpander"] > div:first-child {
        border-radius: 16px 16px 0 0 !important;
        background: #F9FBFF !important;
        padding: 14px 20px !important;
    }

    /* ══════════════════════════════════════════
       보안 인증 pill
    ══════════════════════════════════════════ */
    .ds-security-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #F0FDF4;
        border: 1px solid #86EFAC;
        border-radius: 20px;
        padding: 6px 14px;
        font-size: 12px;
        font-weight: 600;
        color: #15803D;
    }

    /* ══════════════════════════════════════════
       분석 가이드 카드
    ══════════════════════════════════════════ */
    .ds-guide-tip-card {
        background: #FFFFFF;
        border-radius: 18px;
        border: 1px solid #E4EAF5;
        box-shadow: 0 2px 10px rgba(15,36,71,0.06);
        padding: 20px 18px;
        text-align: center;
        height: 100%;
    }
    .ds-guide-tip-icon {
        font-size: 36px;
        margin-bottom: 10px;
        line-height: 1;
    }

    /* file_uploader 스타일 개선 */
    [data-testid="stFileUploader"] {
        border: none !important;
    }
    [data-testid="stFileUploader"] > div {
        border-radius: 16px !important;
        border: 2px dashed #B8CAFF !important;
        background: #F9FBFF !important;
        padding: 20px !important;
    }
    [data-testid="stFileUploaderDropzone"] {
        background: transparent !important;
    }

    /* spinner */
    .stSpinner > div {
        border-top-color: #4B7BFF !important;
    }

    /* ══════════════════════════════════════════
       분석 영역 카드 (카메라/업로드)
    ══════════════════════════════════════════ */
    .ds-upload-card {
        background: #FFFFFF;
        border-radius: 22px;
        border: 1px solid #E4EAF5;
        box-shadow: 0 2px 16px rgba(15,36,71,0.07);
        padding: 28px 24px;
        min-height: 400px;
    }

    </style>
    """, unsafe_allow_html=True)
