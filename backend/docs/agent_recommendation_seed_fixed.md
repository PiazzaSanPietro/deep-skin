# Recommendation Rules and Seed Data

현재 추천은 AI가 직접 제품을 추천하는 방식이 아니라 DB seed rule 기반으로 생성합니다.

## 관련 테이블

| Table | 역할 |
|---|---|
| `ingredient_rules` | 성분 key, 표시명, 민감 피부 주의 여부 |
| `recommendation_rules` | 부위/이슈/severity별 추천 카테고리, 추천 성분, 관리 팁 |
| `part_recommendations` | 세션별 최종 추천 결과 |
| `user_profiles` | 알러지 성분, 민감 여부 필터링에 사용 |

Seed migration:

```text
0005_seed_rules.py
0006_seed_rules_extended.py
```

## 추천 생성 흐름

`recommendation_service.generate_and_save(db, session_id, user_id)` 기준:

```text
1. 기존 part_recommendations 삭제
2. skin_part_results 조회
3. 사용자 프로필 조회
4. profile.allergy_ingredients -> allergy_keys 구성
5. profile.sensitive == 1이면 ingredient_rules.caution_for_sensitive 성분 조회
6. (display_part_name, issue_type)별 가장 높은 severity 선택
7. recommendation_rules에서 정확히 일치하는 rule 조회
8. recommend_ingredients에서 allergy/sensitive 성분 제외
9. part_recommendations 저장
10. sensitive 사용자면 '전체 얼굴' sensitive rule을 추가로 저장할 수 있음
```

## Rule 매칭 키

```text
display_part_name
issue_type
severity
```

예:

```text
display_part_name = 볼
issue_type = pore
severity = moderate
```

## issue_type / severity 규칙

`issue_type`에는 이슈 종류만 저장합니다. 심각도는 `severity`로 분리합니다.

사용되는 주요 값:

| issue_type | 의미 |
|---|---|
| `pore` | 모공 |
| `wrinkle` | 주름 |
| `dryness` | 건조 |
| `sagging` | 처짐/탄력 |
| `sensitive` | 민감 피부 추가 추천 |

`ai_inference_contract.md`에는 remote AI 확장을 위해 `pigmentation`, `moisture`, `acne`도 허용 후보로 문서화되어 있습니다. 실제 추천 rule이 없으면 추천이 생성되지 않습니다.

Severity:

```text
normal
mild
moderate
severe
```

## 성분 제외 규칙

`_filter_ingredients()` 기준:

- 추천 성분 key가 `profile.allergy_ingredients`에 있으면 제외하고 `reason_type = allergy`로 기록
- 사용자가 `sensitive == 1`이고 성분이 `ingredient_rules.caution_for_sensitive == True`이면 제외하고 `reason_type = sensitive`로 기록
- 제외된 성분은 `part_recommendations.excluded_ingredients`에 저장
- 제외 이유는 `exclusion_reason`에 저장

## 현재 사용하지 않는 프로필 값

아래 값은 저장되지만 현재 추천 생성 필터에는 직접 반영되지 않습니다.

- `skin_type`
- `main_concerns`
- `preferred_product_types`

TODO: 제품 추천 고도화 시 위 필드를 rule 매칭 또는 랭킹에 반영할지 결정해야 합니다.

## Products 테이블

`products` 테이블과 ORM 모델은 존재하지만 현재 `recommendation_service`에서 조회하지 않습니다. 현재 API는 제품 row가 아니라 rule에 저장된 카테고리/성분/팁 중심으로 응답합니다.

TODO: 실제 제품 추천이 필요하면 `products` 조회/필터링/응답 스키마를 별도로 설계해야 합니다.