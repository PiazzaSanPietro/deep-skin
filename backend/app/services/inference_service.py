import logging
from pathlib import Path

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.image_upload import InferenceResult, PartResult

logger = logging.getLogger(__name__)


def run_inference(
    image_path: str,
    session_id: int | None = None,
    user_id: int | None = None,
    image_id: int | None = None,
) -> InferenceResult:
    if settings.AI_INFERENCE_MODE == "remote":
        return _run_remote(image_path, session_id, user_id, image_id)
    return _run_mock()


# ── Mock ─────────────────────────────────────────────────────────────────────

def _run_mock() -> InferenceResult:
    return InferenceResult(
        model_name="mock_skin_model",
        model_version="0.0.1",
        parts=[
            PartResult(
                raw_part_name="left_cheek",
                display_part_name="볼",
                metric_name="pore",
                metric_display_name="모공",
                issue_type="pore",
                grade_value=2,
                severity="moderate",
                confidence_score=0.82,
            ),
            PartResult(
                raw_part_name="right_cheek",
                display_part_name="볼",
                metric_name="pore",
                metric_display_name="모공",
                issue_type="pore",
                grade_value=1,
                severity="mild",
                confidence_score=0.79,
            ),
            PartResult(
                raw_part_name="forehead",
                display_part_name="이마",
                metric_name="wrinkle",
                metric_display_name="주름",
                issue_type="wrinkle",
                grade_value=0,
                severity="normal",
                confidence_score=0.91,
            ),
            PartResult(
                raw_part_name="glabella",
                display_part_name="미간",
                metric_name="wrinkle",
                metric_display_name="주름",
                issue_type="wrinkle",
                grade_value=2,
                severity="moderate",
                confidence_score=0.84,
            ),
            PartResult(
                raw_part_name="left_eye",
                display_part_name="눈가",
                metric_name="wrinkle",
                metric_display_name="주름",
                issue_type="wrinkle",
                grade_value=3,
                severity="severe",
                confidence_score=0.88,
            ),
            PartResult(
                raw_part_name="lips",
                display_part_name="입술",
                metric_name="dryness",
                metric_display_name="건조",
                issue_type="dryness",
                grade_value=1,
                severity="mild",
                confidence_score=0.77,
            ),
            PartResult(
                raw_part_name="chin",
                display_part_name="턱",
                metric_name="sagging",
                metric_display_name="처짐",
                issue_type="sagging",
                grade_value=2,
                severity="moderate",
                confidence_score=0.74,
            ),
        ],
    )


# ── Remote ───────────────────────────────────────────────────────────────────

def _run_remote(
    image_path: str,
    session_id: int | None,
    user_id: int | None,
    image_id: int | None,
) -> InferenceResult:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")

    form_data: dict[str, str] = {}
    if session_id is not None:
        form_data["session_id"] = str(session_id)
    if user_id is not None:
        form_data["user_id"] = str(user_id)
    if image_id is not None:
        form_data["image_id"] = str(image_id)

    file_bytes = path.read_bytes()

    logger.info(
        "AI inference 요청 | url=%s image=%s session_id=%s",
        settings.AI_INFERENCE_URL, image_path, session_id,
    )

    try:
        with httpx.Client(timeout=settings.AI_INFERENCE_TIMEOUT_SECONDS) as client:
            response = client.post(
                settings.AI_INFERENCE_URL,
                files={"file": (path.name, file_bytes, "image/jpeg")},
                data=form_data,
            )
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise RuntimeError(f"AI 서버 응답 시간 초과: {exc}") from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"AI 서버 연결 실패: {exc}") from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"AI 서버 오류 (status={exc.response.status_code}): {exc.response.text}"
        ) from exc

    try:
        payload = response.json()
    except Exception as exc:
        raise RuntimeError(f"AI 서버 응답 JSON 파싱 실패: {exc}") from exc

    logger.info(
        "AI inference 응답 | model=%s parts=%d개",
        payload.get("model_name"), len(payload.get("parts", [])),
    )

    return _validate_response(payload)


def _validate_response(data: dict) -> InferenceResult:
    try:
        return InferenceResult(**data)
    except (ValidationError, TypeError) as exc:
        raise RuntimeError(f"AI 서버 응답 형식이 올바르지 않습니다: {exc}") from exc
