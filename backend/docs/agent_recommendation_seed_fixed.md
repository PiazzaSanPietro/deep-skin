# 추천 규칙 Seed 데이터 설계

## 목적

초기 추천 시스템은 생성형 AI 추천이 아니라 **DB 기반 Rule-based 추천**으로 구현한다.

즉, 화장품 카테고리, 추천 성분, 관리법, 설명 문구는 DB에 미리 저장한다.

모델 분석 결과가 생성되면 백엔드는 다음 값을 기준으로 추천 규칙을 조회한다.

```text
display_part_name
issue_type
severity
```

이후 사용자 프로필의 다음 값을 기준으로 추천 성분을 필터링한다.

```text
user_profiles.skin_type
user_profiles.sensitive
user_profiles.allergy_ingredients
user_profiles.preferred_product_types
```

---

# 1. 추천 규칙 사용 기준

## 추천 생성 흐름

```text
1. skin_part_results에서 부위별 문제 지표 조회
2. display_part_name, issue_type, severity 기준으로 recommendation_rules 조회
3. user_profiles에서 민감성 여부, 알레르기 성분 조회
4. recommend_ingredients 중 알레르기 성분 제외
5. 민감성 피부 주의 성분은 제외하거나 care_tip에 주의 문구 추가
6. 최종 추천 결과를 part_recommendations에 저장
7. API 응답으로 반환
```

---

# 2. issue_type / severity 저장 규칙

## 핵심 원칙

`issue_type`에는 `pore_high`, `wrinkle_high`, `moisture_low`처럼 상태가 포함된 값을 저장하지 않는다.

상태는 `severity` 컬럼으로 구분한다.

## 권장 저장 방식

```text
issue_type = pore
severity = normal / mild / moderate / severe

issue_type = wrinkle
severity = normal / mild / moderate / severe

issue_type = moisture
severity = normal / mild / moderate / severe
```

## 비권장 저장 방식

```text
pore_high
wrinkle_high
moisture_low
dryness_high
```

## 사용 가능한 issue_type

```text
pore
pigmentation
moisture
wrinkle
dryness
sagging
acne
sensitive
```

## severity 기준

```text
normal   : 정상 / 양호 / 유지 관리
mild     : 경미 / 예방 관리
moderate : 관리 필요
severe   : 집중 관리 필요
```

---

# 3. 성분 key 저장 기준

성분은 화면 표시명과 내부 key를 분리해서 관리한다.

예:

```json
{
  "key": "retinol",
  "name": "레티놀"
}
```

사용자 알레르기 성분도 가능하면 `key` 기준으로 저장한다.

예:

```json
["retinol", "fragrance", "alcohol"]
```

화면에는 한글명으로 보여준다.

---

# 4. 중복 방지 인덱스 권장

`recommendation_rules` 테이블에는 아래 unique key를 추가하는 것을 권장한다.

```sql
ALTER TABLE recommendation_rules
ADD UNIQUE KEY uq_recommendation_rules_part_issue_severity (
    display_part_name,
    issue_type,
    severity
);
```

---

# 5. ingredient_rules Seed

성분별 주의사항을 미리 저장한다.

```sql
INSERT INTO ingredient_rules (
    ingredient_name,
    display_name,
    caution_for_sensitive,
    description
) VALUES
('hyaluronic_acid', '히알루론산', FALSE, '수분 공급에 도움을 줄 수 있는 보습 성분입니다.'),
('ceramide', '세라마이드', FALSE, '피부 장벽 강화와 보습 관리에 도움을 줄 수 있는 성분입니다.'),
('glycerin', '글리세린', FALSE, '수분을 끌어당겨 피부 보습에 도움을 줄 수 있는 성분입니다.'),
('panthenol', '판테놀', FALSE, '피부 진정과 장벽 관리에 도움을 줄 수 있는 성분입니다.'),
('madecassoside', '마데카소사이드', FALSE, '민감 피부 진정 관리에 도움을 줄 수 있는 성분입니다.'),
('allantoin', '알란토인', FALSE, '피부 진정과 보호에 도움을 줄 수 있는 성분입니다.'),
('niacinamide', '나이아신아마이드', FALSE, '피부 톤, 색소침착, 피지 관리에 도움을 줄 수 있는 성분입니다.'),
('vitamin_c', '비타민C', TRUE, '색소침착 관리에 도움을 줄 수 있으나 민감 피부는 자극에 주의해야 합니다.'),
('bha', 'BHA', TRUE, '피지와 모공 관리에 도움을 줄 수 있으나 자극이 있을 수 있어 사용 빈도 조절이 필요합니다.'),
('zinc_pca', '징크 PCA', FALSE, '피지 조절과 모공 관리에 도움을 줄 수 있는 성분입니다.'),
('retinol', '레티놀', TRUE, '주름 개선과 탄력 관리에 도움을 줄 수 있으나 민감 피부는 낮은 농도부터 사용해야 합니다.'),
('peptide', '펩타이드', FALSE, '피부 탄력과 주름 관리에 도움을 줄 수 있는 성분입니다.'),
('adenosine', '아데노신', FALSE, '주름 개선 기능성 성분으로 사용됩니다.'),
('collagen', '콜라겐', FALSE, '탄력 관리 제품에 자주 사용되는 성분입니다.'),
('shea_butter', '시어버터', FALSE, '건조한 부위 보습 관리에 도움을 줄 수 있는 성분입니다.'),
('fragrance', '향료', TRUE, '민감 피부 또는 알레르기 사용자는 피하는 것이 좋습니다.'),
('alcohol', '알코올', TRUE, '건조하거나 민감한 피부에는 자극이 될 수 있습니다.');
```

---

# 6. recommendation_rules Seed

아래 Seed 데이터는 모두 다음 기준을 따른다.

```text
issue_type = 지표명
severity = normal / mild / moderate / severe
```

---

## 6.1 볼 - 모공

```sql
INSERT INTO recommendation_rules (
    display_part_name, issue_type, issue_display_name, severity,
    reason_template, recommend_categories, recommend_ingredients, care_tips
) VALUES
(
    '볼', 'pore', '모공', 'normal',
    '볼 부위의 모공 상태가 양호하게 분석되었습니다. 현재 상태를 유지하기 위한 기본 관리가 적합합니다.',
    JSON_ARRAY('수분 토너', '가벼운 보습 크림', '저자극 클렌저'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'hyaluronic_acid', 'name', '히알루론산'),
        JSON_OBJECT('key', 'ceramide', 'name', '세라마이드'),
        JSON_OBJECT('key', 'glycerin', 'name', '글리세린')
    ),
    JSON_ARRAY(
        '현재 모공 상태를 유지하기 위해 과도한 각질 제거는 피하는 것이 좋습니다.',
        '세안 후 가벼운 보습제를 사용해 피부 밸런스를 유지하는 것이 좋습니다.'
    )
),
(
    '볼', 'pore', '모공', 'mild',
    '볼 부위의 모공이 약간 도드라져 보여 예방 관리가 필요합니다.',
    JSON_ARRAY('모공 케어 토너', '수분 세럼', '저자극 클렌저'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'niacinamide', 'name', '나이아신아마이드'),
        JSON_OBJECT('key', 'hyaluronic_acid', 'name', '히알루론산'),
        JSON_OBJECT('key', 'glycerin', 'name', '글리세린')
    ),
    JSON_ARRAY(
        '피지 조절과 수분 관리를 함께 하는 것이 좋습니다.',
        '강한 필링 제품보다는 저자극 모공 케어 제품부터 사용하는 것이 좋습니다.'
    )
),
(
    '볼', 'pore', '모공', 'moderate',
    '볼 부위의 모공 등급이 보통 이상으로 분석되어 모공 관리가 필요합니다.',
    JSON_ARRAY('모공 케어 토너', '피지 조절 세럼', '클레이 마스크'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'bha', 'name', 'BHA'),
        JSON_OBJECT('key', 'niacinamide', 'name', '나이아신아마이드'),
        JSON_OBJECT('key', 'zinc_pca', 'name', '징크 PCA')
    ),
    JSON_ARRAY(
        '피지 조절과 모공 케어 중심의 제품을 사용하는 것이 좋습니다.',
        '자극이 강한 필링 제품은 주 1~2회 이하로 사용하는 것이 좋습니다.'
    )
),
(
    '볼', 'pore', '모공', 'severe',
    '볼 부위의 모공 등급이 높게 분석되어 집중적인 모공 및 피지 관리가 필요합니다.',
    JSON_ARRAY('모공 집중 케어 토너', '피지 조절 세럼', '클레이 마스크', '저자극 각질 케어 제품'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'bha', 'name', 'BHA'),
        JSON_OBJECT('key', 'niacinamide', 'name', '나이아신아마이드'),
        JSON_OBJECT('key', 'zinc_pca', 'name', '징크 PCA')
    ),
    JSON_ARRAY(
        '모공과 피지 관리 제품을 사용하되 과도한 각질 제거는 피하는 것이 좋습니다.',
        '민감 피부라면 BHA 제품은 낮은 빈도부터 사용하는 것이 좋습니다.'
    )
);
```

---

## 6.2 볼 - 색소침착

```sql
INSERT INTO recommendation_rules (
    display_part_name, issue_type, issue_display_name, severity,
    reason_template, recommend_categories, recommend_ingredients, care_tips
) VALUES
(
    '볼', 'pigmentation', '색소침착', 'normal',
    '볼 부위의 색소침착 상태가 양호하게 분석되었습니다. 현재 피부 톤을 유지하는 관리가 적합합니다.',
    JSON_ARRAY('수분 크림', '자외선 차단제', '저자극 진정 크림'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'panthenol', 'name', '판테놀'),
        JSON_OBJECT('key', 'ceramide', 'name', '세라마이드'),
        JSON_OBJECT('key', 'hyaluronic_acid', 'name', '히알루론산')
    ),
    JSON_ARRAY(
        '색소침착 예방을 위해 자외선 차단제를 꾸준히 사용하는 것이 좋습니다.',
        '피부 자극을 줄이고 보습 중심으로 관리하는 것이 좋습니다.'
    )
),
(
    '볼', 'pigmentation', '색소침착', 'mild',
    '볼 부위에 약한 색소침착 경향이 보여 예방적인 톤 관리가 필요합니다.',
    JSON_ARRAY('톤 케어 세럼', '자외선 차단제', '진정 크림'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'niacinamide', 'name', '나이아신아마이드'),
        JSON_OBJECT('key', 'panthenol', 'name', '판테놀'),
        JSON_OBJECT('key', 'ceramide', 'name', '세라마이드')
    ),
    JSON_ARRAY(
        '약한 색소침착은 자외선 차단과 톤 케어를 함께 하는 것이 좋습니다.',
        '고농도 미백 제품보다는 저자극 톤 케어 제품부터 사용하는 것이 좋습니다.'
    )
),
(
    '볼', 'pigmentation', '색소침착', 'moderate',
    '볼 부위에 색소침착이 관찰되어 피부 톤 관리가 필요합니다.',
    JSON_ARRAY('잡티 케어 세럼', '미백 기능성 앰플', '톤 케어 크림', '자외선 차단제'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'niacinamide', 'name', '나이아신아마이드'),
        JSON_OBJECT('key', 'vitamin_c', 'name', '비타민C'),
        JSON_OBJECT('key', 'panthenol', 'name', '판테놀')
    ),
    JSON_ARRAY(
        '색소침착 관리는 미백 성분과 자외선 차단을 함께 관리하는 것이 중요합니다.',
        '비타민C 제품은 아침에 사용할 경우 자외선 차단제를 함께 사용하는 것이 좋습니다.'
    )
),
(
    '볼', 'pigmentation', '색소침착', 'severe',
    '볼 부위의 색소침착 정도가 높게 분석되어 집중적인 잡티 및 톤 관리가 필요합니다.',
    JSON_ARRAY('고기능 잡티 케어 세럼', '미백 기능성 앰플', '톤 개선 크림', '자외선 차단제'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'niacinamide', 'name', '나이아신아마이드'),
        JSON_OBJECT('key', 'vitamin_c', 'name', '비타민C'),
        JSON_OBJECT('key', 'panthenol', 'name', '판테놀')
    ),
    JSON_ARRAY(
        '색소침착이 심한 경우 미백 성분과 자외선 차단을 꾸준히 병행하는 것이 좋습니다.',
        '민감 피부는 비타민C 제품을 낮은 농도부터 사용하는 것이 좋습니다.'
    )
);
```

---

## 6.3 볼 - 수분

```sql
INSERT INTO recommendation_rules (
    display_part_name, issue_type, issue_display_name, severity,
    reason_template, recommend_categories, recommend_ingredients, care_tips
) VALUES
(
    '볼', 'moisture', '수분', 'normal',
    '볼 부위의 수분 상태가 양호하게 분석되었습니다. 현재 보습 루틴을 유지하는 것이 좋습니다.',
    JSON_ARRAY('수분 토너', '수분 크림', '가벼운 보습 세럼'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'hyaluronic_acid', 'name', '히알루론산'),
        JSON_OBJECT('key', 'glycerin', 'name', '글리세린'),
        JSON_OBJECT('key', 'ceramide', 'name', '세라마이드')
    ),
    JSON_ARRAY(
        '현재 수분 상태를 유지하기 위해 세안 후 보습제를 꾸준히 사용하는 것이 좋습니다.',
        '계절 변화에 따라 보습제의 제형을 조절하는 것이 좋습니다.'
    )
),
(
    '볼', 'moisture', '수분', 'mild',
    '볼 부위의 수분이 약간 부족한 경향이 있어 예방적인 보습 관리가 필요합니다.',
    JSON_ARRAY('보습 세럼', '수분 크림', '장벽 케어 크림'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'hyaluronic_acid', 'name', '히알루론산'),
        JSON_OBJECT('key', 'ceramide', 'name', '세라마이드'),
        JSON_OBJECT('key', 'panthenol', 'name', '판테놀')
    ),
    JSON_ARRAY(
        '세안 후 피부가 마르기 전에 보습제를 사용하는 것이 좋습니다.',
        '가벼운 수분 세럼과 크림을 함께 사용하면 보습 유지에 도움이 됩니다.'
    )
),
(
    '볼', 'moisture', '수분', 'moderate',
    '볼 부위의 수분 수치가 낮게 분석되어 보습 관리가 필요합니다.',
    JSON_ARRAY('수분 크림', '보습 세럼', '장벽 케어 크림'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'hyaluronic_acid', 'name', '히알루론산'),
        JSON_OBJECT('key', 'ceramide', 'name', '세라마이드'),
        JSON_OBJECT('key', 'glycerin', 'name', '글리세린')
    ),
    JSON_ARRAY(
        '수분 세럼 사용 후 크림으로 수분을 잡아주는 것이 좋습니다.',
        '건조감이 지속되면 피부 장벽 케어 제품을 함께 사용하는 것이 좋습니다.'
    )
),
(
    '볼', 'moisture', '수분', 'severe',
    '볼 부위의 수분 부족이 높게 분석되어 집중적인 보습과 장벽 관리가 필요합니다.',
    JSON_ARRAY('고보습 크림', '장벽 케어 크림', '보습 앰플', '수면팩'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'hyaluronic_acid', 'name', '히알루론산'),
        JSON_OBJECT('key', 'ceramide', 'name', '세라마이드'),
        JSON_OBJECT('key', 'panthenol', 'name', '판테놀')
    ),
    JSON_ARRAY(
        '수분 공급 제품과 장벽 케어 제품을 함께 사용하는 것이 좋습니다.',
        '세안 후 3분 이내 보습제를 사용하는 것이 좋습니다.'
    )
);
```

---

## 6.4 눈가 - 주름

```sql
INSERT INTO recommendation_rules (
    display_part_name, issue_type, issue_display_name, severity,
    reason_template, recommend_categories, recommend_ingredients, care_tips
) VALUES
(
    '눈가', 'wrinkle', '주름', 'normal',
    '눈가 주름 상태가 양호하게 분석되었습니다. 현재 상태를 유지하기 위한 보습 중심 관리가 적합합니다.',
    JSON_ARRAY('수분 아이크림', '보습 크림', '저자극 세럼'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'hyaluronic_acid', 'name', '히알루론산'),
        JSON_OBJECT('key', 'ceramide', 'name', '세라마이드'),
        JSON_OBJECT('key', 'peptide', 'name', '펩타이드')
    ),
    JSON_ARRAY(
        '눈가 피부는 얇기 때문에 보습을 꾸준히 유지하는 것이 좋습니다.',
        '눈가를 강하게 문지르지 않는 것이 좋습니다.'
    )
),
(
    '눈가', 'wrinkle', '주름', 'mild',
    '눈가에 약한 주름 경향이 보여 예방적인 탄력 관리가 필요합니다.',
    JSON_ARRAY('아이크림', '보습 세럼', '탄력 크림'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'peptide', 'name', '펩타이드'),
        JSON_OBJECT('key', 'hyaluronic_acid', 'name', '히알루론산'),
        JSON_OBJECT('key', 'adenosine', 'name', '아데노신')
    ),
    JSON_ARRAY(
        '눈가 전용 제품을 꾸준히 사용하는 것이 좋습니다.',
        '잔주름은 건조할 때 더 도드라질 수 있으므로 보습을 함께 관리하는 것이 좋습니다.'
    )
),
(
    '눈가', 'wrinkle', '주름', 'moderate',
    '눈가 주름이 보통 이상으로 분석되어 주름 개선과 탄력 관리가 필요합니다.',
    JSON_ARRAY('아이크림', '주름 개선 세럼', '탄력 크림'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'peptide', 'name', '펩타이드'),
        JSON_OBJECT('key', 'adenosine', 'name', '아데노신'),
        JSON_OBJECT('key', 'ceramide', 'name', '세라마이드')
    ),
    JSON_ARRAY(
        '눈가 전용 제품을 사용하는 것이 좋습니다.',
        '눈가 피부는 얇기 때문에 자극이 적은 제품부터 사용하는 것이 좋습니다.'
    )
),
(
    '눈가', 'wrinkle', '주름', 'severe',
    '눈가 주름 깊이가 높게 분석되어 집중적인 주름 개선 관리가 필요합니다.',
    JSON_ARRAY('고기능 아이크림', '주름 개선 세럼', '탄력 크림'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'retinol', 'name', '레티놀'),
        JSON_OBJECT('key', 'peptide', 'name', '펩타이드'),
        JSON_OBJECT('key', 'adenosine', 'name', '아데노신')
    ),
    JSON_ARRAY(
        '레티놀 성분은 낮은 농도부터 사용하고 낮에는 자외선 차단제를 함께 사용하는 것이 좋습니다.',
        '민감 피부라면 레티놀 대신 펩타이드나 아데노신 중심 제품을 우선 고려하는 것이 좋습니다.'
    )
);
```

---

## 6.5 이마 - 주름

```sql
INSERT INTO recommendation_rules (
    display_part_name, issue_type, issue_display_name, severity,
    reason_template, recommend_categories, recommend_ingredients, care_tips
) VALUES
(
    '이마', 'wrinkle', '주름', 'normal',
    '이마 주름 상태가 양호하게 분석되었습니다. 보습과 자외선 차단을 통해 현재 상태를 유지하는 것이 좋습니다.',
    JSON_ARRAY('수분 크림', '보습 세럼', '자외선 차단제'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'hyaluronic_acid', 'name', '히알루론산'),
        JSON_OBJECT('key', 'ceramide', 'name', '세라마이드'),
        JSON_OBJECT('key', 'glycerin', 'name', '글리세린')
    ),
    JSON_ARRAY(
        '이마 부위는 건조하면 잔주름이 도드라져 보일 수 있어 보습 관리가 중요합니다.',
        '자외선 차단제를 꾸준히 사용해 피부 노화를 예방하는 것이 좋습니다.'
    )
),
(
    '이마', 'wrinkle', '주름', 'mild',
    '이마에 약한 주름 경향이 보여 예방적인 탄력 관리가 필요합니다.',
    JSON_ARRAY('탄력 크림', '보습 세럼', '주름 예방 세럼'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'peptide', 'name', '펩타이드'),
        JSON_OBJECT('key', 'hyaluronic_acid', 'name', '히알루론산'),
        JSON_OBJECT('key', 'adenosine', 'name', '아데노신')
    ),
    JSON_ARRAY(
        '보습과 탄력 관리를 함께 하면 주름 예방에 도움이 됩니다.',
        '표정 주름이 도드라지는 부위는 자극이 적은 탄력 제품부터 사용하는 것이 좋습니다.'
    )
),
(
    '이마', 'wrinkle', '주름', 'moderate',
    '이마 주름이 보통 이상으로 분석되어 탄력 관리가 필요합니다.',
    JSON_ARRAY('탄력 크림', '주름 개선 세럼', '보습 크림'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'peptide', 'name', '펩타이드'),
        JSON_OBJECT('key', 'adenosine', 'name', '아데노신'),
        JSON_OBJECT('key', 'hyaluronic_acid', 'name', '히알루론산')
    ),
    JSON_ARRAY(
        '이마 주름 관리를 위해 보습과 탄력 관리를 함께 하는 것이 좋습니다.',
        '건조함이 심하면 주름이 더 도드라져 보일 수 있으므로 보습제를 꾸준히 사용하는 것이 좋습니다.'
    )
),
(
    '이마', 'wrinkle', '주름', 'severe',
    '이마 주름 정도가 높게 분석되어 집중적인 탄력 및 주름 개선 관리가 필요합니다.',
    JSON_ARRAY('고기능 탄력 크림', '주름 개선 세럼', '레티놀 크림'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'retinol', 'name', '레티놀'),
        JSON_OBJECT('key', 'peptide', 'name', '펩타이드'),
        JSON_OBJECT('key', 'adenosine', 'name', '아데노신')
    ),
    JSON_ARRAY(
        '주름 개선 성분은 낮은 빈도부터 시작하는 것이 좋습니다.',
        '민감 피부는 레티놀보다 펩타이드 중심 제품부터 사용하는 것이 좋습니다.'
    )
);
```

---

## 6.6 입술 - 건조

```sql
INSERT INTO recommendation_rules (
    display_part_name, issue_type, issue_display_name, severity,
    reason_template, recommend_categories, recommend_ingredients, care_tips
) VALUES
(
    '입술', 'dryness', '건조', 'normal',
    '입술 건조 상태가 양호하게 분석되었습니다. 현재 보습 관리를 유지하는 것이 좋습니다.',
    JSON_ARRAY('데일리 립밤', '보습 립 케어 제품'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'shea_butter', 'name', '시어버터'),
        JSON_OBJECT('key', 'panthenol', 'name', '판테놀'),
        JSON_OBJECT('key', 'ceramide', 'name', '세라마이드')
    ),
    JSON_ARRAY(
        '입술이 건조하지 않아도 수시로 립밤을 사용해 보습을 유지하는 것이 좋습니다.',
        '입술을 자주 핥는 습관은 건조함을 유발할 수 있어 주의하는 것이 좋습니다.'
    )
),
(
    '입술', 'dryness', '건조', 'mild',
    '입술에 약한 건조 경향이 있어 예방적인 보습 관리가 필요합니다.',
    JSON_ARRAY('립밤', '립 마스크', '보습 립 케어 제품'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'shea_butter', 'name', '시어버터'),
        JSON_OBJECT('key', 'panthenol', 'name', '판테놀'),
        JSON_OBJECT('key', 'ceramide', 'name', '세라마이드')
    ),
    JSON_ARRAY(
        '수시로 립밤을 사용해 건조해지기 전에 보습하는 것이 좋습니다.',
        '자기 전에는 립 마스크나 고보습 립 제품을 사용하는 것이 좋습니다.'
    )
),
(
    '입술', 'dryness', '건조', 'moderate',
    '입술 건조도가 보통 이상으로 분석되어 보습 관리가 필요합니다.',
    JSON_ARRAY('립밤', '립 마스크', '고보습 립 케어 제품'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'ceramide', 'name', '세라마이드'),
        JSON_OBJECT('key', 'shea_butter', 'name', '시어버터'),
        JSON_OBJECT('key', 'panthenol', 'name', '판테놀')
    ),
    JSON_ARRAY(
        '수시로 립밤을 사용하고 자기 전에는 고보습 립 제품을 사용하는 것이 좋습니다.',
        '입술 각질을 무리하게 제거하지 않는 것이 좋습니다.'
    )
),
(
    '입술', 'dryness', '건조', 'severe',
    '입술 건조도가 높게 분석되어 집중적인 보습 관리가 필요합니다.',
    JSON_ARRAY('고보습 립밤', '립 마스크', '입술 전용 보습 크림'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'ceramide', 'name', '세라마이드'),
        JSON_OBJECT('key', 'shea_butter', 'name', '시어버터'),
        JSON_OBJECT('key', 'panthenol', 'name', '판테놀')
    ),
    JSON_ARRAY(
        '자기 전 립 마스크나 고보습 립밤을 사용하는 것이 좋습니다.',
        '입술 각질을 뜯거나 강하게 문지르지 않는 것이 좋습니다.'
    )
);
```

---

## 6.7 턱 - 처짐

```sql
INSERT INTO recommendation_rules (
    display_part_name, issue_type, issue_display_name, severity,
    reason_template, recommend_categories, recommend_ingredients, care_tips
) VALUES
(
    '턱', 'sagging', '처짐', 'normal',
    '턱 부위의 탄력 상태가 양호하게 분석되었습니다. 현재 상태를 유지하기 위한 기본 탄력 관리가 적합합니다.',
    JSON_ARRAY('보습 크림', '탄력 크림', '수분 세럼'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'hyaluronic_acid', 'name', '히알루론산'),
        JSON_OBJECT('key', 'peptide', 'name', '펩타이드'),
        JSON_OBJECT('key', 'ceramide', 'name', '세라마이드')
    ),
    JSON_ARRAY(
        '턱 라인은 보습과 탄력 관리를 꾸준히 유지하는 것이 좋습니다.',
        '피부가 건조해지면 탄력이 떨어져 보일 수 있어 보습 관리가 중요합니다.'
    )
),
(
    '턱', 'sagging', '처짐', 'mild',
    '턱 부위에 약한 탄력 저하 경향이 보여 예방적인 탄력 관리가 필요합니다.',
    JSON_ARRAY('탄력 크림', '리프팅 크림', '탄력 세럼'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'peptide', 'name', '펩타이드'),
        JSON_OBJECT('key', 'collagen', 'name', '콜라겐'),
        JSON_OBJECT('key', 'adenosine', 'name', '아데노신')
    ),
    JSON_ARRAY(
        '탄력 저하가 심해지기 전에 보습과 탄력 관리를 함께 하는 것이 좋습니다.',
        '자극이 강한 고기능 제품보다는 저자극 탄력 제품부터 사용하는 것이 좋습니다.'
    )
),
(
    '턱', 'sagging', '처짐', 'moderate',
    '턱 부위의 처짐이 보통 이상으로 분석되어 탄력 관리가 필요합니다.',
    JSON_ARRAY('탄력 크림', '리프팅 크림', '탄력 세럼'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'peptide', 'name', '펩타이드'),
        JSON_OBJECT('key', 'collagen', 'name', '콜라겐'),
        JSON_OBJECT('key', 'adenosine', 'name', '아데노신')
    ),
    JSON_ARRAY(
        '턱 라인에는 탄력 관리 제품을 꾸준히 사용하는 것이 좋습니다.',
        '보습과 탄력 관리를 함께 진행하는 것이 좋습니다.'
    )
),
(
    '턱', 'sagging', '처짐', 'severe',
    '턱 부위의 처짐 정도가 높게 분석되어 집중적인 탄력 및 리프팅 관리가 필요합니다.',
    JSON_ARRAY('고기능 탄력 크림', '리프팅 크림', '탄력 앰플'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'peptide', 'name', '펩타이드'),
        JSON_OBJECT('key', 'collagen', 'name', '콜라겐'),
        JSON_OBJECT('key', 'adenosine', 'name', '아데노신')
    ),
    JSON_ARRAY(
        '턱 라인에는 탄력과 보습을 함께 관리하는 제품을 사용하는 것이 좋습니다.',
        '민감 피부는 고기능 제품을 낮은 빈도부터 사용하는 것이 좋습니다.'
    )
);
```

---

## 6.8 전체 얼굴 - 여드름

```sql
INSERT INTO recommendation_rules (
    display_part_name, issue_type, issue_display_name, severity,
    reason_template, recommend_categories, recommend_ingredients, care_tips
) VALUES
(
    '전체 얼굴', 'acne', '여드름', 'moderate',
    '여드름성 병변이 관찰되어 진정 및 피지 관리가 필요합니다.',
    JSON_ARRAY('진정 토너', '트러블 케어 세럼', '피지 조절 제품'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'bha', 'name', 'BHA'),
        JSON_OBJECT('key', 'niacinamide', 'name', '나이아신아마이드'),
        JSON_OBJECT('key', 'madecassoside', 'name', '마데카소사이드'),
        JSON_OBJECT('key', 'panthenol', 'name', '판테놀')
    ),
    JSON_ARRAY(
        '여드름 부위는 강하게 문지르지 않는 것이 좋습니다.',
        '피지 조절 제품과 진정 제품을 함께 사용하는 것이 좋습니다.',
        '민감 피부라면 BHA 제품은 낮은 빈도부터 사용하는 것이 좋습니다.'
    )
);
```

---

## 6.9 전체 얼굴 - 민감 피부 공통 진정

```sql
INSERT INTO recommendation_rules (
    display_part_name, issue_type, issue_display_name, severity,
    reason_template, recommend_categories, recommend_ingredients, care_tips
) VALUES
(
    '전체 얼굴', 'sensitive', '민감 피부', 'moderate',
    '민감성 피부로 등록되어 자극이 적은 진정 및 장벽 관리가 필요합니다.',
    JSON_ARRAY('진정 크림', '장벽 케어 크림', '저자극 보습 세럼'),
    JSON_ARRAY(
        JSON_OBJECT('key', 'panthenol', 'name', '판테놀'),
        JSON_OBJECT('key', 'ceramide', 'name', '세라마이드'),
        JSON_OBJECT('key', 'madecassoside', 'name', '마데카소사이드'),
        JSON_OBJECT('key', 'allantoin', 'name', '알란토인')
    ),
    JSON_ARRAY(
        '향료와 알코올이 적은 제품을 선택하는 것이 좋습니다.',
        '새로운 기능성 제품은 한 번에 여러 개 사용하지 않는 것이 좋습니다.',
        '피부가 예민할 때는 보습과 진정 중심으로 관리하는 것이 좋습니다.'
    )
);
```

---

# 7. 추천 성분 필터링 예시

## 사용자 프로필 예시

```json
{
  "sensitive": 1,
  "allergy_ingredients": ["retinol", "fragrance"]
}
```

## 추천 규칙 원본

```json
{
  "recommend_ingredients": [
    {
      "key": "retinol",
      "name": "레티놀"
    },
    {
      "key": "peptide",
      "name": "펩타이드"
    },
    {
      "key": "adenosine",
      "name": "아데노신"
    }
  ]
}
```

## 최종 추천 결과

```json
{
  "recommend_ingredients": [
    {
      "key": "peptide",
      "name": "펩타이드"
    },
    {
      "key": "adenosine",
      "name": "아데노신"
    }
  ],
  "excluded_ingredients": [
    {
      "key": "retinol",
      "name": "레티놀"
    }
  ],
  "exclusion_reason": "사용자가 피해야 할 성분으로 등록한 레티놀은 추천 성분에서 제외했습니다."
}
```

---

# 8. 추천 API 응답 예시

정상 상태 사용자에게도 유지 관리 추천을 반환한다.

```json
{
  "session_id": 1,
  "recommendations": [
    {
      "display_part_name": "볼",
      "issue_type": "pore",
      "issue_display_name": "모공",
      "severity": "normal",
      "reason": "볼 부위의 모공 상태가 양호하게 분석되었습니다. 현재 상태를 유지하기 위한 기본 관리가 적합합니다.",
      "recommend_categories": ["수분 토너", "가벼운 보습 크림", "저자극 클렌저"],
      "recommend_ingredients": [
        {
          "key": "hyaluronic_acid",
          "name": "히알루론산"
        },
        {
          "key": "ceramide",
          "name": "세라마이드"
        },
        {
          "key": "glycerin",
          "name": "글리세린"
        }
      ],
      "excluded_ingredients": [],
      "exclusion_reason": null,
      "care_tips": [
        "현재 모공 상태를 유지하기 위해 과도한 각질 제거는 피하는 것이 좋습니다.",
        "세안 후 가벼운 보습제를 사용해 피부 밸런스를 유지하는 것이 좋습니다."
      ]
    }
  ]
}
```
