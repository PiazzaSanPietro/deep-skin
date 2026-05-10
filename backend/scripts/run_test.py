"""
Mock / Remote 모드 통합 테스트 스크립트.

Usage:
    python scripts/run_test.py [--mode mock|remote]
"""
import argparse
import io
import sys
import time

import httpx
from PIL import Image
import sqlalchemy as sa

BASE = "http://localhost:8000"
DB_URL = "mysql+pymysql://root:zxasqw12@localhost:3306/deep_skin?charset=utf8mb4"
TEST_EMAIL = f"testrunner_{int(time.time())}@example.com"
TEST_PW = "test1234"


def section(title: str):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print("="*55)


def ok(msg: str):
    print(f"  [OK]  {msg}")


def fail(msg: str):
    print(f"  [FAIL] {msg}")
    sys.exit(1)


def warn(msg: str):
    print(f"  [WARN] {msg}")


def make_test_jpeg() -> bytes:
    img = Image.new("RGB", (100, 100), color=(200, 180, 160))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def run_tests(mode: str):
    # ── 1. 회원가입 ──────────────────────────────────────────
    section("1. 회원가입")
    r = httpx.post(f"{BASE}/auth/signup", json={"email": TEST_EMAIL, "password": TEST_PW, "name": "테스트러너"})
    if r.status_code == 201:
        ok(f"signup 성공 | user_id={r.json()['id']}")
    else:
        fail(f"signup 실패 | {r.status_code} {r.text}")

    # ── 2. 로그인 ─────────────────────────────────────────────
    section("2. 로그인")
    r = httpx.post(f"{BASE}/auth/login", json={"email": TEST_EMAIL, "password": TEST_PW})
    if r.status_code != 200:
        fail(f"login 실패 | {r.status_code} {r.text}")
    access_token = r.json()["access_token"]
    ok(f"login 성공 | access_token 발급 완료")
    headers = {"Authorization": f"Bearer {access_token}"}

    # ── 3. 프로필 저장 ────────────────────────────────────────
    section("3. 프로필 저장")
    r = httpx.put(f"{BASE}/users/me/profile", headers=headers, json={
        "age": 28, "sensitive": 1, "allergy_ingredients": ["retinol"]
    })
    if r.status_code == 200:
        ok("프로필 저장 성공")
    else:
        warn(f"프로필 저장 실패 | {r.status_code} {r.text}")

    # ── 4. 분석 세션 생성 ─────────────────────────────────────
    section("4. 분석 세션 생성")
    r = httpx.post(f"{BASE}/analysis/sessions", headers=headers, json={"session_name": f"테스트_{mode}"})
    if r.status_code != 201:
        fail(f"세션 생성 실패 | {r.status_code} {r.text}")
    session_id = r.json()["id"]
    ok(f"세션 생성 성공 | session_id={session_id}")

    # ── 5. 이미지 업로드 ──────────────────────────────────────
    section("5. 이미지 업로드")
    jpeg_bytes = make_test_jpeg()
    r = httpx.post(
        f"{BASE}/analysis/sessions/{session_id}/images",
        headers=headers,
        files={"file": ("test_face.jpg", jpeg_bytes, "image/jpeg")},
        timeout=35,
    )
    if r.status_code != 200:
        fail(f"이미지 업로드 실패 | {r.status_code} {r.text}")
    body = r.json()
    upload_status = body.get("upload_status")
    session_status = body.get("session_status")
    parts_count = len(body.get("inference_result", {}).get("parts", []))
    model_name = body.get("inference_result", {}).get("model_name", "?")
    if upload_status == "processed" and session_status == "completed":
        ok(f"이미지 업로드 성공 | upload_status={upload_status} session_status={session_status}")
        ok(f"inference parts={parts_count}개 | model={model_name}")
    else:
        fail(f"이미지 업로드 상태 이상 | upload_status={upload_status} session_status={session_status}")

    # ── 6. DB 직접 조회: skin_part_results ───────────────────
    section("6. DB 확인: skin_part_results")
    engine = sa.create_engine(DB_URL)
    with engine.connect() as conn:
        result = conn.execute(
            sa.text("SELECT COUNT(*) FROM skin_part_results WHERE session_id=:sid AND image_id IS NOT NULL"),
            {"sid": session_id}
        )
        count = result.scalar()
        if count == parts_count:
            ok(f"skin_part_results {count}개 저장 확인 (parts 수와 일치)")
        else:
            fail(f"skin_part_results 불일치 | DB={count}개 / parts={parts_count}개")

        rows = conn.execute(
            sa.text("SELECT display_part_name, issue_type, severity FROM skin_part_results WHERE session_id=:sid"),
            {"sid": session_id}
        ).fetchall()
        for row in rows:
            print(f"    → {row[0]} | {row[1]} | {row[2]}")

    # ── 7. DB 직접 조회: part_recommendations ────────────────
    section("7. DB 확인: part_recommendations")
    with engine.connect() as conn:
        rec_count = conn.execute(
            sa.text("SELECT COUNT(*) FROM part_recommendations WHERE session_id=:sid"),
            {"sid": session_id}
        ).scalar()
        if rec_count > 0:
            ok(f"part_recommendations {rec_count}개 생성 확인")
        else:
            fail("part_recommendations 생성되지 않음")

    # ── 8. 추천 API ───────────────────────────────────────────
    section("8. GET /recommendations/sessions/{session_id}")
    r = httpx.get(f"{BASE}/recommendations/sessions/{session_id}", headers=headers)
    if r.status_code != 200:
        fail(f"추천 API 실패 | {r.status_code} {r.text}")
    recs = r.json().get("recommendations", [])
    ok(f"추천 API 성공 | {len(recs)}개 추천 반환")
    for rec in recs:
        excl = [f"{e['key']}({e.get('reason_type','?')})" for e in rec.get("excluded_ingredients", [])]
        excl_str = ", ".join(excl) if excl else "없음"
        print(f"    → {rec['display_part_name']} | {rec['issue_type']} | {rec['severity']} | 제외: {excl_str}")

    # ── 9. 리포트 API ─────────────────────────────────────────
    section("9. GET /analysis/sessions/{session_id}/report")
    r = httpx.get(f"{BASE}/analysis/sessions/{session_id}/report", headers=headers)
    if r.status_code != 200:
        fail(f"리포트 API 실패 | {r.status_code} {r.text}")
    report = r.json()
    overall = report.get("overall_summary", {})
    part_reports = report.get("part_reports", [])
    ok(f"리포트 API 성공 | overall_status={overall.get('status')} | parts={len(part_reports)}개")
    ok(f"main_message: {overall.get('main_message')}")
    for mi in overall.get("main_issues", []):
        print(f"    main_issue: {mi['issue_type']} / {mi['severity']}")
    for pr in part_reports:
        print(f"    → {pr['display_part_name']} | issues={len(pr['issues'])}개 | rec={'있음' if pr.get('recommendation') else '없음'}")

    section(f"[{mode.upper()} 모드 테스트 완료]")
    ok("모든 항목 통과")
    engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="mock", choices=["mock", "remote"])
    args = parser.parse_args()
    run_tests(args.mode)
