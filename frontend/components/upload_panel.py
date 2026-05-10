"""
업로드 패널: 실제 파일 선택 버튼이 항상 보이고, 미리보기는 최대 340px로 제한.
"""
import base64
import io
import os

import streamlit as st


# ── 아이콘 헬퍼 ──────────────────────────────────────────────────────────────

def _b64_src(rel: str) -> str:
    path = os.path.join("assets", "icons", rel)
    try:
        with open(path, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    except Exception:
        return ""


# ── 메인 렌더 ────────────────────────────────────────────────────────────────

def render() -> dict | None:
    """
    카메라 촬영 / 이미지 업로드 탭을 렌더링한다.
    Returns {"bytes": bytes, "name": str} 또는 None.
    """
    col_camera, col_upload = st.columns([1, 1], gap="large")

    result = None

    with col_camera:
        cam = _render_camera_card()
        if cam:
            result = cam

    with col_upload:
        up = _render_upload_card()
        if up:
            result = up

    return result


# ── 카메라 카드 ───────────────────────────────────────────────────────────────

def _render_camera_card() -> dict | None:
    face_src = _b64_src("analysis/face_guide_large.png")
    face_img = (
        f'<img src="{face_src}" width="160" '
        f'style="opacity:0.9;object-fit:contain;margin-bottom:8px;">'
        if face_src else '<div style="font-size:64px;">🧖</div>'
    )
    camera_src = _b64_src("analysis/camera.png")
    camera_img = (
        f'<img src="{camera_src}" width="28" style="vertical-align:middle;margin-right:8px;">'
        if camera_src else "📷"
    )

    st.markdown(f"""
    <div class="ds-upload-card" style="text-align:center;">
        <div style="font-size:15px;font-weight:700;color:#0F2447;margin-bottom:16px;
                    display:flex;align-items:center;justify-content:center;">
            {camera_img} 카메라 촬영
        </div>
        <div style="margin:8px 0 12px;">{face_img}</div>
        <div style="font-size:13px;color:#6B7894;line-height:1.6;margin-bottom:16px;">
            정면을 바라보고 촬영하세요.<br>밝은 환경에서 촬영하면 더 정확합니다.
        </div>
    </div>
    """, unsafe_allow_html=True)

    camera_image = st.camera_input("카메라로 촬영하기", label_visibility="collapsed")
    if camera_image:
        return {"bytes": camera_image.getvalue(), "name": "camera_capture.jpg"}
    return None


# ── 업로드 카드 ───────────────────────────────────────────────────────────────

def _render_upload_card() -> dict | None:
    cloud_src = _b64_src("analysis/upload_cloud.png")
    cloud_img = (
        f'<img src="{cloud_src}" width="56" style="object-fit:contain;margin-bottom:4px;">'
        if cloud_src else '<div style="font-size:44px;">☁️</div>'
    )
    upload_src = _b64_src("analysis/upload_cloud.png")
    upload_hdr = (
        f'<img src="{upload_src}" width="24" style="vertical-align:middle;margin-right:8px;">'
        if upload_src else "📤"
    )

    st.markdown(f"""
    <div class="ds-upload-card">
        <div style="font-size:15px;font-weight:700;color:#0F2447;margin-bottom:16px;
                    display:flex;align-items:center;">
            {upload_hdr} 이미지 업로드
        </div>
        <div style="text-align:center;padding:8px 0 4px;">
            {cloud_img}
            <div style="font-size:14px;font-weight:600;color:#4B7BFF;margin-bottom:4px;">
                이미지를 업로드해주세요
            </div>
            <div style="font-size:12px;color:#A0AABB;margin-bottom:16px;line-height:1.6;">
                아래 파일 선택 버튼을 눌러 JPG/PNG 이미지를 업로드하세요.<br>
                JPG, JPEG, PNG 지원 / 최대 10MB
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "파일 선택 (JPG, PNG, 최대 10MB)",
        type=["jpg", "jpeg", "png"],
    )

    if not uploaded_file:
        return None

    # 미리보기 — max-height: 340px
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(uploaded_file.getvalue()))
        st.markdown(
            '<div style="border-radius:16px;overflow:hidden;border:1px solid #E4EAF5;'
            'margin-top:12px;max-height:340px;text-align:center;">',
            unsafe_allow_html=True,
        )
        # use_container_width=False, width 고정으로 크기 제한
        w, h = img.size
        max_h = 320
        if h > max_h:
            scale = max_h / h
            display_w = int(w * scale)
        else:
            display_w = min(w, 600)
        st.image(img, caption="업로드된 이미지 미리보기", width=display_w)
        st.markdown("</div>", unsafe_allow_html=True)
    except Exception:
        st.success("파일이 선택되었습니다: " + uploaded_file.name, icon="✅")

    return {"bytes": uploaded_file.getvalue(), "name": uploaded_file.name}


# ── 가이드 카드 ───────────────────────────────────────────────────────────────

def render_guide_cards():
    """촬영 가이드 카드 3개."""
    guides = [
        ("analysis/sun.png",        "☀️", "밝은 조명에서 촬영하세요",
         "자연광이나 밝은 실내 조명 아래서 촬영해주세요."),
        ("analysis/face_guide.png", "😐", "정면 얼굴 사진을 업로드하세요",
         "카메라를 정면으로 바라보며 촬영해주세요."),
        ("analysis/no_makeup.png",  "🚫", "메이크업이 옅은 상태를 권장합니다",
         "베이스 메이크업 없는 맨얼굴 사진이 가장 정확합니다."),
    ]
    cols = st.columns(3, gap="medium")
    for col, (icon_rel, emoji, title, desc) in zip(cols, guides):
        with col:
            icon_src = _b64_src(icon_rel)
            icon_html = (
                f'<img src="{icon_src}" width="44" '
                f'style="object-fit:contain;margin-bottom:10px;">'
                if icon_src else f'<div style="font-size:36px;margin-bottom:10px;">{emoji}</div>'
            )
            st.markdown(f"""
            <div class="ds-guide-tip-card">
                <div class="ds-guide-tip-icon">{icon_html}</div>
                <div style="font-size:14px;font-weight:700;color:#0F2447;margin-bottom:6px;">{title}</div>
                <div style="font-size:12px;color:#6B7894;line-height:1.6;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
