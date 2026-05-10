"""Phase 2 API flow integration test."""
import sys
import io
import requests
from PIL import Image

BASE = "http://127.0.0.1:8000"
EMAIL = "test@example.com"
PASSWORD = "test1234"


def ok(label):
    print(f"  [PASS] {label}")


def fail(label, detail=""):
    print(f"  [FAIL] {label}  {detail}")
    sys.exit(1)


def check(label, resp, expected_status=None):
    ok_codes = {200, 201} if expected_status is None else {expected_status}
    if resp.status_code not in ok_codes:
        fail(label, f"HTTP {resp.status_code}: {resp.text[:200]}")
    ok(label)
    return resp.json()


# ── 1. 회원가입 ────────────────────────────────────────────────────────────────
print("\n[1] SIGNUP")
r = requests.post(f"{BASE}/auth/signup", json={
    "email": "phase2@test.com",
    "password": "test1234",
    "name": "Phase2테스터",
})
if r.status_code in (200, 201):
    ok("Signup new account")
elif r.status_code == 400:
    ok("Signup - 이미 존재하는 계정 (OK, 재사용)")
else:
    fail("Signup", f"HTTP {r.status_code}: {r.text[:200]}")

# ── 2. 로그인 ──────────────────────────────────────────────────────────────────
print("\n[2] LOGIN")
r = requests.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD})
data = check("Login with test@example.com", r)
token = data["access_token"]
headers = {"Authorization": f"Bearer {token}"}
ok(f"Token obtained ({len(token)} chars)")

# ── 3. 프로필 조회 ─────────────────────────────────────────────────────────────
print("\n[3] GET PROFILE")
r = requests.get(f"{BASE}/users/me/profile", headers=headers)
data = check("GET /users/me/profile", r)
print(f"     age={data.get('age')}, gender={data.get('gender')}, "
      f"skin_type={data.get('skin_type')}, sensitive={data.get('sensitive')}")
concerns = data.get("main_concerns") or []
allergy = data.get("allergy_ingredients") or []
products = data.get("preferred_product_types") or []
required = [data.get("age"), data.get("gender"), data.get("skin_type"),
            data.get("sensitive"), concerns, allergy, products]
complete = all(v is not None and v != [] for v in required)
ok(f"Profile complete={complete}")

# ── 4. 프로필 저장 ─────────────────────────────────────────────────────────────
print("\n[4] PUT PROFILE")
r = requests.put(f"{BASE}/users/me/profile", headers=headers, json={
    "age": 28,
    "birth_year": 1997,
    "gender": "F",
    "skin_type": 3,
    "sensitive": 1,
    "main_concerns": ["wrinkle", "pore"],
    "allergy_ingredients": ["retinol"],
    "preferred_product_types": ["세럼/에센스", "크림/모이스처라이저"],
})
data = check("PUT /users/me/profile", r)
ok(f"Profile saved: {data.get('message')}")

# ── 5. 분석 세션 생성 ──────────────────────────────────────────────────────────
print("\n[5] CREATE SESSION")
r = requests.post(f"{BASE}/analysis/sessions", headers=headers,
                  json={"session_name": "Phase2 테스트 분석"})
data = check("POST /analysis/sessions", r)
session_id = data["id"]
ok(f"Session created: id={session_id}, status={data.get('status')}")

# ── 6. 이미지 업로드 ────────────────────────────────────────────────────────────
print("\n[6] UPLOAD IMAGE")
# Pillow로 유효한 100x100 JPEG 생성
img = Image.new("RGB", (100, 100), color=(200, 180, 170))
buf = io.BytesIO()
img.save(buf, format="JPEG")
jpeg_bytes = buf.getvalue()
ok(f"Test JPEG created: {len(jpeg_bytes)} bytes")
files = {"file": ("test_face.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")}
r = requests.post(
    f"{BASE}/analysis/sessions/{session_id}/images",
    headers={"Authorization": f"Bearer {token}"},
    files=files,
)
data = check("POST /analysis/sessions/{session_id}/images", r)
ok(f"Upload: session_status={data.get('session_status')}, upload_status={data.get('upload_status')}")
parts = data.get("inference_result", {}).get("parts", [])
ok(f"Inference parts: {len(parts)}")

# ── 7. 리포트 조회 ─────────────────────────────────────────────────────────────
print("\n[7] GET REPORT")
r = requests.get(f"{BASE}/analysis/sessions/{session_id}/report", headers=headers)
data = check("GET /analysis/sessions/{session_id}/report", r)
ok(f"Report status: {data.get('status')}")
overall = data.get("overall_summary", {})
ok(f"Overall: {overall.get('status')} / {overall.get('main_message','')[:50]}")
part_reports = data.get("part_reports", [])
ok(f"Part reports: {len(part_reports)} parts")
for p in part_reports:
    issues = p.get("issues", [])
    rec = p.get("recommendation") or {}
    ingr_count = len(rec.get("ingredients") or [])
    excl_count = len(rec.get("excluded_ingredients") or [])
    ok(f"  {p['display_part_name']}: {len(issues)} issues, {ingr_count} ingr, {excl_count} excl")

# ── 8. 로그아웃 ────────────────────────────────────────────────────────────────
print("\n[8] LOGOUT")
r = requests.post(f"{BASE}/auth/logout", headers=headers)
data = check("POST /auth/logout", r)
ok(f"Logout: {data.get('message')}")

print("\n" + "="*50)
print("ALL TESTS PASSED")
print("="*50)
