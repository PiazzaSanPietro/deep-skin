"""
seed_metric_boost_rules.py 스크립트 테스트.

두 가지 방식으로 검증한다:
  A) SEEDS 상수 직접 검증 (DB 불필요 — 항상 실행)
  B) 실제 DB 통합 테스트 (DB 연결 불가 시 자동 skip)

확인 항목:
  1.  seed 총 11개 정의
  2.  재실행 시 중복 생성 안 됨
  3.  moisture threshold_max=35
  4.  pore_count threshold_min=700
  5.  wrinkle Ra threshold_min=25
  6.  elasticity R2 threshold_max=0.50
  7.  elasticity R7 threshold_max=0.35
  8.  wrinkle Rmax/Rt/Rz/Rq seed 존재
  9.  pigmentation_count priority=60
 10.  acne_count threshold_min=30
 11.  zinc_pca는 add_ingredients에 없음
 12.  Rz metric_name이 "Rz" 정확히 일치
 13.  is_active=True 전체 확인
"""
import pytest

from scripts.seed_metric_boost_rules import SEEDS, _fingerprint


# ── A. SEEDS 상수 직접 검증 (DB 불필요) ──────────────────────────────────────

def _seed(group: str, name: str) -> dict:
    for s in SEEDS:
        if s["metric_group"] == group and s["metric_name"] == name:
            return s
    raise KeyError(f"seed 없음: {group}/{name}")


def test_seed_total_count():
    assert len(SEEDS) == 11


def test_moisture_seed():
    s = _seed("moisture", "moisture")
    assert s["threshold_max"] == pytest.approx(35.0)
    assert s["threshold_min"] is None
    assert s["direction"] == "low_is_bad"
    assert "ceramide" in (s["add_ingredients"] or [])
    assert "panthenol" in (s["add_ingredients"] or [])
    assert s["is_active"] is True


def test_pore_count_seed():
    s = _seed("pore", "pore_count")
    assert s["threshold_min"] == pytest.approx(700.0)
    assert s["threshold_max"] is None
    assert s["direction"] == "high_is_bad"
    assert "bha" in (s["boost_ingredients"] or [])
    assert s["is_active"] is True


def test_wrinkle_Ra_seed():
    s = _seed("wrinkle", "Ra")
    assert s["threshold_min"] == pytest.approx(25.0)
    assert s["direction"] == "high_is_bad"
    assert "peptide" in (s["boost_ingredients"] or [])
    assert "adenosine" in (s["boost_ingredients"] or [])


def test_elasticity_R2_seed():
    s = _seed("elasticity", "R2")
    assert s["threshold_max"] == pytest.approx(0.50)
    assert s["threshold_min"] is None
    assert s["direction"] == "low_is_bad"
    assert "peptide" in (s["add_ingredients"] or [])
    assert "adenosine" in (s["add_ingredients"] or [])


def test_elasticity_R7_seed():
    s = _seed("elasticity", "R7")
    assert s["threshold_max"] == pytest.approx(0.35)
    assert s["direction"] == "low_is_bad"
    assert "peptide" in (s["add_ingredients"] or [])


def test_wrinkle_roughness_seeds_exist():
    for name in ("Rmax", "Rt", "Rz", "Rq"):
        s = _seed("wrinkle", name)
        assert s["direction"] == "high_is_bad"
        assert s["is_active"] is True


def test_pigmentation_count_seed():
    s = _seed("pigmentation", "pigmentation_count")
    assert s["priority"] == 60
    assert s["threshold_min"] == pytest.approx(100.0)
    assert "niacinamide" in (s["add_ingredients"] or [])


def test_acne_count_seed():
    s = _seed("acne", "acne_count")
    assert s["threshold_min"] == pytest.approx(30.0)
    assert "bha" in (s["add_ingredients"] or [])
    assert "panthenol" in (s["add_ingredients"] or [])


def test_zinc_pca_not_in_any_add_ingredients():
    for s in SEEDS:
        add_ings = s.get("add_ingredients") or []
        assert "zinc_pca" not in add_ings, (
            f"zinc_pca가 {s['metric_group']}/{s['metric_name']}의 add_ingredients에 포함됨"
        )


def test_Rz_metric_name_exact():
    s = _seed("wrinkle", "Rz")
    assert s["metric_name"] == "Rz"


def test_all_seeds_active():
    for s in SEEDS:
        assert s["is_active"] is True, f"{s['metric_group']}/{s['metric_name']} is_active=False"


def test_no_duplicate_fingerprints():
    fps = [_fingerprint(s) for s in SEEDS]
    assert len(fps) == len(set(fps)), "SEEDS 내 중복 fingerprint 발견"


# ── B. DB 통합 테스트 (DB 연결 불가 시 skip) ─────────────────────────────────

@pytest.fixture(scope="module")
def db_session_for_seed():
    try:
        import sqlalchemy as sa
        from app.core.config import settings
        engine = sa.create_engine(settings.DATABASE_URL)
        with engine.connect():
            pass
    except Exception as exc:
        pytest.skip(f"DB 연결 불가 — 통합 테스트 skip: {exc}")

    from app.db.database import SessionLocal
    from app.models.metric_recommendation_boost_rule import MetricRecommendationBoostRule

    session = SessionLocal()
    # 테스트 전 기존 seed 모두 삭제 후 재삽입
    session.query(MetricRecommendationBoostRule).delete(synchronize_session=False)
    session.commit()
    yield session
    session.close()


def test_db_seed_inserts_11(db_session_for_seed):
    from scripts.seed_metric_boost_rules import run_seed
    from app.models.metric_recommendation_boost_rule import MetricRecommendationBoostRule
    inserted, skipped = run_seed(db_session_for_seed)
    assert inserted == 11
    assert skipped == 0
    count = db_session_for_seed.query(MetricRecommendationBoostRule).count()
    assert count == 11


def test_db_seed_no_duplicates_on_rerun(db_session_for_seed):
    from scripts.seed_metric_boost_rules import run_seed
    inserted2, skipped2 = run_seed(db_session_for_seed)
    assert inserted2 == 0
    assert skipped2 == 11
