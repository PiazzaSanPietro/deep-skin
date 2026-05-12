# Backend DB Design

현재 DB는 MySQL + SQLAlchemy ORM + Alembic migration 기준입니다.

## 연결 방식

`app/core/config.py`의 설정값으로 SQLAlchemy URL을 조합합니다.

```text
mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4
```

`DATABASE_URL` 환경 변수는 현재 `Settings` 필드가 아니므로 직접 읽지 않습니다.

## Migration

현재 migration 순서:

```text
0001_create_auth_tables.py
0002_create_analysis_image_tables.py
0003_create_skin_result_tables.py
0004_create_recommendation_tables.py
0005_seed_rules.py
0006_seed_rules_extended.py
0007_create_multivalue_ai_tables.py   ← Phase 1-1 추가 (2026-05-12)
0008_create_metric_boost_tables.py    ← Phase 2-3B 추가 (2026-05-13)
```

실행:

```powershell
cd backend
alembic upgrade head
```

## 현재 ORM 테이블

| Table | Model | 역할 |
|---|---|---|
| `users` | `User` | 계정 정보, password hash, 활성 상태 |
| `user_profiles` | `UserProfile` | 나이, 성별, 피부 타입, 민감 여부, 알러지/선호 정보 |
| `refresh_tokens` | `RefreshToken` | refresh token hash, 만료/폐기 시각 |
| `analysis_sessions` | `AnalysisSession` | 분석 단위 세션과 상태 |
| `uploaded_images` | `UploadedImage` | 업로드 이미지 파일 메타데이터 |
| `skin_json_records` | `SkinJsonRecord` | 개발용 AI-Hub JSON 원본 저장 |
| `skin_part_results` | `SkinPartResult` | AI/JSON에서 나온 부위별 분석 결과 |
| `ingredient_rules` | `IngredientRule` | 성분 key와 민감 피부 주의 여부 |
| `recommendation_rules` | `RecommendationRule` | 부위/이슈/severity별 추천 규칙 |
| `part_recommendations` | `PartRecommendation` | 세션별 최종 추천 결과 저장 |
| `products` | `Product` | 제품 후보 테이블. 현재 추천 API에서 직접 사용하지 않음 |
| `ai_raw_responses` | `AiRawResponse` | multivalue AI 응답 원본 JSON 보존 (Phase 1-1 추가) |
| `skin_part_detections` | `SkinPartDetection` | YOLO bbox 검출 결과 및 crop bbox (Phase 1-1 추가) |
| `skin_metric_values` | `SkinMetricValue` | equipment.* 상세 측정값 row 단위 (Phase 1-1 추가) |
| `metric_threshold_rules` | `MetricThresholdRule` | metric별 위험 기준/임계값 관리 (Phase 2-3A 추가) |
| `metric_recommendation_boost_rules` | `MetricRecommendationBoostRule` | 임계값 기반 추천 보정 rule (Phase 2-3B 연결, seed 미삽입) |

## 주요 관계

```text
users
├─ user_profiles (1:1)
├─ refresh_tokens (1:N)
└─ analysis_sessions (1:N)
   ├─ uploaded_images (1:N)
   ├─ skin_json_records (1:N)
   ├─ skin_part_results (1:N)
   └─ part_recommendations (1:N)

recommendation_rules
└─ part_recommendations.rule_id
```

`skin_part_results`는 이미지 기반 결과면 `image_id`, 개발용 JSON 결과면 `json_record_id`가 연결됩니다.

## 세션 상태

현재 코드에서 사용하는 주요 상태:

| status | 의미 |
|---|---|
| `pending` | 세션 생성 직후 |
| `processing` | 이미지/JSON 처리 중 |
| `completed` | 분석과 추천 생성 완료 |
| `failed` | 이미지 추론 실패 등 |

## 분석 결과 저장 규칙

`skin_part_results`의 핵심 필드:

| Field | 설명 |
|---|---|
| `raw_part_name` | 모델/JSON 원본 부위명 |
| `display_part_name` | UI 표시용 부위명 |
| `metric_name` | 지표 key |
| `metric_display_name` | 지표 표시명 |
| `issue_type` | 이슈 key. 예: `pore`, `wrinkle`, `dryness`, `sagging` |
| `severity` | `normal`, `mild`, `moderate`, `severe` |
| `grade_value` | 원본 등급 값. 분류 등급 정수 (0~3) |
| `predicted_value` | 이미지 기반 AI 모델 예측 회귀값. mock/remote inference 경로에서 저장. 예: `0.62` |
| `measured_value` | AI-Hub JSON 또는 피부 측정 장비 기반 원본 수치. dev JSON 경로에서 저장. 예: `2.73`, `55.667` |
| `confidence_score` | 모델 신뢰도 |
| `model_name`, `model_version` | 추론 출처 |

`issue_type`에는 심각도 정보를 섞지 않습니다. 심각도는 `severity` 컬럼으로 분리합니다.

`predicted_value`와 `measured_value`는 `Float(53), nullable=True`로 DB에 존재합니다. 이미지 inference 경로에는 `predicted_value`, dev JSON 경로에는 `measured_value`가 각각 저장됩니다. 두 컬럼 모두 migration 추가 없이 기존 컬럼을 사용합니다.

## 추천 저장 규칙

`recommendation_service.generate_and_save()`는 다음 기준으로 추천을 저장합니다.

1. `skin_part_results`를 조회
2. `(display_part_name, issue_type)`별 가장 높은 severity 선택
3. `recommendation_rules`에서 `(display_part_name, issue_type, severity)` 일치 rule 조회
4. 사용자 프로필의 `allergy_ingredients`와 `sensitive` 기준으로 추천 성분 필터링
5. `part_recommendations`에 저장

현재 직접 필터링에 쓰이는 프로필 필드:

- `sensitive`
- `allergy_ingredients`

현재 저장은 되지만 추천 필터링에 직접 사용하지 않는 필드:

- `skin_type`
- `main_concerns`
- `preferred_product_types`

## 현재 미사용/확인 필요

- `products` 테이블은 현재 서비스/API 흐름에서 직접 조회하지 않습니다.
- `analysis_sessions.analyzed_at` — Phase 3-C QA에서 버그 발견 및 수정 완료 (2026-05-12). `image_service._run_flat_mode()`, `_run_multivalue_mode()`, `dev_json_service.upload_dev_json()` 각 완료 처리에서 `session.analyzed_at = datetime.utcnow()`를 설정하도록 수정. 이로써 trends 차트 X축 날짜가 실제 분석 완료 시각을 반영한다.
- `analysis_sessions.overall_status`, `summary_message`는 모델에 있지만 현재 서비스 흐름에서 갱신하지 않음 (report_service에서 동적 생성).