"""
MultiValue 저장 통합 테스트.

실제 DB 연결이 필요합니다. DB에 접속할 수 없으면 자동으로 skip됩니다.
AI 서버 없이 example_response.json을 직접 사용합니다.

확인 항목:
  - ai_raw_responses     1 row
  - skin_part_results    약 11 row
  - skin_metric_values   약 80 row
  - skin_part_detections 최대 8 row
"""

import json
import time
from pathlib import Path

import pytest
import sqlalchemy as sa

# SkinPartResult.json_record_id → skin_json_records FK를 메타데이터에 등록
import app.models.skin_json_record  # noqa: F401

_EXAMPLE_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts/face_multivalue_inf/example_response.json"
)

# ── DB fixture ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def db_engine():
    try:
        from app.core.config import settings
        engine = sa.create_engine(settings.DATABASE_URL)
        with engine.connect():
            pass
        yield engine
        engine.dispose()
    except Exception as exc:
        pytest.skip(f"DB 연결 불가 — 통합 테스트 skip: {exc}")


@pytest.fixture(scope="module")
def db_session(db_engine):
    from app.db.database import SessionLocal
    session = SessionLocal()
    yield session
    session.close()


# ── 테스트 픽스처: user / analysis_session / uploaded_image ───────────────────

@pytest.fixture(scope="module")
def fixtures(db_session):
    from app.models.analysis_session import AnalysisSession
    from app.models.uploaded_image import UploadedImage
    from app.models.user import User

    unique = int(time.time() * 1000) % 10_000_000
    user = User(
        email=f"multivalue_storage_test_{unique}@test.com",
        password_hash="hashed",
        name="StorageTest",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    session = AnalysisSession(
        user_id=user.id,
        session_name="multivalue_storage_test",
        input_type="image",
        status="processing",
    )
    db_session.add(session)
    db_session.flush()

    image = UploadedImage(
        session_id=session.id,
        user_id=user.id,
        original_filename="test.jpg",
        stored_filename="test_stored.jpg",
        file_path="/tmp/test_stored.jpg",
        content_type="image/jpeg",
        file_size=1024,
        width=100,
        height=100,
        upload_status="processing",
    )
    db_session.add(image)
    db_session.flush()
    db_session.commit()

    yield {
        "user_id": user.id,
        "session_id": session.id,
        "image_id": image.id,
    }

    # 정리: user 삭제 → FK CASCADE로 모든 하위 레코드 자동 삭제
    cleanup_user_id = user.id  # expunge 전에 id 미리 저장
    db_session.expunge_all()
    db_session.execute(
        sa.text("DELETE FROM users WHERE id = :uid"),
        {"uid": cleanup_user_id},
    )
    db_session.commit()


# ── 저장 헬퍼 ─────────────────────────────────────────────────────────────────

def _save_parsed(db_session, parsed: dict) -> None:
    """parse_multivalue_response() 결과를 DB에 저장한다."""
    from app.models.ai_raw_response import AiRawResponse
    from app.models.skin_metric_value import SkinMetricValue
    from app.models.skin_part_detection import SkinPartDetection
    from app.models.skin_part_result import SkinPartResult

    session_id = parsed["raw_response"].session_id

    db_session.query(SkinPartResult).filter(
        SkinPartResult.session_id == session_id,
        SkinPartResult.image_id.is_not(None),
    ).delete(synchronize_session=False)
    db_session.query(AiRawResponse).filter(
        AiRawResponse.session_id == session_id,
    ).delete(synchronize_session=False)
    db_session.query(SkinMetricValue).filter(
        SkinMetricValue.session_id == session_id,
    ).delete(synchronize_session=False)
    db_session.query(SkinPartDetection).filter(
        SkinPartDetection.session_id == session_id,
    ).delete(synchronize_session=False)

    db_session.add(parsed["raw_response"])
    db_session.add_all(parsed["part_results"])
    db_session.add_all(parsed["metric_values"])
    db_session.add_all(parsed["detections"])
    db_session.commit()


# ── 테스트 케이스 ─────────────────────────────────────────────────────────────

def test_multivalue_storage_row_counts(db_session, fixtures):
    """parse → DB 저장 후 각 테이블 row 수가 예상 범위에 있는지 확인한다."""
    from app.models.ai_raw_response import AiRawResponse
    from app.models.skin_metric_value import SkinMetricValue
    from app.models.skin_part_detection import SkinPartDetection
    from app.models.skin_part_result import SkinPartResult
    from app.services.multivalue_parser import parse_multivalue_response

    session_id = fixtures["session_id"]
    user_id = fixtures["user_id"]
    image_id = fixtures["image_id"]

    payload = json.loads(_EXAMPLE_PATH.read_text())
    parsed = parse_multivalue_response(payload, session_id=session_id, user_id=user_id, image_id=image_id)
    _save_parsed(db_session, parsed)

    raw_count = db_session.query(AiRawResponse).filter(AiRawResponse.session_id == session_id).count()
    part_count = db_session.query(SkinPartResult).filter(SkinPartResult.session_id == session_id).count()
    metric_count = db_session.query(SkinMetricValue).filter(SkinMetricValue.session_id == session_id).count()
    det_count = db_session.query(SkinPartDetection).filter(SkinPartDetection.session_id == session_id).count()

    assert raw_count == 1, f"ai_raw_responses: 기대 1, 실제 {raw_count}"
    assert part_count == 11, f"skin_part_results: 기대 11, 실제 {part_count}"
    assert 70 <= metric_count <= 90, f"skin_metric_values: 기대 70~90, 실제 {metric_count}"
    assert 1 <= det_count <= 8, f"skin_part_detections: 기대 1~8, 실제 {det_count}"


def test_multivalue_storage_raw_json_preserved(db_session, fixtures):
    """ai_raw_responses.raw_json에 원본 payload가 통째로 저장되는지 확인한다."""
    from app.models.ai_raw_response import AiRawResponse

    session_id = fixtures["session_id"]

    raw = db_session.query(AiRawResponse).filter(AiRawResponse.session_id == session_id).first()
    assert raw is not None
    assert raw.server_type == "multivalue"
    assert isinstance(raw.raw_json, dict)
    assert "parts" in raw.raw_json
    assert "detected_parts" in raw.raw_json
    assert raw.model_name == "skin_dinov3_multivalue"


def test_multivalue_storage_chin_moisture_dummy(db_session, fixtures):
    """chin_moisture는 is_dummy=True, dummy_reason='label_not_trained'으로 저장되는지 확인한다."""
    from app.models.skin_metric_value import SkinMetricValue

    session_id = fixtures["session_id"]

    chin_moisture = (
        db_session.query(SkinMetricValue)
        .filter(
            SkinMetricValue.session_id == session_id,
            SkinMetricValue.metric_key == "chin_moisture",
        )
        .first()
    )
    assert chin_moisture is not None
    assert chin_moisture.is_dummy is True
    assert chin_moisture.dummy_reason == "label_not_trained"
    assert chin_moisture.source == "dummy_fallback"


def test_multivalue_storage_yolo_detections(db_session, fixtures):
    """YOLO로 검출된 파트는 bbox_source='yolo'로 저장되는지 확인한다."""
    from app.models.skin_part_detection import SkinPartDetection

    session_id = fixtures["session_id"]

    yolo_dets = (
        db_session.query(SkinPartDetection)
        .filter(
            SkinPartDetection.session_id == session_id,
            SkinPartDetection.bbox_source == "yolo",
        )
        .all()
    )
    assert len(yolo_dets) > 0

    left_eye = next((d for d in yolo_dets if d.raw_part_name == "left_eye"), None)
    assert left_eye is not None
    assert left_eye.detection_confidence is not None
    assert left_eye.class_name == "l_eye"


def test_multivalue_storage_severity_correctness(db_session, fixtures):
    """forehead_pigmentation grade=2 → severity='moderate'로 저장되는지 확인한다."""
    from app.models.skin_part_result import SkinPartResult

    session_id = fixtures["session_id"]

    pigmentation = (
        db_session.query(SkinPartResult)
        .filter(
            SkinPartResult.session_id == session_id,
            SkinPartResult.raw_part_name == "forehead",
            SkinPartResult.metric_name == "pigmentation",
        )
        .first()
    )
    assert pigmentation is not None
    assert pigmentation.grade_value == 2
    assert pigmentation.severity == "moderate"


def test_multivalue_storage_reupload_idempotent(db_session, fixtures):
    """같은 session에 두 번 저장해도 ai_raw_responses가 1개만 남는지 확인한다."""
    from app.models.ai_raw_response import AiRawResponse
    from app.services.multivalue_parser import parse_multivalue_response

    session_id = fixtures["session_id"]
    user_id = fixtures["user_id"]
    image_id = fixtures["image_id"]

    payload = json.loads(_EXAMPLE_PATH.read_text())
    parsed = parse_multivalue_response(payload, session_id=session_id, user_id=user_id, image_id=image_id)
    _save_parsed(db_session, parsed)

    raw_count = db_session.query(AiRawResponse).filter(AiRawResponse.session_id == session_id).count()
    assert raw_count == 1, f"재저장 후 ai_raw_responses: 기대 1, 실제 {raw_count}"
