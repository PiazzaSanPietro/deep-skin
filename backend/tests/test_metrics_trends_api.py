"""
metrics trends API 통합 테스트: GET /analysis/metrics/trends

실제 DB 연결이 필요합니다. DB에 접속할 수 없으면 자동으로 skip됩니다.
AI 서버 없이 example_response.json을 직접 사용합니다.

확인 항목:
  1. trend API 정상 응답 (forehead moisture)
  2. 현재 사용자 데이터만 조회 (다른 사용자 세션은 trend=[] 반환)
  3. dummy metric 제외 (chin_moisture는 trend에 미포함)
  4. 해당 metric 없음 → trend=[]
  5. limit 동작 확인 (세션 3개 중 limit=2면 2개만)
  6. 인증 없음 → 401
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

import app.models.skin_json_record  # noqa: F401 — FK metadata

_EXAMPLE_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts/face_multivalue_inf/example_response.json"
)


# ── DB 픽스처 ──────────────────────────────────────────────────────────────────


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


# ── 테스트 픽스처 ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def fixtures(db_session):
    from app.models.analysis_session import AnalysisSession
    from app.models.uploaded_image import UploadedImage
    from app.models.user import User
    from app.services.multivalue_parser import parse_multivalue_response

    unique = int(time.time() * 1000) % 10_000_000
    payload = json.loads(_EXAMPLE_PATH.read_text())
    base_time = datetime(2026, 5, 1, 10, 0, 0)

    owner = User(
        email=f"trends_owner_{unique}@test.com",
        password_hash="hashed",
        name="TrendsOwner",
        is_active=True,
    )
    other = User(
        email=f"trends_other_{unique}@test.com",
        password_hash="hashed",
        name="TrendsOther",
        is_active=True,
    )
    db_session.add(owner)
    db_session.add(other)
    db_session.flush()

    # owner: 3 completed multivalue sessions at different times
    session_ids = []
    for i in range(3):
        sess = AnalysisSession(
            user_id=owner.id,
            session_name=f"trends_test_{i}_{unique}",
            input_type="image",
            status="completed",
            analyzed_at=base_time + timedelta(days=i * 7),
        )
        db_session.add(sess)
        db_session.flush()

        img = UploadedImage(
            session_id=sess.id,
            user_id=owner.id,
            original_filename="test.jpg",
            stored_filename=f"stored_{i}_{unique}.jpg",
            file_path=f"/tmp/trends_test_{i}_{unique}.jpg",
            content_type="image/jpeg",
            file_size=1024,
            width=100,
            height=100,
            upload_status="processed",
        )
        db_session.add(img)
        db_session.flush()

        parsed = parse_multivalue_response(
            payload,
            session_id=sess.id,
            user_id=owner.id,
            image_id=img.id,
        )
        db_session.add(parsed["raw_response"])
        db_session.add_all(parsed["part_results"])
        db_session.add_all(parsed["metric_values"])
        db_session.add_all(parsed["detections"])
        session_ids.append(sess.id)

    # other: 1 completed multivalue session
    other_sess = AnalysisSession(
        user_id=other.id,
        session_name=f"trends_other_test_{unique}",
        input_type="image",
        status="completed",
        analyzed_at=base_time,
    )
    db_session.add(other_sess)
    db_session.flush()

    other_img = UploadedImage(
        session_id=other_sess.id,
        user_id=other.id,
        original_filename="test.jpg",
        stored_filename=f"stored_other_{unique}.jpg",
        file_path=f"/tmp/trends_other_{unique}.jpg",
        content_type="image/jpeg",
        file_size=1024,
        width=100,
        height=100,
        upload_status="processed",
    )
    db_session.add(other_img)
    db_session.flush()

    other_parsed = parse_multivalue_response(
        payload,
        session_id=other_sess.id,
        user_id=other.id,
        image_id=other_img.id,
    )
    db_session.add(other_parsed["raw_response"])
    db_session.add_all(other_parsed["part_results"])
    db_session.add_all(other_parsed["metric_values"])
    db_session.add_all(other_parsed["detections"])

    db_session.commit()

    yield {
        "owner_id": owner.id,
        "other_id": other.id,
        "session_ids": session_ids,
        "other_session_id": other_sess.id,
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


@pytest.fixture(scope="module")
def client():
    from app.main import app

    return TestClient(app)


def _auth(user_id: int) -> dict:
    from app.core.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


# ── 테스트 케이스 ──────────────────────────────────────────────────────────────


def test_trends_success(client, fixtures):
    """forehead moisture 추이 정상 조회 — 3개 세션, time ASC 정렬."""
    resp = client.get(
        "/analysis/metrics/trends",
        params={
            "raw_part_name": "forehead",
            "metric_group": "moisture",
            "metric_name": "moisture",
        },
        headers=_auth(fixtures["owner_id"]),
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["raw_part_name"] == "forehead"
    assert body["metric_group"] == "moisture"
    assert body["metric_name"] == "moisture"
    assert body["display_part_name"] is not None
    assert body["metric_key"] is not None
    trend = body["trend"]
    assert len(trend) == 3
    # 시간 오름차순 확인
    dates = [t["analyzed_at"] for t in trend]
    assert dates == sorted(dates)
    for point in trend:
        assert "session_id" in point
        assert "analyzed_at" in point
        assert "value" in point


def test_trends_only_own_data(client, fixtures):
    """다른 사용자 데이터는 포함되지 않는다 — owner는 3개, other로 조회하면 1개."""
    resp = client.get(
        "/analysis/metrics/trends",
        params={
            "raw_part_name": "forehead",
            "metric_group": "moisture",
            "metric_name": "moisture",
        },
        headers=_auth(fixtures["other_id"]),
    )
    assert resp.status_code == 200
    trend = resp.json()["trend"]
    # other는 1개 세션만 가짐
    assert len(trend) == 1
    # session_id가 owner 세션이 아님을 확인
    other_session_ids = {trend[0]["session_id"]}
    owner_session_ids = set(fixtures["session_ids"])
    assert other_session_ids.isdisjoint(owner_session_ids)


def test_trends_dummy_excluded(client, fixtures):
    """chin_moisture(is_dummy=True)는 trend에 포함되지 않는다."""
    resp = client.get(
        "/analysis/metrics/trends",
        params={
            "raw_part_name": "chin",
            "metric_group": "moisture",
            "metric_name": "moisture",
        },
        headers=_auth(fixtures["owner_id"]),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["trend"] == []


def test_trends_no_data_returns_empty(client, fixtures):
    """존재하지 않는 metric 조합 → trend=[]."""
    resp = client.get(
        "/analysis/metrics/trends",
        params={
            "raw_part_name": "forehead",
            "metric_group": "nonexistent",
            "metric_name": "nonexistent",
        },
        headers=_auth(fixtures["owner_id"]),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["trend"] == []
    assert body["display_part_name"] is None
    assert body["metric_key"] is None


def test_trends_limit(client, fixtures):
    """limit=2이면 최근 2개만 반환한다."""
    resp = client.get(
        "/analysis/metrics/trends",
        params={
            "raw_part_name": "forehead",
            "metric_group": "moisture",
            "metric_name": "moisture",
            "limit": 2,
        },
        headers=_auth(fixtures["owner_id"]),
    )
    assert resp.status_code == 200
    trend = resp.json()["trend"]
    assert len(trend) == 2
    # 최근 2개(세션 2, 3) — time ASC 정렬이므로 마지막이 가장 최신
    session_ids_in_trend = {p["session_id"] for p in trend}
    expected_latest_two = set(fixtures["session_ids"][-2:])
    assert session_ids_in_trend == expected_latest_two


def test_trends_unauthorized(client, fixtures):
    """Authorization 헤더 없이 호출 → 401."""
    resp = client.get(
        "/analysis/metrics/trends",
        params={
            "raw_part_name": "forehead",
            "metric_group": "moisture",
            "metric_name": "moisture",
        },
    )
    assert resp.status_code == 401
