# Backend Agent Notes

이 문서는 `backend` 폴더에서 작업할 때 기준으로 삼는 최신 백엔드 요약입니다. 실제 코드는 FastAPI + MySQL + SQLAlchemy + Alembic 기반입니다.

## 현재 역할

Deep Skin 백엔드는 사용자가 업로드한 얼굴 이미지를 분석 세션에 연결하고, AI 추론 결과를 DB에 저장한 뒤 부위별 리포트와 rule-based 추천 결과를 제공합니다.

개발/테스트용으로 AI-Hub 형식 JSON을 직접 넣는 `/dev/analysis/sessions/{session_id}/json` 엔드포인트도 있습니다.

## 기술 스택

- FastAPI
- SQLAlchemy 2.x
- Alembic
- MySQL / PyMySQL
- Pydantic v2
- JWT Bearer 인증 (`python-jose`)
- bcrypt 비밀번호 해시
- Pillow 이미지 검증
- httpx 원격 AI 서버 호출

## 주요 폴더

```text
backend/
├── app/
│   ├── main.py
│   ├── core/          # config, security, dependencies, exceptions
│   ├── db/            # SQLAlchemy engine/session
│   ├── models/        # ORM models
│   ├── routers/       # FastAPI routers
│   ├── schemas/       # Pydantic request/response schemas
│   ├── services/      # business logic
│   └── utils/         # AI-Hub JSON parser
├── alembic/           # migrations and seed migrations
├── docs/              # backend documents
├── scripts/           # test runner, dummy AI server, cleanup script
└── uploads/           # local uploaded image storage
```

## 실행 기준

```powershell
cd backend
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --reload
```

환경 변수는 `app/core/config.py`의 `Settings`가 `.env`에서 읽습니다. `DATABASE_URL`은 직접 환경 변수로 읽지 않고 `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`으로 조합합니다.

## 현재 API

- `GET /health`
- `POST /auth/signup`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /users/me/profile`
- `PUT /users/me/profile`
- `POST /analysis/sessions`
- `POST /analysis/sessions/{session_id}/images`
- `GET /analysis/metrics/trends`
- `GET /analysis/sessions/{session_id}/metrics`
- `GET /analysis/sessions/{session_id}/report`
- `GET /recommendations/sessions/{session_id}`
- `POST /dev/analysis/sessions/{session_id}/json`

## Phase 1-1 / Phase 1-2 / Phase 1-3 진행 현황 (2026-05-12)

multivalue AI 응답 저장을 위한 DB 테이블 3개와 ORM 모델이 추가됐습니다.  
Phase 1-2에서 parser가 작성됐고, Phase 1-3에서 `image_service.py` 저장 흐름이 연결됐습니다. 모두 완료 상태입니다.

### 추가된 테이블 (migration 0007)

| 테이블 | 용도 |
|--------|------|
| `ai_raw_responses` | AI 서버 전체 응답 JSON 원본 보존 |
| `skin_part_detections` | YOLO bbox 검출 결과 및 crop bbox 저장 |
| `skin_metric_values` | equipment.* 상세 측정값 row 단위 저장 |

### 추가된 ORM 모델

- `app/models/ai_raw_response.py` — `AiRawResponse`
- `app/models/skin_part_detection.py` — `SkinPartDetection`
- `app/models/skin_metric_value.py` — `SkinMetricValue`

### Phase 1-2 parser 완료

- `app/services/multivalue_parser.py` 추가
- `parse_multivalue_response()` — raw response / annotations / equipment / detections ORM 객체 생성
- `parse_annotations()` — `parts[*].annotations.*` 중 `null`이 아닌 등급값을 `SkinPartResult`로 변환
- `parse_equipment()` — numeric equipment 값을 `SkinMetricValue`로 변환, `metric_key` 기반 `metric_group` / `metric_name` 파싱
- `parse_detections()` — `detected_parts[*].bbox_xyxy`는 `bbox_source="yolo"`, 미검출 part의 `images.bbox`는 `bbox_source="full_image_fallback"`로 변환
- `chin_moisture`는 `is_dummy=true`, `dummy_reason="label_not_trained"`, `source="dummy_fallback"` 처리
- unknown annotation/equipment key, invalid bbox, non-numeric value는 warning log 후 skip
- DB add/commit, `image_service.py`, `recommendation_service.py`, router/API, frontend는 변경하지 않음

### Phase 1-3 DB 저장 연결 완료

- `app/core/config.py` — `AI_MULTIVALUE_INFERENCE_URL` 추가 (기본값 `http://localhost:9001/inference/skin`)
- `app/schemas/image_upload.py` — `PartResult.confidence_score`를 `Optional[float] = None`으로 변경 (multivalue annotations는 confidence 미제공)
- `app/services/inference_service.py` — `run_multivalue_inference()` 추가 (원본 dict 반환, InferenceResult 변환 없음)
- `app/services/image_service.py` — `AI_INFERENCE_MODE` 분기 추가
  - `"multivalue"`: `_run_multivalue_mode()` — 4개 테이블 순차 저장 + 추천 생성
  - `"mock"` / `"remote"`: `_run_flat_mode()` — 기존 flat 저장 로직 완전 유지
- `tests/test_multivalue_storage.py` — DB 통합 테스트 6개 (DB 없으면 자동 skip)

검증:

- `../.venv/bin/python -m compileall app tests` 통과
- `../.venv/bin/python -m pytest tests/test_multivalue_parser.py -q` 통과 (`9 passed`)
- `../.venv/bin/python -m pytest tests/test_multivalue_storage.py -v` 통과 (`6 passed`, DB 연결됨)
- `../.venv/bin/python -m pytest` 전체 통과 (`15 passed`)
- DB row count (example_response.json 기준):
  - `ai_raw_responses`: 1
  - `skin_part_results`: 11
  - `skin_metric_values`: 80
  - `skin_part_detections`: 8
- 기존 mock mode recommendation / report 흐름 변경 없음

### Phase 2-3B 추천 보정 로직 완료 (2026-05-12)

- `app/services/recommendation_boost_service.py` 추가
  - `apply_boost(db, session_id, display_part_name, categories, ingredients, care_tips)` → `tuple[list, list, list]`
  - `SkinMetricValue` 조회 (is_dummy=False 필터), `MetricRecommendationBoostRule` 매칭
  - `or_()` 사용: `raw_part_name == metric.raw_part_name OR raw_part_name IS NULL`
  - 규칙 중복 적용 방지: `seen_rule_ids` set으로 rule.id 기준 dedup
  - 단일 규칙 적용 실패 시 warning log 후 skip (전체 보정 실패 시 원본 반환)
  - 헬퍼: `_matches_threshold`, `_apply_single_rule`, `_boost_ingredient_priority`, `_add_new_ingredients`, `_add_unique`, `_extract_keys`
- `app/services/recommendation_service.py` 수정
  - `boost_service.apply_boost()` 호출 추가 (rule 조회 직후, `_filter_ingredients` 직전)
  - allergy/sensitive 필터링은 boost 이후에 적용 (기존 `_filter_ingredients` 순서 유지)
- `tests/test_recommendation_metric_boost.py` — 10개 단위 테스트 (DB 없이 mock 기반)

검증:

- `compileall app tests` 통과
- `pytest` 전체 31 passed (21 기존 + 10 신규)
- 기존 mock/remote mode 추천 흐름 변경 없음 (seed 데이터 없으므로 boost 미적용 = 원본 그대로)

### Phase 2-3A DB/ORM 준비 완료 (2026-05-12)

- `alembic/versions/0008_create_metric_boost_tables.py` — migration 추가
- `app/models/metric_threshold_rule.py` — `MetricThresholdRule` ORM 모델 추가
- `app/models/metric_recommendation_boost_rule.py` — `MetricRecommendationBoostRule` ORM 모델 추가
- `alembic/env.py` — 두 모델 import 추가

검증:

- `alembic upgrade head` 성공
- downgrade/upgrade 왕복 통과
- `metric_threshold_rules` / `metric_recommendation_boost_rules` 테이블 및 인덱스 생성 확인
- `compileall app alembic tests` 통과
- `pytest` 21 passed 유지

Phase 2-3B에서 `recommendation_service` 보정 로직 연결 완료.  
운영 seed 미삽입 (임계값 미확정) — Phase 2-5에서 후보 검증 완료.

### Phase 2-1 metrics API 완료 (2026-05-12)

- `app/schemas/metrics.py` — `MetricItem`, `PartMetrics`, `MetricsResponse` Pydantic 스키마 추가
- `app/services/metric_service.py` — `get_metrics()` 구현 (facepart ASC 정렬, 부위별 그룹핑)
- `app/routers/analysis.py` — `GET /analysis/sessions/{session_id}/metrics` 엔드포인트 추가
- `tests/test_metrics_api.py` — HTTP-layer 통합 테스트 6개 (DB 없으면 자동 skip)

검증:

- `compileall app tests` 통과
- `pytest` 전체 21 passed (9 parser + 6 storage + 6 metrics)

### Phase 2-4 metrics trends API 완료 (2026-05-12)

- `app/schemas/metrics.py` — `TrendPoint`, `TrendsResponse` 스키마 추가
- `app/services/metric_trend_service.py` — `get_trends()` 구현
  - `AnalysisSession.status="completed"`, `SkinMetricValue.is_dummy=False` 필터
  - 최근 `limit`개를 DESC로 가져와 Python에서 ASC 재정렬
  - `analyzed_at IS NULL` → `created_at` 대체 (`func.coalesce`)
- `app/routers/analysis.py` — `GET /analysis/metrics/trends` 엔드포인트 추가
- `tests/test_metrics_trends_api.py` — DB 통합 테스트 6개

검증:

- `compileall app tests` 통과
- `pytest` 전체 37 passed (31 기존 + 6 신규)

### Phase 2-5 추천 보정 seed 후보 검증 완료 (2026-05-12)

- `docs/recommendation_boost_seed_plan.md` 추가
  - 모공(≥700) / 수분(≤35) / 주름 Ra(≥25) / 탄력 R2(≤0.35) 후보 rule 정의
  - 운영 반영 전 체크리스트 / 시나리오 3개 / INSERT SQL 참고 포함
- `tests/test_recommendation_boost_seed_candidates.py` 추가 — 10개 mock 기반 단위 테스트
  - MagicMock으로 SkinMetricValue/MetricRecommendationBoostRule 흉내
  - 4개 지표 보정 동작, threshold 불충족, dummy 제외, allergy/sensitive 필터, rule 없음, 잘못된 rule skip

검증:

- `compileall app tests` 통과
- `pytest` 전체 47 passed (37 기존 + 10 신규)
- 운영 DB seed 미삽입 유지
- 기존 추천 흐름 변경 없음

### Phase 3-C QA 완료 (2026-05-12) — E2E 안정화 점검

- 버그 수정: `analyzed_at` 미설정 문제
  - `image_service._run_flat_mode()` / `_run_multivalue_mode()` / `dev_json_service.upload_dev_json()` 3곳에 `session.analyzed_at = datetime.utcnow()` 추가
  - 수정 전: trends 차트 X축이 `created_at`(세션 생성 시각)을 표시
  - 수정 후: trends 차트 X축이 `analyzed_at`(분석 완료 시각)을 표시
- 문서 정합성 확인 완료: `AGENTS.md`, `agent_db_design_fixed.md`, multivalue_ai_db_design_plan.md
- `compileall app tests` 통과 / `pytest` 47 passed 유지

### Phase 3-E 실제 얼굴 이미지 YOLO bbox E2E 검증 완료 (2026-05-12)

- 테스트 이미지: 940×1410 정면 얼굴 (uploads/skin_images/1/20/...)
- AI 서버 직접 테스트: `detected_parts` 3개 검출 (forehead conf=0.766, lips conf=0.770, chin conf=0.913)
- session_id=104 (user_id=69)

DB 저장 결과:

| 테이블 | 건수 |
|--------|------|
| `ai_raw_responses` | 1 |
| `skin_part_results` | 11 |
| `skin_metric_values` | 80 |
| `skin_part_detections` | 8 (yolo 3건 + fallback 5건) |
| `part_recommendations` | 8 |

`skin_part_detections` bbox_source 분포:
- `bbox_source=yolo`: forehead (conf=0.766), lips (conf=0.770), chin (conf=0.913)
- `bbox_source=full_image_fallback`: glabella, left_eye, right_eye, left_cheek, right_cheek

실제 추론값 예시:
- `forehead_moisture`: 50.64 (이전 100×100 test: 0.0)
- `forehead_elasticity_R2`: 0.438
- `chin_elasticity_R2`: 0.826
- `forehead pigmentation`: grade=3 (severe)
- `forehead wrinkle`: grade=4 (severe)
- `chin sagging`: grade=2 (mild)
- `lips dryness`: grade=2 (mild)

report `overall_status`: 집중 관리 필요 (grade 3~4 항목 존재)

API 검증:
- `GET /analysis/sessions/104/report` — `status=completed`, 6 part_reports ✅
- `GET /analysis/sessions/104/metrics` — 7 parts, 80 metrics ✅
- `GET /analysis/metrics/trends?...forehead moisture` — 2 trend points (session 88 + 104) ✅
- `GET /analysis/metrics/trends?...forehead elasticity R2` — value=0.4381 ✅
- `GET /analysis/reports/latest` — session_id=104 ✅

결론: YOLO bbox 검출 → DB 저장 → API 조회 전체 흐름 이상 없음. pytest 47 passed 유지.

### Phase 3-D 실환경 E2E 테스트 완료 (2026-05-12)

- 테스트 계정: `e2etest@example.com` / `user_id=69`
- AI 서버: port 9001, `models_loaded=true`, `face_detector_loaded=true`, `device=cpu`
- sys.path 버그 수정: `multivalue_ai_server.py`에 `_DINOV3_DIR` 추가 (dinov3 패키지 로드 실패 수정)
- `.env`: `AI_INFERENCE_MODE=multivalue`, `AI_MULTIVALUE_INFERENCE_URL=http://localhost:9001/inference/skin`

DB row counts (session_id=88, 100×100 test image):

| 테이블 | 건수 |
|--------|------|
| `ai_raw_responses` | 1 |
| `skin_part_results` | 11 |
| `skin_metric_values` | 80 |
| `skin_part_detections` | 8 (all `full_image_fallback` — YOLO miss on 100×100) |
| `part_recommendations` | 8 |

검증 결과:
- `GET /analysis/sessions/88/report` — `status=completed`, 6 part_reports ✅
- `GET /analysis/sessions/88/metrics` — 7 parts, 총 80 metric values ✅
- `GET /analysis/metrics/trends?raw_part_name=forehead&metric_group=moisture&metric_name=moisture` — trend 1개 반환 ✅
- `GET /analysis/metrics/trends?raw_part_name=left_cheek&metric_group=pore&metric_name=pore_count` — trend 1개 반환 ✅
- `GET /recommendations/sessions/88` — 8 recommendations ✅
- `chin_moisture`: `is_dummy=true`, `dummy_reason="label_not_trained"` ✅
- `ai_raw_responses.raw_json`: 5431 bytes 저장 ✅
- `pytest` 47 passed ✅

trends API 파라미터 주의: `metric_name`은 DB의 `skin_metric_values.metric_name` 컬럼값 기준.  
예: forehead moisture → `metric_name=moisture` (not `forehead_moisture`). `metric_key`는 별도 필드.

### Phase 3-A 1차 베타 boost seed 삽입 완료 (2026-05-12)

- `scripts/seed_metric_boost_rules.py` 추가 (재실행 안전, 중복 방지)
- `tests/test_metric_boost_seed_script.py` 추가 (13개 SEEDS 검증 + 2개 DB 통합 = 15 tests)
- 11개 seed 삽입 (피부 측정 장비 해석 기준 1차 베타값)

| metric | 임계값 | priority |
|---|---|---|
| moisture / moisture | ≤ 35 (low_is_bad) | 100 |
| pore / pore_count | ≥ 700 (high_is_bad) | 100 |
| wrinkle / Ra | ≥ 25 (high_is_bad) | 100 |
| elasticity / R2 | ≤ 0.50 (low_is_bad) | 90 |
| elasticity / R7 | ≤ 0.35 (low_is_bad) | 90 |
| wrinkle / Rmax | ≥ 120 (high_is_bad) | 80 |
| wrinkle / Rt | ≥ 120 (high_is_bad) | 80 |
| wrinkle / Rz | ≥ 80 (high_is_bad) | 80 |
| wrinkle / Rq | ≥ 18 (high_is_bad) | 80 |
| pigmentation / pigmentation_count | ≥ 100 (high_is_bad) | 60 |
| acne / acne_count | ≥ 30 (high_is_bad) | 70 |

주의:
- 1차 베타값 — 통계 기반 최종 임계값 아님
- `zinc_pca`는 `boost_ingredients`로만 사용 (add_ingredients 금지)
- YOLO 미검출 0.0값이 low_is_bad 임계값 의도치 않게 트리거 가능 (알려진 한계)
- `pytest` 62 passed (47 기존 + 15 신규)

### Phase 3-A-1 metric 분포 분석 완료 (2026-05-12)

- `docs/metric_threshold_analysis.md` 작성
- 분석 대상: moisture/moisture, pore/pore_count, wrinkle/Ra, wrinkle/Rmax, elasticity/R2, elasticity/R7, pigmentation_count, acne_count
- 현재 DB 유효 세션: n=1 (session_id=104, 940×1410) — session_id=88(100×100) 제외
- 보조 참고: `example_response.json`, `facepart_03_test/0001_01_F_03.json`

핵심 발견:
- **moisture ≤ 35**: 도메인 기준 부합, 즉시 삽입 가능 ✅
- **pore_count ≥ 700**: 레퍼런스 값 753 → 트리거 확인, 즉시 삽입 가능 ✅
- **wrinkle Ra ≥ 25**: 보수적 임계값, 과보정 없음, 즉시 삽입 가능 ✅
- **elasticity R2 ≤ 0.35**: 지나치게 엄격할 수 있음 → **0.45로 상향 검토 권장**
- `zinc_pca` → `ingredient_rules` 미등록이나 boost_ingredients로는 동작 가능 (add_ingredients로는 금지)
- 통계적 percentile 산출 불가 (n=1) — 최소 50건 이상 필요

### Phase 3-B-1 YOLO 미검출 0.0 더미 처리 완료 (2026-05-12)

- **문제**: YOLO 미검출 부위의 0.0값이 `is_dummy=False`로 저장되어 `low_is_bad` boost rule(moisture≤35, R2≤0.50 등)을 의도치 않게 트리거
- **수정 파일**: `app/services/multivalue_parser.py`

변경 내용:
- `_is_yolo_miss_zero(raw_part_name, value, detected_part_names, is_label_dummy)` 헬퍼 추가
- `parse_equipment()` 시그니처에 `detected_part_names: set[str] | None = None` 파라미터 추가
- YOLO 미검출 부위 + value=0.0 → `is_dummy=True`, `dummy_reason="yolo_miss_or_model_fallback"`, `source="dummy_fallback"`
- `parse_multivalue_response()` — `detected_parts`로 `detected_part_names` set 빌드 후 `parse_equipment()`에 전달

예외 처리:
- `full_face` 부위 (acne_count, pigmentation_count): YOLO 의존 아님 → 항상 is_dummy=False
- `chin_moisture`: `label_not_trained`이 우선 적용, YOLO miss 판별 수행 안 함
- `detected_part_names=None`: 하위 호환 — YOLO miss 판별 스킵 (None은 미전달)
- value가 0.0이 아니면 YOLO miss여도 is_dummy=False 유지

테스트 (`tests/test_multivalue_parser.py`):
- 15개 신규 테스트 추가 (총 24 tests)
  - YOLO miss 0.0 → dummy / 검출 0.0 → real / chin_moisture 유지 / full_face 예외 / 비제로 예외 / 하위 호환 / E2E contrast
  - `_is_yolo_miss_zero` 단위 테스트 6개
- `tests/test_recommendation_metric_boost.py`: `test_apply_boost_dummy_vs_real_metric_contrast` 추가 (총 11 tests)
- **78 passed** (`pytest -q` 전체)

**`recommendation_boost_service.py`는 이미 `SkinMetricValue.is_dummy == False` 필터를 갖고 있었음 — 변경 불필요**

---

## 회귀값 반영 현황 (2026-05-11 완료)

현재 백엔드는 `skin_part_results.measured_value` / `predicted_value` 컬럼을 활용합니다.

- `predicted_value`: 이미지 기반 AI 모델 예측 회귀값. mock/remote inference 경로에서 저장
- `measured_value`: AI-Hub JSON 또는 피부 측정 장비 기반 원본 수치. dev JSON 경로에서 저장
- `grade_value` / `severity` 기존 흐름 유지 — 기존 코드와 하위 호환
- `recommendation_service`는 현재 `severity` 기반으로 동작 (미변경)
- 두 컬럼은 migration 0003에서 이미 생성되어 있으며, 신규 migration 추가 불필요

관련 문서: `docs/ai_inference_contract.md`, `docs/regression_implementation_plan.md`, `docs/regression_result_db_plan.md`

## 작업 주의사항

- 기능 코드를 수정할 때는 라우터보다 서비스 계층의 실제 흐름을 먼저 확인합니다.
- 인증 필요 API는 `Depends(get_current_user)`와 `Authorization: Bearer <access_token>`을 기준으로 합니다.
- 업로드 파일은 로컬 `UPLOAD_DIR/{user_id}/{session_id}/{uuid}.jpg`에 저장되고 DB에는 경로와 메타데이터만 저장됩니다.
- 추천 로직은 현재 `recommendation_rules`, `ingredient_rules`, `part_recommendations` 기반 rule-based 방식입니다.
- `products` 테이블/모델은 존재하지만 현재 API 응답 생성 흐름에서는 직접 사용하지 않습니다.
- 모델 학습, EfficientNet/ViT 학습 코드, 이미지 분류 학습 파이프라인은 현재 백엔드 범위가 아닙니다.

## 참고 문서

- `docs/agent_backend_overview.md`
- `docs/agent_api_design_fixed.md`
- `docs/agent_auth_jwt.md`
- `docs/agent_db_design_fixed.md`
- `docs/agent_image_upload.md`
- `docs/agent_recommendation_seed_fixed.md`
- `docs/ai_inference_contract.md`
- `docs/backend_test_guide.md`
