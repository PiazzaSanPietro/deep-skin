# Metric 분포 분석 및 임계값 후보 검토

작성일: 2026-05-12  
목적: `skin_metric_values` 분포 확인 + 운영 boost seed 임계값 후보 타당성 평가

---

## 1. 현재 데이터 현황

### 1.1 분석 가능 세션

| session_id | 이미지 해상도 | YOLO 검출 | 비고 |
|---|---|---|---|
| 88 | 100×100 | 0개 (all fallback) | **분석 제외** — 크기 미달 |
| 104 | 940×1410 | 3개 (forehead/lips/chin) | 실제 얼굴 이미지 ✅ |

> `is_dummy=false` 조건 및 `session_id=88` 제외 기준 적용.

### 1.2 데이터 수 요약

현재 DB에 저장된 실제 측정값(is_dummy=false, session=104)은 **단일 세션(n=1)**에서 나온 것입니다.  
통계적으로 유의미한 percentile 산출이 불가능합니다.  
아래 수치는 참고용으로만 사용해야 하며, 임계값 확정에는 **최소 50~100건 이상의 세션 데이터가 필요**합니다.

### 1.3 보조 참고 자료

DB 외에 다음 2개 샘플이 분석에 참고됩니다:

| 출처 | 내용 |
|---|---|
| `scripts/face_multivalue_inf/example_response.json` | AI-Hub 형식 레퍼런스 응답 (grade 포함) |
| `scripts/facepart_03_test/0001_01_F_03.json` | left_eye 부위 장비 측정 레퍼런스 |

---

## 2. Metric별 분포 통계

> **주의**: n=1(session_id=104), YOLO 미검출 부위는 값이 0으로 저장됨.  
> 0값은 실제 측정값이 아닌 모델 미추론 결과일 수 있음.

### 2.1 moisture / moisture

| raw_part_name | n (DB) | 값 (session 104) | 참고 (example_response.json) |
|---|---|---|---|
| forehead | 1 | **50.64** | 59.97 |
| left_cheek | 1 | 0.00 ← YOLO miss | 65.81 |
| right_cheek | 1 | 0.00 ← YOLO miss | 66.24 |
| chin | n/a | n/a | n/a (chin moisture 미학습) |

**도메인 기준 (Corneometer CM 825 기반 피부 수분 지표)**

| 등급 | 범위 |
|---|---|
| 건조 (dry) | < 30 |
| 약건조 (slightly dry) | 30–45 |
| 정상 (normal) | 45–65 |
| 충분 (well-hydrated) | > 65 |

현재 세션 104 forehead_moisture=50.64 → 정상 범위.  
기존 후보 임계값 ≤ 35 → 약건조 하한과 일치. **후보로 적절**.

---

### 2.2 pore / pore_count

| raw_part_name | n (DB) | 값 (session 104) | 참고 (example_response.json) |
|---|---|---|---|
| left_cheek | 1 | 0.00 ← YOLO miss | **753.0** |
| right_cheek | 1 | 0.00 ← YOLO miss | **753.0** |

**관찰**: session 104에서 YOLO가 볼 부위를 검출하지 못해 0.0이 저장됨. example_response 기준 l/r cheek 모두 753.

현재 후보 임계값 ≥ 700 → example_response 값(753)이 이를 초과함.  
쿼리 기준: `pore_count=753 ≥ 700` → 보정 트리거됨. **후보로 타당**.

---

### 2.3 wrinkle / Ra

| raw_part_name | n (DB) | 값 (session 104) | 참고 |
|---|---|---|---|
| left_eye | 1 | 0.00 ← YOLO miss | example_response: 17.56 (grade=1) |
| right_eye | 1 | 0.00 ← YOLO miss | example_response: 18.42 (grade=1) |
| — | — | — | facepart_03_test: 14.58 (grade=3) |

**참고 샘플 분포**

| 출처 | Ra 값 | grade (l_perocular_wrinkle) |
|---|---|---|
| example_response l_eye | 17.56 | 1 |
| example_response r_eye | 18.42 | 1 |
| facepart_03_test l_eye | 14.58 | 3 |

> grade=3(severe)인 샘플의 Ra=14.58이 grade=1 샘플보다 낮은 것은  
> Ra 단독이 grade를 결정하는 지표가 아님을 시사합니다.  
> grade는 Ra 외에 여러 wrinkle 지표(Rmax, Rt, Rz 등)의 종합 평가임.

현재 후보 임계값 ≥ 25 µm → 현재 데이터 범위(14–18)보다 높음.  
Ra ≥ 25는 "중증 이상"에 해당하는 보수적 임계값임. **과보정 위험 없음, 후보 유효**.

---

### 2.4 wrinkle / Rmax

| raw_part_name | n (DB) | 값 | 참고 |
|---|---|---|---|
| left_eye | 1 | 0.00 ← YOLO miss | example_response: 133.96 |
| right_eye | 1 | 0.00 ← YOLO miss | example_response: 139.04 |
| — | — | — | facepart_03_test: 121.23 |

> Rmax는 현재 boost seed 후보에 포함되지 않음. 참고용 수치만 기록.

---

### 2.5 elasticity / R2

| raw_part_name | n (DB) | 값 (session 104) | 참고 (example_response.json) |
|---|---|---|---|
| forehead | 1 | **0.4381** | 0.5535 |
| left_cheek | 1 | 0.00 ← YOLO miss | 0.5969 |
| right_cheek | 1 | 0.00 ← YOLO miss | 0.5858 |
| chin | 1 | **0.8259** | 0.4704 |

**도메인 기준 (Cutometer MPA 580 / R2 = Ua/Uf, 탄력성 지수)**

| 등급 | 범위 |
|---|---|
| 탄력 좋음 | > 0.70 |
| 보통 | 0.50–0.70 |
| 주의 | 0.35–0.50 |
| 저하 | < 0.35 |

현재 샘플:
- session 104 forehead R2=0.438 → **주의** 구간
- example_response forehead R2=0.554 → 보통 구간
- example_response cheek R2: 0.58~0.60 → 보통~좋음

현재 후보 임계값 ≤ 0.35 → "탄력 저하" 기준에 해당.  
현재 두 샘플 모두 0.438 이상 → 임계값이 트리거되지 않음.  
**임계값이 지나치게 낮을 가능성 있음** — 0.45 또는 0.50도 검토 가치 있음.

---

### 2.6 elasticity / R7

| raw_part_name | n (DB) | 값 (session 104) | 참고 (example_response.json) |
|---|---|---|---|
| forehead | 1 | **0.2656** | 0.3022 |
| left_cheek | 1 | 0.00 ← YOLO miss | n/a |
| right_cheek | 1 | 0.00 ← YOLO miss | n/a |
| chin | 1 | **0.5482** | 0.2923 |

> R7 (Ur/Uf) = 생물학적 탄력 = 외력 제거 후 원위치 복귀 비율.  
> 문헌 정상 범위: > 0.35–0.40. session 104 forehead=0.266 → 정상 이하.  
> 현재 boost seed 후보에 R7 임계값은 없음 (참고용).

---

### 2.7 pigmentation / pigmentation_count

| raw_part_name | n (DB) | 값 (session 104) | 참고 (example_response.json) |
|---|---|---|---|
| full_face | 1 | **13** | **146** |

> 두 샘플 간 편차 매우 큼 (13 vs 146).  
> 현재 boost seed 후보에 pigmentation_count 임계값 없음.  
> 이미지 해상도·ROI 크기에 따라 count가 크게 달라짐.  
> **임계값 설정 시 이미지 조건 통제 필요.**

---

### 2.8 acne / acne_count

| raw_part_name | n (DB) | 값 (session 104) | 참고 (example_response.json) |
|---|---|---|---|
| full_face | 1 | **0** | **0** |

> 두 샘플 모두 0. 분포 분석 불가.

---

## 3. boost 성분 키 존재 여부 확인

| 성분 key | `ingredient_rules` 존재 | caution_for_sensitive | 비고 |
|---|---|---|---|
| `bha` | ✅ | 1 (주의) | 민감 피부 필터링 적용됨 |
| `zinc_pca` | ❌ **없음** | — | **ingredient_rules에 미등록** |
| `ceramide` | ✅ | 0 | |
| `panthenol` | ✅ | 0 | |
| `peptide` | ✅ | 0 | |
| `adenosine` | ✅ | 0 | |

> **`zinc_pca`는 `ingredient_rules` 테이블에 없습니다.**  
> 그러나 `recommendation_rules`의 pore(moderate/severe)에는 이미  
> `{"key": "zinc_pca", "name": "징크 PCA"}` 형식으로 포함되어 있습니다.  
> boost_service는 `ingredient_rules`가 아닌 `recommendation_rules`의 기존 성분 목록에서  
> key 기반으로 우선순위를 조정하므로, `zinc_pca`가 기존 추천에 있다면 boost 동작에 지장 없음.  
> **단, `add_ingredients`(신규 추가) 용도로는 zinc_pca 사용 불가 — key가 rules에 없으면 추가 시 표시명 없음.**

---

## 4. 임계값 후보 평가 요약

| metric | direction | 후보 임계값 | 평가 | 비고 |
|---|---|---|---|---|
| moisture / moisture | low_is_bad | ≤ 35 | ✅ 도메인 기준 부합 | "약건조 하한"과 일치 |
| pore / pore_count | high_is_bad | ≥ 700 | ✅ 레퍼런스 753 → 트리거됨 | 타당 |
| wrinkle / Ra | high_is_bad | ≥ 25 | ✅ 보수적 임계값, 과보정 없음 | 현재 데이터 14–18 범위 |
| elasticity / R2 | low_is_bad | ≤ 0.35 | ⚠️ 다소 엄격 | 0.45–0.50도 검토 가치 |

---

## 5. 데이터 충분성 평가

### 5.1 지금 당장 seed 삽입이 가능한 metric

아래 조건을 모두 충족할 때만 해당됩니다:

- 도메인 문헌 기준이 명확하고
- 현재 샘플과 일치하며
- 성분 key가 DB에 존재함

| metric | 삽입 가능 여부 | 근거 |
|---|---|---|
| moisture ≤ 35 | ✅ **가능** | 피부 수분 임계값 도메인 기준 명확, ceramide/panthenol key 존재 |
| pore_count ≥ 700 | ✅ **가능** | 레퍼런스 샘플에서 트리거 확인, bha key 존재 (zinc_pca는 기존 rules에 있음) |
| wrinkle Ra ≥ 25 | ✅ **가능** | 보수적 임계값으로 과보정 없음, peptide/adenosine key 존재 |
| elasticity R2 ≤ 0.35 | ⚠️ **검토 필요** | 임계값이 지나치게 낮을 수 있음 — 0.45로 상향 권장 |

### 5.2 추가 데이터가 필요한 metric

| metric | 이유 |
|---|---|
| wrinkle / Rmax | boost 후보 없음, 기준 불명확 |
| elasticity / R7 | boost 후보 없음 |
| pigmentation_count | 샘플 간 편차 극심 (13 vs 146) — ROI 조건 통제 필요 |
| acne_count | 양 샘플 모두 0 — 분포 확인 불가 |
| cheek/eye 전체 | YOLO 미검출로 DB 값이 0 — 유효 데이터 없음 |

---

## 6. 최소 데이터 요건

운영 seed 임계값을 통계적으로 근거 있게 정하려면:

| 조건 | 최소 권장 |
|---|---|
| 전체 세션 수 | 50건 이상 |
| 각 부위별 YOLO 검출 세션 | 30건 이상 |
| 수분 데이터 있는 세션 | 30건 (forehead YOLO 검출) |
| 볼 모공 데이터 있는 세션 | 30건 (cheek YOLO 검출) |
| 눈가 주름 데이터 있는 세션 | 30건 (eye YOLO 검출) |

**현재 상태: 유효 세션 1건 — 통계적 percentile 산출 불가**

---

## 7. 권장 사항

### 7.1 즉시 삽입 가능 (도메인 기준 + 검증 완료)

```
moisture ≤ 35  → ceramide, panthenol 추가
pore_count ≥ 700 → bha 우선순위 상향 (zinc_pca는 기존 rules에서 boost)
wrinkle Ra ≥ 25 → peptide, adenosine 우선순위 상향
```

> 세 항목 모두 `recommendation_boost_seed_plan.md`의 기존 후보와 일치하며,  
> ingredient key 존재 확인 완료. 도메인 기준 타당.

### 7.2 임계값 조정 권장

```
elasticity R2 임계값: 0.35 → 0.45 상향 검토
이유: 현재 forehead R2=0.438(session 104)이 0.35 이하가 아닌데도 "주의" 구간 해당.
      0.45로 상향하면 이 경우도 보정 트리거됨.
```

### 7.3 데이터 축적 후 재검토 대상

```
elasticity R2 최종 임계값 (0.35 vs 0.45 vs 0.50)
pore_count 임계값 (700이 적절한지)
pigmentation_count 임계값 (ROI 조건 통제 후)
```

---

## 8. zinc_pca 처리 방침

`ingredient_rules`에 `zinc_pca`가 없으나:

1. `recommendation_rules`의 pore(moderate/severe)에 이미 포함됨
2. boost_service는 `recommend_ingredients` 중에서 key 기반 우선순위 조정
3. `add_ingredients`(신규 추가)로는 zinc_pca 사용 금지

**결론**: `boost_ingredients=["bha", "zinc_pca"]`로 설정해도  
`_boost_ingredient_priority`는 기존 추천 목록 안에서 순서만 바꾸므로 동작에 문제 없음.  
단, `add_ingredients`에 zinc_pca를 넣으면 표시명 없이 key만 저장될 수 있음 → 사용하지 말 것.

---

## 9. YOLO 미검출 부위의 0.0값 트리거 — ✅ Phase 3-B-1 수정 완료 (2026-05-12)

**수정 전 문제**: YOLO 미검출 부위 metric이 `is_dummy=False`로 저장되어  
`low_is_bad` 임계값(moisture ≤ 35, R2 ≤ 0.50, R7 ≤ 0.35)이 의도치 않게 트리거됨.

**수정 내용** (`multivalue_parser.py`):  
- `parse_multivalue_response()`가 `detected_parts`에서 `detected_part_names` set을 빌드해 `parse_equipment()`에 전달  
- YOLO 미검출 부위(`raw_part_name not in detected_part_names`) + `value == 0.0` → `is_dummy=True`, `dummy_reason="yolo_miss_or_model_fallback"`  
- `recommendation_boost_service.apply_boost()`는 이미 `is_dummy == False` 필터를 보유 → 추가 변경 없음

**예외 처리**:
- `full_face` (acne_count, pigmentation_count): YOLO 의존 없음 → is_dummy=False 유지
- `chin_moisture`: `label_not_trained` 우선 — YOLO 검출 여부와 무관
- value ≠ 0.0: YOLO miss여도 is_dummy=False 유지 (실제 추론값으로 간주)
- `detected_part_names=None` (미전달): 하위 호환 — YOLO miss 판별 스킵

session 104 반영 결과 (수정 후):
- `left_cheek moisture=0.0` → `is_dummy=True` (더 이상 boost 트리거 안 됨) ✅
- `left_cheek R2=0.0` → `is_dummy=True` ✅
- `left_cheek R7=0.0` → `is_dummy=True` ✅

---

## 10. 다음 단계

**Phase 3-A 완료**: 11개 1차 베타 seed 삽입 완료 (`scripts/seed_metric_boost_rules.py`).  
**Phase 3-B-1 완료**: YOLO 미검출 0.0 더미 처리 수정 완료.

향후 검토 항목:
1. 유효 데이터 50건 이상 축적 후 임계값 재분석 (elasticity R2 0.50 → 조정 가능)
2. pigmentation_count 임계값 100 — ROI/조명 통제 후 재검토
3. pore_count 임계값 700 — 해상도별 ROI 보정 후 재검토
4. 신규 세션 저장 시 YOLO 미검출 부위가 올바르게 `is_dummy=True`로 저장되는지 E2E 재검증 권장
