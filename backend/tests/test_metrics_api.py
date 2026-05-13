"""
metrics API 통합 테스트: GET /analysis/sessions/{session_id}/metrics

실제 DB 연결이 필요합니다. DB에 접속할 수 없으면 자동으로 skip됩니다.
AI 서버 없이 example_response.json을 직접 사용합니다.

확인 항목:
  - 200 + parts 비어있지 않음 (multivalue 세션)
  - chin_moisture dummy 값 포함
  - flat 세션 → 200 + parts=[]
  - 다른 사용자 세션 → 404
  - 존재하지 않는 session_id → 404
  - 인증 없음 → 401
"""

import json
import time
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

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


# ── 테스트 픽스처: 소유자 / 다른 사용자 / 세션 2개 / metric 데이터 ─────────────


@pytest.fixture(scope="module")
def fixtures(db_session):
    from app.models.analysis_session import AnalysisSession
    from app.models.uploaded_image import UploadedImage
    from app.models.user import User
    from app.services.multivalue_parser import parse_multivalue_response

    unique = int(time.time() * 1000) % 10_000_000

    owner = User(
        email=f"metrics_api_owner_{unique}@test.com",
        password_hash="hashed",
        name="MetricsOwner",
        is_active=True,
    )
    other = User(
        email=f"metrics_api_other_{unique}@test.com",
        password_hash="hashed",
        name="MetricsOther",
        is_active=True,
    )
    db_session.add(owner)
    db_session.add(other)
    db_session.flush()

    mv_session = AnalysisSession(
        user_id=owner.id,
        session_name="metrics_api_multivalue_test",
        input_type="image",
        status="completed",
    )
    flat_session = AnalysisSession(
        user_id=owner.id,
        session_name="metrics_api_flat_test",
        input_type="image",
        status="completed",
    )
    db_session.add(mv_session)
    db_session.add(flat_session)
    db_session.flush()

    image = UploadedImage(
        session_id=mv_session.id,
        user_id=owner.id,
        original_filename="test.jpg",
        stored_filename="test_stored.jpg",
        file_path="/tmp/test_metrics_api.jpg",
        content_type="image/jpeg",
        file_size=1024,
        width=100,
        height=100,
        upload_status="processed",
    )
    db_session.add(image)
    db_session.flush()

    payload = json.loads(_EXAMPLE_PATH.read_text())
    parsed = parse_multivalue_response(
        payload,
        session_id=mv_session.id,
        user_id=owner.id,
        image_id=image.id,
    )
    db_session.add(parsed["raw_response"])
    db_session.add_all(parsed["part_results"])
    db_session.add_all(parsed["metric_values"])
    db_session.add_all(parsed["detections"])
    db_session.commit()

    yield {
        "owner_id": owner.id,
        "other_id": other.id,
        "mv_session_id": mv_session.id,
        "flat_session_id": flat_session.id,
    }

    cleanup_owner_id = owner.id
    cleanup_other_id = other.id
    db_session.expunge_all()
    db_session.execute(
        sa.text("DELETE FROM users WHERE id = :uid"), {"uid": cleanup_owner_id}
    )
    db_session.execute(
        sa.text("DELETE FROM users WHERE id = :uid"), {"uid": cleanup_other_id}
    )
    db_session.commit()


# ── TestClient / 인증 헬퍼 ─────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    from app.main import app

    return TestClient(app)


def _auth(user_id: int) -> dict:
    from app.core.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


# ── 테스트 케이스 ─────────────────────────────────────────────────────────────


def test_metrics_success(client, fixtures):
    """multivalue 세션의 metrics 조회 성공 — 200, parts 비어있지 않음."""
    session_id = fixtures["mv_session_id"]

    resp = client.get(
        f"/analysis/sessions/{session_id}/metrics",
        headers=_auth(fixtures["owner_id"]),
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["session_id"] == session_id
    assert len(body["parts"]) > 0

    part_names = {p["raw_part_name"] for p in body["parts"]}
    assert "forehead" in part_names

    first_metric = body["parts"][0]["metrics"][0]
    for field in (
        "metric_group",
        "metric_name",
        "metric_key",
        "value",
        "value_type",
        "is_dummy",
        "source",
    ):
        assert field in first_metric, f"필드 '{field}' 누락"


def test_metrics_chin_dummy(client, fixtures):
    """chin_moisture는 is_dummy=True, dummy_reason='label_not_trained'으로 반환된다."""
    session_id = fixtures["mv_session_id"]

    resp = client.get(
        f"/analysis/sessions/{session_id}/metrics",
        headers=_auth(fixtures["owner_id"]),
    )
    assert resp.status_code == 200

    chin_list = [
        m
        for p in resp.json()["parts"]
        for m in p["metrics"]
        if m["metric_key"] == "chin_moisture"
    ]
    assert len(chin_list) == 1
    chin = chin_list[0]
    assert chin["is_dummy"] is True
    assert chin["dummy_reason"] == "label_not_trained"
    assert chin["source"] == "dummy_fallback"


def test_metrics_flat_session_empty(client, fixtures):
    """flat 세션(metric 데이터 없음) 조회 → 200, parts=[]."""
    session_id = fixtures["flat_session_id"]

    resp = client.get(
        f"/analysis/sessions/{session_id}/metrics",
        headers=_auth(fixtures["owner_id"]),
    )

    assert resp.status_code == 200
    assert resp.json()["parts"] == []


def test_metrics_other_user_forbidden(client, fixtures):
    """다른 사용자가 소유자의 세션을 조회하면 404를 반환한다."""
    session_id = fixtures["mv_session_id"]

    resp = client.get(
        f"/analysis/sessions/{session_id}/metrics",
        headers=_auth(fixtures["other_id"]),
    )

    assert resp.status_code == 404


def test_metrics_session_not_found(client, fixtures):
    """존재하지 않는 session_id 조회 → 404."""
    resp = client.get(
        "/analysis/sessions/99999999/metrics",
        headers=_auth(fixtures["owner_id"]),
    )

    assert resp.status_code == 404


def test_metrics_unauthorized(client, fixtures):
    """Authorization 헤더 없이 호출 → 401."""
    session_id = fixtures["mv_session_id"]

    resp = client.get(f"/analysis/sessions/{session_id}/metrics")

    assert resp.status_code == 401
