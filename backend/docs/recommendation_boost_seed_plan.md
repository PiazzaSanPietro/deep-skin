# 추천 보정 seed 후보 계획

작성일: 2026-05-12  
상태: **후보 단계** — 운영 DB에 아직 삽입하지 않음

---

## 1. 목적

`skin_metric_values`에 저장된 상세 측정값을 기반으로  
기존 rule-based 추천 결과(`recommendation_rules`)를 보정하는 로직을 운영에 반영하기 위해  
어떤 rule을 삽입할지 후보를 정의하고 테스트로 검증한다.

보정 로직 자체는 Phase 2-3B에서 `recommendation_boost_service.py`로 구현 완료됐다.  
이 문서는 **어떤 값으로 rule을 채울 것인지**에 대한 후보 계획이다.

---

## 2. 현재 상태

| 항목 | 상태 |
|---|---|
| `metric_recommendation_boost_rules` 테이블 | 생성 완료 (migration 0008) |
| `metric_threshold_rules` 테이블 | 생성 완료 (migration 0008) |
| `recommendation_boost_service.apply_boost()` | 구현 완료 |
| 운영 seed 삽입 | **미삽입** |
| 임계값 확정 | **미확정** — 임상/데이터 분석 후 확정 필요 |

seed가 없으면 `apply_boost()`는 아무 보정도 하지 않고 원본 추천 결과를 그대로 반환한다.

---

## 3. metric 방향성 (direction)

| direction | 의미 | 예시 |
|---|---|---|
| `high_is_bad` | 값이 클수록 문제 — `threshold_min` 이상이면 보정 | 모공 개수, 주름 Ra |
| `low_is_bad` | 값이 작을수록 문제 — `threshold_max` 이하이면 보정 | 수분, 탄력 R2 |
| `metric_specific` | 별도 범위 지정 — `threshold_min` ≤ value ≤ `threshold_max` | 향후 확장 |

`_matches_threshold`는 [threshold_min, threshold_max] 범위 안에 value가 들어올 때 True를 반환한다.  
`high_is_bad`이면 `threshold_min`만 설정, `low_is_bad`이면 `threshold_max`만 설정한다.

---

## 4. 후보 rule 정의

> 아래 수치는 임상 데이터 분석 전 **초안 수치**입니다. 운영 반영 전 반드시 실측 데이터로 검증해야 합니다.

### 4-1. 모공 보정 (pore)

```
metric_group  = pore
metric_name   = pore_count
raw_part_name = NULL  (모든 부위 적용)
direction     = high_is_bad
threshold_min = 700
threshold_max = NULL

boost_ingredients = ["bha", "zinc_pca"]
add_ingredients   = NULL
add_categories    = NULL
add_care_tips     = "피지와 모공 관리를 함께 진행하세요."
priority = 0
```

**보정 의도**: 모공 개수 700개 이상이면 기존 추천 성분 중 BHA(살리실산), 징크PCA를 앞으로 이동.

### 4-2. 수분 보정 (moisture)

```
metric_group  = moisture
metric_name   = moisture
raw_part_name = NULL
direction     = low_is_bad
threshold_min = NULL
threshold_max = 35

boost_ingredients = NULL
add_ingredients   = ["ceramide", "panthenol"]
add_categories    = NULL
add_care_tips     = "보습 후 장벽 케어 제품을 함께 사용하세요."
priority = 0
```

**보정 의도**: 수분 35% 이하이면 ceramide, panthenol을 보조 성분으로 추가.

### 4-3. 주름 보정 (wrinkle)

```
metric_group  = wrinkle
metric_name   = Ra
raw_part_name = NULL
direction     = high_is_bad
threshold_min = 25
threshold_max = NULL

boost_ingredients = ["peptide", "adenosine"]
add_ingredients   = NULL
add_categories    = NULL
add_care_tips     = "눈가 주름은 보습과 탄력 케어를 함께 관리해주세요."
priority = 0
```

**보정 의도**: 주름 Ra 25 이상이면 peptide, adenosine을 우선순위로 이동.

### 4-4. 탄력 보정 (elasticity)

```
metric_group  = elasticity
metric_name   = R2
raw_part_name = NULL
direction     = low_is_bad
threshold_min = NULL
threshold_max = 0.35

boost_ingredients = NULL
add_ingredients   = ["peptide", "adenosine"]
add_categories    = NULL
add_care_tips     = "탄력 저하가 보이는 부위는 장벽 케어와 탄력 케어를 병행해주세요."
priority = 0
```

**보정 의도**: 탄력 R2 0.35 이하이면 peptide, adenosine을 보조 성분으로 추가.

---

## 5. allergy / sensitive 필터링 순서 보장

`recommendation_service.generate_and_save()`의 호출 순서:

```
1. recommendation_rules 기반 기본 추천 결과 도출
   (categories, ingredients, care_tips)
2. boost_service.apply_boost() → 보정 적용
   - boost_ingredients: 기존 성분 우선순위 재배치
   - add_ingredients: 보조 성분 추가
   - add_care_tips: 케어 팁 추가
3. _filter_ingredients() → allergy/sensitive 필터링
   - 알러지 성분 → excluded_ingredients (reason_type: allergy)
   - 민감 피부 주의 성분 → excluded_ingredients (reason_type: sensitive)
```

boost로 add된 성분도 필터링 대상에 포함된다. 예:  
- boost로 ceramide 추가 → 사용자 allergy에 ceramide 있으면 excluded  
- boost로 peptide 추가 → sensitive 피부 주의 성분이면 caution excluded

---

## 6. 테스트 검증 방법

테스트 파일: `tests/test_recommendation_boost_seed_candidates.py`

테스트는 운영 DB 삽입 없이 `unittest.mock.MagicMock`으로 DB를 흉내낸다.  
`MetricRecommendationBoostRule`, `SkinMetricValue` 객체를 테스트 내에서 직접 생성한다.

확인 항목:

| 번호 | 확인 내용 |
|---|---|
| 1 | pore_count ≥ 700 → bha/zinc_pca 우선순위 상승 |
| 2 | moisture ≤ 35 → ceramide/panthenol 추가 |
| 3 | wrinkle Ra ≥ 25 → peptide/adenosine 우선순위 상승 |
| 4 | elasticity R2 ≤ 0.35 → peptide/adenosine 추가 |
| 5 | threshold 조건 불충족 → 원본 유지 |
| 6 | is_dummy=True metric → 보정 제외 |
| 7 | allergy 성분은 boost 후에도 제거 |
| 8 | sensitive caution 성분은 boost 후에도 제거 |
| 9 | boost rule 없음 → 원본 유지 |
| 10 | 잘못된 rule (비정상 JSON) → warning + skip, 원본 유지 |

---

## 7. Phase 3-A 1차 베타 seed 삽입 완료 (2026-05-12)

`scripts/seed_metric_boost_rules.py`로 11개 1차 베타 seed 삽입 완료.

| metric | 임계값 | 상태 |
|---|---|---|
| moisture / moisture | ≤ 35 | ✅ 삽입 |
| pore / pore_count | ≥ 700 | ✅ 삽입 |
| wrinkle / Ra | ≥ 25 | ✅ 삽입 |
| elasticity / R2 | ≤ 0.50 (베타) | ✅ 삽입 |
| elasticity / R7 | ≤ 0.35 | ✅ 삽입 |
| wrinkle / Rmax | ≥ 120 | ✅ 삽입 |
| wrinkle / Rt | ≥ 120 | ✅ 삽입 |
| wrinkle / Rz | ≥ 80 | ✅ 삽입 |
| wrinkle / Rq | ≥ 18 | ✅ 삽입 |
| pigmentation / pigmentation_count | ≥ 100 (priority=60) | ✅ 삽입 |
| acne / acne_count | ≥ 30 | ✅ 삽입 |

주의 사항:
- 이 seed는 피부 측정 장비 해석 기준 기반 1차 베타값 — 통계 기반 최종 임계값 아님
- `zinc_pca`는 `ingredient_rules` 미등록 → `add_ingredients`로 사용 안 함, `boost_ingredients`만 사용
- Rz의 `metric_name`은 DB 저장값 기준 `"Rz"` (metric_key는 `"..._Rz=Rtm"`)
- YOLO 미검출 부위의 0.0값이 low_is_bad 임계값을 의도치 않게 트리거할 수 있음 (알려진 한계)
- 데이터 50건 이상 축적 후 임계값 재분석 예정

## 8. 운영 반영 전 필요한 확인 사항

아래 항목을 충족해야 임계값을 최종 확정한다 (1차 베타 삽입 완료, 재검토 기준):

- [ ] 유효 데이터 50건 이상 축적
- [ ] elasticity R2 임계값 0.50 → 재검토 (0.45~0.50 범위)
- [ ] pore_count 임계값 700 → 해상도/ROI 조건 통제 후 재검토
- [x] ~~YOLO 미검출 부위 metric is_dummy=True 처리 로직 추가~~ ✅ Phase 3-B-1 완료 (2026-05-12)
  - `multivalue_parser.parse_equipment()` — YOLO 미검출 부위 + value=0.0 → `is_dummy=True`, `dummy_reason="yolo_miss_or_model_fallback"`
  - `recommendation_boost_service.apply_boost()` — `is_dummy == False` 필터 이미 존재, 변경 없음
- [ ] `raw_part_name=NULL` 전체 부위 적용이 의도한 대로 동작하는지 확인
- [ ] 모공 개수 단위 확인 (example_response.json 기준 left_cheek pore_count: ~700~800 범위)
- [ ] 수분 단위 확인 (측정 범위: 0~100, 정상 범위: 50~60 수준)
- [ ] 운영 seed 삽입 후 기존 추천 결과 변화 여부 사전 검토

---

## 8. 수동 테스트 시나리오

### 시나리오 1: 볼 모공 보정

```
부위: left_cheek (볼)
이슈: pore / moderate
기존 추천 성분: [niacinamide, bha, zinc_pca]
측정값: pore_count = 753

기대 결과:
  recommend_ingredients[0].key = "bha"      ← 우선순위 상승
  recommend_ingredients[1].key = "zinc_pca"  ← 우선순위 상승
  recommend_ingredients[2].key = "niacinamide"
  care_tips: "피지와 모공 관리를 함께 진행하세요." 포함
```

### 시나리오 2: 이마 수분 보정

```
부위: forehead (이마)
이슈: dryness / mild
기존 추천 성분: [hyaluronic_acid, glycerin]
측정값: moisture = 31.2

기대 결과:
  recommend_ingredients에 ceramide 추가
  recommend_ingredients에 panthenol 추가
  care_tips: "보습 후 장벽 케어 제품을 함께 사용하세요." 포함
```

### 시나리오 3: 눈가 주름 + 민감 피부 필터링

```
부위: left_eye (눈가)
이슈: wrinkle / mild
기존 추천 성분: [retinol, adenosine, peptide]
측정값: wrinkle Ra = 28.5
사용자: sensitive=True, retinol은 caution_for_sensitive=True

기대 결과:
  adenosine, peptide는 앞으로 이동 (boost)
  retinol은 excluded_ingredients로 이동 (sensitive 필터링)
  recommend_ingredients = [adenosine, peptide]
  excluded_ingredients = [retinol (reason_type: sensitive)]
  care_tips: "눈가 주름은 보습과 탄력 케어를 함께 관리해주세요." 포함
```

---

## 9. 운영 seed INSERT 예시 (미삽입 — 확정 후 사용)

```sql
-- 운영 반영 시 사용할 INSERT 예시 (현재 미삽입)
INSERT INTO metric_recommendation_boost_rules
  (metric_group, metric_name, raw_part_name, direction,
   threshold_min, threshold_max,
   boost_ingredients, add_ingredients, add_care_tips, priority, is_active)
VALUES
  ('pore', 'pore_count', NULL, 'high_is_bad',
   700, NULL,
   '["bha", "zinc_pca"]', NULL,
   '피지와 모공 관리를 함께 진행하세요.', 0, 1),

  ('moisture', 'moisture', NULL, 'low_is_bad',
   NULL, 35,
   NULL, '["ceramide", "panthenol"]',
   '보습 후 장벽 케어 제품을 함께 사용하세요.', 0, 1),

  ('wrinkle', 'Ra', NULL, 'high_is_bad',
   25, NULL,
   '["peptide", "adenosine"]', NULL,
   '눈가 주름은 보습과 탄력 케어를 함께 관리해주세요.', 0, 1),

  ('elasticity', 'R2', NULL, 'low_is_bad',
   NULL, 0.35,
   NULL, '["peptide", "adenosine"]',
   '탄력 저하가 보이는 부위는 장벽 케어와 탄력 케어를 병행해주세요.', 0, 1);
```
