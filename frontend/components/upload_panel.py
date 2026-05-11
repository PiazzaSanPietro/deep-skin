"""
Analysis upload panel.

Renders the camera and file upload inputs while keeping the visual shell close to
the Deep Skin dashboard design.
"""
import io

import streamlit as st


def render() -> dict | None:
    """Render camera and upload cards. Return selected image data."""
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


def _render_camera_card() -> dict | None:
    with st.container(key="ds_camera_card"):
        st.markdown(
            """
            <div class="ds-camera-card-header">
                <div class="ds-analysis-card-title">📷 카메라 촬영</div>
                <div class="ds-camera-card-hint">
                    얼굴이 화면 중앙에 오도록 정면을 바라봐주세요.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        camera_image = st.camera_input("카메라로 촬영하기", label_visibility="collapsed")
        if camera_image:
            st.markdown(
                """
                <style>
                .st-key-ds_camera_card [data-testid="stCameraInputButton"]::after {
                    content: "↻" !important;
                    font-size: 25px !important;
                    font-weight: 900 !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
    if camera_image:
        return {"bytes": camera_image.getvalue(), "name": "camera_capture.jpg"}
    return None


def _render_upload_card() -> dict | None:
    with st.container(key="ds_upload_card"):
        st.markdown(
            """
            <div class="ds-analysis-card-title">☁ 이미지 업로드</div>
            <div class="ds-upload-dropzone">
                <div class="ds-upload-cloud">☁</div>
                <div class="ds-upload-title">이미지를 업로드해주세요.</div>
                <div class="ds-upload-desc">JPG, PNG 파일 지원</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        uploaded_file = st.file_uploader(
            "이미지 파일 선택",
            type=["jpg", "jpeg", "png"],
            label_visibility="collapsed",
        )

    if not uploaded_file:
        return None

    try:
        from PIL import Image

        img = Image.open(io.BytesIO(uploaded_file.getvalue()))
        st.markdown('<div class="ds-preview-frame">', unsafe_allow_html=True)
        w, h = img.size
        max_h = 320
        display_w = int(w * (max_h / h)) if h > max_h else min(w, 620)
        st.image(img, caption="업로드된 이미지 미리보기", width=display_w)
        st.markdown("</div>", unsafe_allow_html=True)
    except Exception:
        st.success("파일이 선택되었습니다: " + uploaded_file.name, icon="✅")

    return {"bytes": uploaded_file.getvalue(), "name": uploaded_file.name}


def render_guide_cards():
    guides = [
        ("🧑‍🦱", "정면 얼굴 사진을 업로드하세요", "얼굴 전체가 보이도록 정면을 바라보고 촬영해주세요."),
        ("☀️", "밝은 조명에서 촬영하세요", "자연광 또는 밝은 실내 조명에서 촬영하면 더 정확해요."),
        ("✨", "메이크업이 옅은 상태를 권장합니다", "피부 본연의 상태를 분석하기 위해 메이크업을 최소화해주세요."),
    ]
    cols = st.columns(3, gap="medium")
    for col, (icon, title, desc) in zip(cols, guides):
        with col:
            st.markdown(
                f"""
                <div class="ds-analysis-guide-card">
                    <div class="ds-analysis-guide-icon">{icon}</div>
                    <div>
                        <div class="ds-analysis-guide-title">{title}</div>
                        <div class="ds-analysis-guide-desc">{desc}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
