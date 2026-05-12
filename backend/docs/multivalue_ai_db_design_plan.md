# MultiValue AI 응답 DB 저장 구조 설계

작성일: 2026-05-12  
대상 서버: `backend/scripts/multivalue_ai_server.py`  
대상 모델: `skin_dinov3_multivalue` (EndToEndInferencer + MultiTaskSkinModel)

---

## 1. 현재 MultiValue AI 응답 구조 분석

### 1.1 최상위 응답

```json
{
  "model_name": "skin_dinov3_multivalue",
  "model_version": "0.1.0",
  "parts": [ /* facepart 0~8, 총 9개 객체 */ ],
  "detected_parts": [
    {
      "raw_part_name": "left_eye",
      "class_name": "l_eye",
      "confidence": 0.803,
      "bbox_xyxy": [196.07, 1420.30, 411.79, 1843.80]
    }
    /* YOLO가 검출한 파트만 포함, 최대 8개 */
  ]
}
```

### 1.2 parts[] 내 단일 파트 객체

각 파트는 `info / images / annotations / equipment` 4개 섹션을 가진다.

```json
{
  "info": {
    "filename": "uploaded.jpg",
    "id": "0000",
    "gender": "U",
    "age": 30,
    "date": "2024-01-01",
    "skin_type": 0,
    "sensitive": 0
  },
  "images": {
    "device": 0,
    "width": 1920,
    "height": 1080,
    "angle": 0,
    "facepart": 3,
    "bbox": [196, 1420, 411, 1843]
  },
  "annotations": {
    "l_perocular_wrinkle": 2
  },
  "equipment": {
    "l_perocular_wrinkle_Ra": 0.312,
    "l_perocular_wrinkle_Rmax": 1.804,
    "l_perocular_wrinkle_Rt": 1.982,
    "l_perocular_wrinkle_Rz=Rtm": 1.654,
    "l_perocular_wrinkle_Rp": 0.918,
    "l_perocular_wrinkle_Rv": 0.864,
    "l_perocular_wrinkle_Rq": 0.388,
    "l_perocular_wrinkle_R3z": 1.543
  }
}
```

### 1.3 facepart별 annotations/equipment 전체 목록

| facepart | raw_part_name | annotations 키 | equipment 키 | 비고 |
|----------|--------------|---------------|-------------|------|
| 0 | (full face) | `acne: null` | `pigmentation_count`, `acne_count` | annotations는 항상 null → 저장 제외 |
| 1 | forehead | `forehead_pigmentation`, `forehead_wrinkle` | `forehead_moisture`, `forehead_elasticity_R0~R9` (10개), `forehead_elasticity_Q0~Q3` (4개) | 총 equipment 15개 |
| 2 | glabella | `glabellus_wrinkle` | `null` | equipment 없음 |
| 3 | left_eye | `l_perocular_wrinkle` | `Ra, Rmax, Rt, Rz=Rtm, Rp, Rv, Rq, R3z` 접두사 8개 | 거칠기 측정값 |
| 4 | right_eye | `r_perocular_wrinkle` | 동일 8개 (r_ 접두사) | |
| 5 | left_cheek | `l_cheek_pore`, `l_cheek_pigmentation` | `l_cheek_moisture`, `l_cheek_elasticity_R0~R9` (10개), `l_cheek_elasticity_Q0~Q3` (4개), `l_cheek_pore` (count) | 총 16개 |
| 6 | right_cheek | `r_cheek_pore`, `r_cheek_pigmentation` | 동일 16개 (r_ 접두사) | |
| 7 | lips | `lip_dryness` | `null` | equipment 없음 |
| 8 | chin | `chin_sagging` | `chin_moisture` (더미), `chin_elasticity_R0~R9` (10개), `chin_elasticity_Q0~Q3` (4개) | `chin_moisture`는 라벨 미학습 → 항상 0.0 더미 |

**세션당 예상 row 수:**
- annotations → skin_part_results: 약 11개
- equipment → skin_metric_values: 약 80개 (더미 포함)
- detected_parts → skin_part_detections: 최대 8개
- 원본 JSON → ai_raw_responses: 1개

---

## 2. 기존 flat PartResult와의 차이

### 2.1 기존 구조 (dummy_ai_server 기준)

`InferenceResult.parts[]`는 파트당 1 row였고 내용이 단순했다:

```
raw_part_name | metric_name | grade_value | severity | confidence_score
left_eye      | wrinkle     | 3           | severe   | 0.88
```

### 2.2 multivalue 구조와의 차이

| 구분 | 기존 (flat) | multivalue |
|------|------------|------------|
| 파트당 row 수 | 1 | annotations 키 수만큼 (1~2개) |
| 등급값 출처 | 단일 inference score | `annotations.*` (전문가 라벨 기반 ordinal 예측) |
| 상세 측정값 | 없음 | `equipment.*` (moisture, elasticity Ri/Qi, roughness Ra/Rmax 등) |
| bbox | 응답에 포함되지 않음 (또는 extra field) | `images.bbox` + `detected_parts[].bbox_xyxy` |
| 사용자 정보 | 없음 | `info.*` (더미값, 사용 안 함) |
| 원본 JSON | 없음 | 전체 응답 보존 필요 |

---

## 3. 더미 필드 필터링 기준

### 3.1 저장하지 않을 항목

| 필드 | 이유 |
|------|------|
| `info.gender`, `info.age`, `info.skin_type`, `info.sensitive` | 서버 코드에 `_DUMMY_INFO`로 하드코딩, 실제 사용자 값 아님 |
| `info.filename`, `info.id`, `info.date` | 메타데이터. `uploaded_images.original_filename`으로 대체 |
| `part0.annotations.acne` | 항상 `null` |

### 3.2 더미 값이지만 row를 남기는 항목 (`is_dummy=true`)

| 필드 | 더미 이유 | dummy_reason 값 |
|------|----------|----------------|
| `chin_moisture` (part8.equipment) | LABEL_REGISTRY에 chin moisture 라벨 없음, 코드에서 명시적으로 `_DUMMY_FLOAT=0.0` 할당 | `"label_not_trained"` |
| YOLO 미검출 파트의 `images.bbox` | `[0, 0, W, H]` (전체 이미지)로 폴백 | bbox_source로 구분 (`"full_image_fallback"`) |
| `results.get(key)` 가 None인 경우 | 모델 출력에 해당 라벨 없음 | `"model_output_missing"` |

### 3.3 더미 구분을 위한 source/is_dummy 규칙

```
source 값:
  "model"              → 모델이 실제 예측한 값
  "dummy_fallback"     → 코드에서 _DUMMY_FLOAT/GRADE로 채운 값
  "bbox_fallback"      → YOLO 미검출로 전체 이미지 bbox 사용

is_dummy 값:
  false  → 실제 모델 출력
  true   → 위 더미 케이스 중 하나
```

---

## 4. annotations / equipment / detected_parts 저장 분리 기준

```
AI 응답 필드                    →  저장 대상 테이블
─────────────────────────────────────────────────────────
parts[*].annotations.*         →  skin_part_results       (등급·이슈·severity)
parts[*].equipment.*           →  skin_metric_values      (상세 측정값)
parts[*].images.bbox           →  skin_part_detections    (이미지 crop bbox)
detected_parts[*].bbox_xyxy    →  skin_part_detections    (YOLO 검출 bbox)
전체 응답 JSON                  →  ai_raw_responses        (원본 보존)
info.*/parts[*].images.device  →  정규화 저장 안 함
info.gender/age/skin_type      →  정규화 저장 안 함, user_profiles 업데이트에 사용하지 않음
```

### 4.1 Phase 1 구현 기준 — 전체 보존

AI 응답 원본 JSON은 `ai_raw_responses.raw_json`에 전체 저장한다. 원본 JSON은 절대 버리지 않는다.

이유:

- 파서 로직 변경 시 재파싱 가능
- 모델 버전 변경 후 결과 비교 가능
- 디버깅 가능
- 지금 사용하지 않는 값도 나중에 의미가 생길 수 있음

### 4.2 Phase 1 구현 기준 — 정규화 저장

정규화 저장은 의미 있는 값만 역할별로 분리한다.

| 값 | 저장 대상 | 기준 |
|----|----------|------|
| AI 응답 전체 | `ai_raw_responses.raw_json` | 전체 보존 |
| `parts[*].annotations.*` | `skin_part_results` | `null`이 아닌 등급값만 저장 |
| `parts[*].equipment.*` | `skin_metric_values` | numeric 값만 저장 |
| `parts[*].images.bbox` | `skin_part_detections` | YOLO 미검출 fallback bbox로 저장 |
| `detected_parts[*].bbox_xyxy / confidence` | `skin_part_detections` | YOLO 검출 bbox로 저장 |
| `model_name / model_version` | `ai_raw_responses`, `skin_part_results` | 원본 모델 추적 가능하게 유지 |

### 4.3 Phase 1 구현 기준 — 정규화 저장하지 않는 값

아래 값은 `raw_json`에는 남기지만 정규화 테이블에는 저장하지 않는다.

- `info.id`
- `info.gender`
- `info.age`
- `info.date`
- `info.skin_type`
- `info.sensitive`
- `images.device`
- `images.angle`

현재 `example_response.json` 기준으로 모든 part에 반복되는 기본값이며, 실제 사용자 프로필 값으로 보기 어렵기 때문이다.

`info.skin_type` / `info.sensitive`는 `user_profiles` 업데이트에 사용하지 않는다. skin type / sensitive가 실제 AI 예측값이라면 `parts[*].info`가 아니라 top-level `profile_prediction` 같은 명시적 필드로 분리하는 방향을 권장한다.

### 4.4 Phase 1 구현 기준 — 조건부 처리 값

| 값 | 처리 |
|----|------|
| `part0.annotations.acne = null` | 저장 제외 |
| `chin_moisture = 0.0` | `skin_metric_values`에 저장, `is_dummy=true`, `dummy_reason="label_not_trained"`, `source="dummy_fallback"` |
| `equipment = null` | 저장 제외 |
| equipment key는 있지만 value가 `null` | Phase 1-2 parser에서는 저장 제외 |
| YOLO 미검출로 `parts[*].images.bbox`를 사용하는 경우 | `skin_part_detections`에 저장, `bbox_source="full_image_fallback"` |
| facepart 0 full face bbox | detections 정규화 저장 제외, `raw_json`에만 보존 |

---

## 5. 신규 테이블 정의

### 5.1 `ai_raw_responses`

AI 서버 전체 응답을 저장한다. 디버깅·재파싱·모델 교체 시 재처리에 사용한다.

```sql
CREATE TABLE ai_raw_responses (
    id              BIGINT       PRIMARY KEY AUTO_INCREMENT,
    session_id      BIGINT       NOT NULL REFERENCES analysis_sessions(id) ON DELETE CASCADE,
    image_id        BIGINT       NULL     REFERENCES uploaded_images(id) ON DELETE SET NULL,
    user_id         BIGINT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    model_name      VARCHAR(100) NOT NULL,
    model_version   VARCHAR(100) NOT NULL,
    server_type     VARCHAR(50)  NOT NULL,   -- "dummy" | "multivalue" | "remote"
    raw_json        JSON         NOT NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ai_raw_responses_session (session_id),
    INDEX idx_ai_raw_responses_user    (user_id)
);
```

### 5.2 `skin_part_detections`

YOLO bbox 검출 결과와 crop bbox를 저장한다.  
`bbox_source`로 YOLO 직접 검출(`"yolo"`)인지 폴백(`"full_image_fallback"`)인지 구분한다.

```sql
CREATE TABLE skin_part_detections (
    id                   BIGINT        PRIMARY KEY AUTO_INCREMENT,
    session_id           BIGINT        NOT NULL REFERENCES analysis_sessions(id) ON DELETE CASCADE,
    image_id             BIGINT        NULL     REFERENCES uploaded_images(id) ON DELETE SET NULL,
    user_id              BIGINT        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    raw_part_name        VARCHAR(50)   NOT NULL,   -- "left_eye", "forehead" 등
    class_name           VARCHAR(50)   NULL,        -- YOLO 클래스명 ("l_eye")
    facepart             TINYINT       NOT NULL,    -- 0~8
    bbox_x1              FLOAT         NOT NULL,
    bbox_y1              FLOAT         NOT NULL,
    bbox_x2              FLOAT         NOT NULL,
    bbox_y2              FLOAT         NOT NULL,
    bbox_source          VARCHAR(30)   NOT NULL,    -- "yolo" | "full_image_fallback"
    detection_confidence FLOAT         NULL,        -- YOLO confidence, NULL이면 fallback
    created_at           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_skin_part_detections_session (session_id),
    INDEX idx_skin_part_detections_part    (raw_part_name)
);
```

### 5.3 `skin_metric_values`

`equipment.*` 상세 측정값을 row 단위로 저장한다.  
파트당 최대 16개, 세션당 약 80개 row.

```sql
CREATE TABLE skin_metric_values (
    id               BIGINT        PRIMARY KEY AUTO_INCREMENT,
    session_id       BIGINT        NOT NULL REFERENCES analysis_sessions(id) ON DELETE CASCADE,
    image_id         BIGINT        NULL     REFERENCES uploaded_images(id) ON DELETE SET NULL,
    user_id          BIGINT        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    part_result_id   BIGINT        NULL     REFERENCES skin_part_results(id) ON DELETE SET NULL,
    raw_part_name    VARCHAR(50)   NOT NULL,    -- "left_cheek", "forehead" 등
    display_part_name VARCHAR(50)  NOT NULL,
    facepart         TINYINT       NOT NULL,    -- 0~8
    metric_group     VARCHAR(50)   NOT NULL,    -- 큰 지표 그룹. "moisture" | "elasticity" | "wrinkle" | "pore" | "pigmentation" | "acne"
    metric_name      VARCHAR(100)  NOT NULL,    -- 그룹 내 세부 지표. "moisture" | "R0" | "R2" | "Q0" | "Ra" | "Rmax" | "Rt" | "pore_count" 등
    metric_key       VARCHAR(100)  NOT NULL,    -- AI 응답 원본 key. 예: "forehead_elasticity_R0", "l_perocular_wrinkle_Ra"
    value            DOUBLE        NOT NULL,
    value_type       VARCHAR(20)   NOT NULL,    -- "reg" | "count" | "ordinal"
    unit             VARCHAR(20)   NULL,        -- 측정 단위 (µm, % 등). 현재는 NULL
    is_dummy         BOOLEAN       NOT NULL DEFAULT FALSE,
    dummy_reason     VARCHAR(100)  NULL,        -- "label_not_trained" | "model_output_missing" 등
    source           VARCHAR(30)   NOT NULL,    -- "model" | "dummy_fallback"
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_skin_metric_values_session     (session_id),
    INDEX idx_skin_metric_values_part        (raw_part_name),
    INDEX idx_skin_metric_values_metric_group (metric_group),
    INDEX idx_skin_metric_values_is_dummy    (is_dummy)
);
```

#### metric_group / metric_name / metric_key 역할 구분

세 컬럼은 같은 측정값을 서로 다른 해상도로 표현한다.

| 컬럼 | 역할 | 값 예시 |
|------|------|--------|
| `metric_group` | **큰 지표 그룹** — 그룹 단위 조회·비교·추천 기준으로 사용 | `moisture`, `elasticity`, `wrinkle`, `pore`, `pigmentation`, `acne` |
| `metric_name` | **세부 지표명** — 그룹 안에서 어떤 측정 파라미터인지 구분 | `moisture`, `R0`, `R2`, `Q0`, `Ra`, `Rmax`, `Rt`, `pore_count`, `pigmentation_count` |
| `metric_key` | **원본 key** — AI 응답 또는 파서 로직에서 사용한 실제 key | `forehead_moisture`, `forehead_elasticity_R2`, `l_perocular_wrinkle_Ra` |

**metric_group을 세분화하지 않는 이유**

`metric_group`에 `R2`, `Ra` 같은 세부 파라미터명을 섞어 넣으면 그룹 단위 조회가 불가능해진다.

```sql
-- 모든 탄력 지표 조회: metric_group='elasticity' 하나로 가능해야 함
SELECT * FROM skin_metric_values
WHERE session_id = 1 AND metric_group = 'elasticity';

-- 모든 눈가 주름 roughness 지표 조회: metric_group='wrinkle' 하나로 가능해야 함
SELECT * FROM skin_metric_values
WHERE session_id = 1 AND raw_part_name = 'left_eye' AND metric_group = 'wrinkle';
```

`metric_group`이 `"elasticity_R2"`처럼 세분화되어 있으면 위 쿼리를 LIKE 패턴으로 우회해야 하고, 추후 프론트 표시 기준이나 추천 임계값 설정도 어려워진다.

#### 저장 예시

**예시 1. 이마 수분**

| 컬럼 | 값 |
|------|----|
| `raw_part_name` | `forehead` |
| `metric_group` | `moisture` |
| `metric_name` | `moisture` |
| `metric_key` | `forehead_moisture` |
| `value` | `59.97` |

**예시 2. 이마 탄력 R2**

| 컬럼 | 값 |
|------|----|
| `raw_part_name` | `forehead` |
| `metric_group` | `elasticity` |
| `metric_name` | `R2` |
| `metric_key` | `forehead_elasticity_R2` |
| `value` | `0.553` |

**예시 3. 왼쪽 눈가 주름 Ra**

| 컬럼 | 값 |
|------|----|
| `raw_part_name` | `left_eye` |
| `metric_group` | `wrinkle` |
| `metric_name` | `Ra` |
| `metric_key` | `l_perocular_wrinkle_Ra` |
| `value` | `17.56` |

**예시 4. 왼쪽 볼 모공 개수**

| 컬럼 | 값 |
|------|----|
| `raw_part_name` | `left_cheek` |
| `metric_group` | `pore` |
| `metric_name` | `pore_count` |
| `metric_key` | `l_cheek_pore` |
| `value` | `753.0` |

**예시 5. 전체 얼굴 색소침착 개수**

| 컬럼 | 값 |
|------|----|
| `raw_part_name` | `full_face` |
| `metric_group` | `pigmentation` |
| `metric_name` | `pigmentation_count` |
| `metric_key` | `pigmentation_count` |
| `value` | `146.0` |

#### metric별 해석 방향 주의사항

상세 측정값은 지표마다 해석 방향이 다르다. "값이 높으면 나쁨" 또는 "값이 낮으면 나쁨" 같은 공통 임계값 규칙을 전체 지표에 적용하면 안 된다.

| metric_group | metric_name | 해석 방향 | 위험 신호 |
|-------------|-------------|---------|---------|
| `moisture` | `moisture` | 낮을수록 건조 | 낮은 값 (`low_is_bad`) |
| `wrinkle` | `Ra`, `Rmax`, `Rt`, `Rz`, `Rp`, `Rv`, `Rq`, `R3z` | 높을수록 거칠기·주름 심화 | 높은 값 (`high_is_bad`) |
| `pore` | `pore_count` | 높을수록 모공 증가 | 높은 값 (`high_is_bad`) |
| `elasticity` | `R2`, `R7` | 낮을수록 탄력 저하 (업계 통용) | 낮은 값 (`low_is_bad`) |
| `elasticity` | `R0`~`R9`, `Q0`~`Q3` | **지표별 별도 해석 필요** | `metric_specific` |
| `pigmentation` | `pigmentation_count` | 높을수록 색소침착 증가 | 높은 값 (`high_is_bad`) |
| `acne` | `acne_count` | 높을수록 여드름 증가 | 높은 값 (`high_is_bad`) |

`metric_specific` 지표는 임계값 확정 전에 추천에 직접 연결하지 않는다.  
임계값은 임상 데이터 분석 후 `metric_threshold_rules` 테이블(→ 7.4절)에 등록한다.

---

## 6. 기존 `skin_part_results` 유지 범위

### 유지

- 테이블 스키마 변경 없이 그대로 사용한다.
- `annotations.*` 키별로 1 row씩 저장한다.
- `grade_value`, `severity`, `issue_type`, `confidence_score` 중심 유지.

### annotations → skin_part_results 매핑

| annotations 키 | raw_part_name | metric_name | issue_type | severity 변환 기준 |
|---------------|--------------|------------|-----------|----------------|
| `forehead_pigmentation` | forehead | pigmentation | pigmentation | 0→normal, 1→mild, 2→moderate, 3→severe |
| `forehead_wrinkle` | forehead | wrinkle | wrinkle | 0→normal, 1~2→mild, 3→moderate, 4→severe |
| `glabellus_wrinkle` | glabella | wrinkle | wrinkle | 0→normal, 1→mild, 2→severe |
| `l_perocular_wrinkle` | left_eye | wrinkle | wrinkle | 0→normal, 1~2→mild, 3~4→moderate, 5→severe |
| `r_perocular_wrinkle` | right_eye | wrinkle | wrinkle | 동일 |
| `l_cheek_pore` | left_cheek | pore | pore | 0→normal, 1~2→mild, 3~4→moderate, 5→severe |
| `l_cheek_pigmentation` | left_cheek | pigmentation | pigmentation | 동일 |
| `r_cheek_pore` | right_cheek | pore | pore | 동일 |
| `r_cheek_pigmentation` | right_cheek | pigmentation | pigmentation | 동일 |
| `lip_dryness` | lips | dryness | dryness | 0→normal, 1~2→mild, 3→moderate, 4→severe |
| `chin_sagging` | chin | sagging | sagging | 0→normal, 1~2→mild, 3~4→moderate, 5→severe |

> part0 (`acne: null`)은 저장하지 않는다.

### 추가 컬럼 없이 처리 가능한 이유

- `grade_value`는 annotations의 정수값 그대로.
- `severity`는 위 grade → severity 매핑 함수로 파생.
- `confidence_score`는 multivalue 모델에서 별도 제공하지 않으므로 `null` 저장.
- `predicted_value`도 `null` (annotations는 등급값만 제공).

---

## 7. 추천 로직 유지·확장 방향

### 7.1 현재 추천 구조 — DB seed rule 기반

현재 추천은 **AI가 성분을 직접 생성하는 방식이 아니다**.  
DB에 seed로 입력된 rule 테이블을 조회해 추천 결과를 만드는 **rule-based 추천**이다.

**사용 테이블**

| 테이블 | 역할 |
|--------|------|
| `recommendation_rules` | `display_part_name + issue_type + severity` 조합에 대한 추천 rule |
| `ingredient_rules` | 성분별 주의·금지 조건 (allergy, sensitive 기준) |
| `part_recommendations` | 최종 추천 결과 저장 |
| `user_profiles` | allergy_ingredients, sensitive 필터링 기준 |

**현재 추천 흐름**

```
1. skin_part_results에서 display_part_name / issue_type / severity 확인
2. recommendation_rules에서 정확히 일치하는 rule 조회
3. rule에 저장된 recommend_categories / recommend_ingredients / care_tips 사용
4. user_profiles.allergy_ingredients 와 sensitive 기준으로 제외 성분 필터링
5. part_recommendations에 최종 추천 결과 저장
```

이 흐름은 multivalue 도입 후에도 **변경하지 않는다**.  
multivalue의 `annotations.*` 값이 `skin_part_results`에 severity로 저장되므로 기존 recommendation_service는 그대로 동작한다.

### 7.2 skin_metric_values의 추천 역할 — 보조 신호

`skin_metric_values`는 **새로운 추천 성분을 AI가 만들어내기 위한 데이터가 아니다**.  
기존 `recommendation_rules` 결과를 더 세밀하게 **조정·보정**하기 위한 보조 신호다.

```
기존 rule → recommend_ingredients / care_tips 결정
                ↓
skin_metric_values → 기존 결과 유지한 채로 보정만 수행
  - 성분 우선순위 조정
  - 보조 성분 후보 추가
  - care_tips 문구 추가
                ↓
allergy / sensitive 필터링 (항상 마지막)
                ↓
part_recommendations 저장
```

### 7.3 추천 고도화 3단계 구조

| 단계 | 기준 | 동작 | 상태 |
|------|------|------|------|
| **1단계** 기본 추천 | `skin_part_results.issue_type + severity` | 기존 `recommendation_rules` 조회. 현재 운영 로직 유지 | **현재 구현** |
| **2단계** 측정값 기반 보정 | `skin_metric_values` 값 확인 | 기존 추천 결과 유지한 상태에서: 성분 우선순위 조정 / 보조 성분 후보 추가 / care_tips 문구 추가 | Phase 2 구현 예정 |
| **3단계** 제품 추천 확장 | `products` 테이블 | 성분 기반 제품 랭킹으로 확장 (현재는 카테고리·성분·관리팁 추천 중심) | 현재 미구현 |

### 7.4 추천 생성 순서 (필터링 포함)

상세 측정값 기반 보정을 추가하더라도 **알러지·민감 피부 필터링은 반드시 마지막에 적용**한다.

```
1. skin_part_results 기반 기본 rule 조회
2. recommendation_rules 결과 생성
   → recommend_categories / recommend_ingredients / care_tips 확정
3. skin_metric_values 기반 보정 rule 적용 (Phase 2~)
   → 추천 성분 우선순위 조정
   → 보조 성분 후보 추가
   → care_tips 문구 추가
4. user_profiles.allergy_ingredients 제외
5. user_profiles.sensitive == 1이면 caution_for_sensitive 성분 제외
6. part_recommendations 저장
```

### 7.5 seed rule 보정 예시

**예시 1. 모공**

```
기본 rule:
  display_part_name = 볼,  issue_type = pore,  severity = moderate

기존 recommendation_rules 결과:
  recommend_ingredients: [niacinamide, bha, zinc_pca]
  care_tips: "모공과 피지 관리를 꾸준히 하세요."

상세 측정값:
  metric_group = pore,  metric_name = pore_count,  value = 753
  direction = high_is_bad  (→ 임계값 초과)

보정:
  bha, zinc_pca 우선순위 상승 (앞으로 이동)
  care_tips에 "피지와 모공 관리를 함께 진행하세요." 추가
```

**예시 2. 수분**

```
기본 rule:
  issue_type = dryness,  severity = mild

기존 recommendation_rules 결과:
  recommend_ingredients: [hyaluronic_acid, glycerin]

상세 측정값:
  metric_group = moisture,  value = 31.2
  direction = low_is_bad  (→ 임계값 하회)

보정:
  ceramide, panthenol을 보조 성분 후보로 추가
  care_tips에 "보습 후 장벽 케어 제품을 함께 사용하세요." 추가
```

**예시 3. 주름**

```
기본 rule:
  issue_type = wrinkle,  severity = moderate

기존 recommendation_rules 결과:
  recommend_ingredients: [retinol, adenosine, peptide]

상세 측정값:
  metric_group = wrinkle,  metric_name = Ra / Rmax / Rt,  value 높음
  direction = high_is_bad  (→ 임계값 초과)

보정:
  peptide / adenosine 관련 care_tips 문구 추가
  민감 피부인 경우 retinol은 ingredient_rules 기준으로 4단계에서 제외될 수 있음
```

### 7.6 `metric_recommendation_boost_rules` 테이블 (Phase 2 신규)

기존 `recommendation_rules`를 직접 수정하지 않고, 측정값 기반 보정 rule을 별도 테이블로 관리한다.  
이 테이블은 기존 추천 결과를 **대체하지 않고 보정만** 수행한다.

```sql
CREATE TABLE metric_recommendation_boost_rules (
    id               BIGINT        PRIMARY KEY AUTO_INCREMENT,
    metric_group     VARCHAR(50)   NOT NULL,
    metric_name      VARCHAR(100)  NOT NULL,
    raw_part_name    VARCHAR(50)   NULL,         -- NULL이면 전체 파트에 적용
    direction        VARCHAR(30)   NOT NULL,     -- "low_is_bad" | "high_is_bad"
    threshold_min    DOUBLE        NULL,
    threshold_max    DOUBLE        NULL,
    boost_ingredients  JSON        NULL,         -- 우선순위 상승 성분 목록
    add_ingredients    JSON        NULL,         -- 보조 성분 후보 추가 목록
    add_categories     JSON        NULL,         -- 보조 카테고리 추가 목록
    add_care_tips      TEXT        NULL,         -- 추가할 care_tips 문구
    priority         INT           NOT NULL DEFAULT 0,
    is_active        BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_boost_rules_metric (metric_group, metric_name),
    INDEX idx_boost_rules_part   (raw_part_name)
);
```

**테이블 역할 분리**

| 테이블 | 역할 |
|--------|------|
| `recommendation_rules` | issue_type + severity 기반 기본 추천 (seed rule, 현재 운영) |
| `metric_recommendation_boost_rules` | 상세 측정값 기반 보정 rule (Phase 2, 기존 결과 유지·보정만 수행) |

### 7.7 `metric_threshold_rules` 테이블 (Phase 2 신규)

equipment 측정값의 임계값을 코드 밖에서 관리하기 위한 테이블.  
임상 데이터 분석 완료 후 이 테이블에 값을 등록하면 보정 서비스가 자동으로 반영한다.

```sql
CREATE TABLE metric_threshold_rules (
    id                 BIGINT       PRIMARY KEY AUTO_INCREMENT,
    raw_part_name      VARCHAR(50)  NOT NULL,
    metric_group       VARCHAR(50)  NOT NULL,
    metric_name        VARCHAR(100) NOT NULL,
    direction          VARCHAR(30)  NOT NULL,   -- "low_is_bad" | "high_is_bad" | "metric_specific"
    mild_threshold     DOUBLE       NULL,
    moderate_threshold DOUBLE       NULL,
    severe_threshold   DOUBLE       NULL,
    description        VARCHAR(255) NULL,
    is_active          BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_metric_threshold_rules_part_group (raw_part_name, metric_group)
);
```

**임계값 등록 예시 (미확정, 참고용)**

| raw_part_name | metric_group | metric_name | direction | mild_threshold | moderate_threshold |
|--------------|-------------|------------|----------|---------------|------------------|
| `forehead` | `moisture` | `moisture` | `low_is_bad` | 50.0 | 35.0 |
| `left_cheek` | `moisture` | `moisture` | `low_is_bad` | 50.0 | 35.0 |
| `left_eye` | `wrinkle` | `Ra` | `high_is_bad` | 15.0 | 25.0 |
| `left_cheek` | `pore` | `pore_count` | `high_is_bad` | 500.0 | 800.0 |
| `left_cheek` | `elasticity` | `R2` | `low_is_bad` | 0.5 | 0.35 |

> 두 테이블 모두 Phase 2에서 migration으로 추가하며, 초기값은 임상 데이터 분석 후 INSERT한다. Phase 1 migration에는 포함하지 않는다.

---

## 8. Migration 필요 여부

### 기존 테이블

| 테이블 | 변경 필요 여부 | 내용 |
|--------|-------------|------|
| `analysis_sessions` | 없음 | 그대로 사용 |
| `uploaded_images` | 없음 | 그대로 사용 |
| `skin_part_results` | 없음 | 스키마 변경 없이 annotations 저장 |
| `skin_json_records` | 없음 | 기존 AI-Hub JSON 파이프라인용, 그대로 유지 |
| `user_profiles` | 없음 | AI info 대신 여기서 사용자 정보 읽음 |

### 신규 테이블 (새 migration 1개 추가)

```
0007_create_multivalue_ai_tables.py
  - CREATE TABLE ai_raw_responses
  - CREATE TABLE skin_part_detections
  - CREATE TABLE skin_metric_values
```

---

## 9. 단계별 구현 계획

### Phase 1 — 저장 구조 완료 (2026-05-12)

**목표**: multivalue AI 응답을 DB에 저장하는 전체 파이프라인 구현

> **Phase 1-1 완료**: migration 0007 적용, ORM 모델 3개 추가, alembic upgrade head 성공.  
> **Phase 1-2 parser 완료**: `app/services/multivalue_parser.py` 작성, parser 단위 테스트 9개 통과.  
> **Phase 1-3 DB 저장 연결 완료**: `image_service.py`에 `AI_INFERENCE_MODE=multivalue` 분기 추가, 4개 테이블 저장 연결, 통합 테스트 6개 통과.

1. Alembic migration `0007_create_multivalue_ai_tables.py` 작성 및 적용
   - `ai_raw_responses`, `skin_part_detections`, `skin_metric_values` 3개 테이블 생성
2. ORM 모델 파일 추가:
   - `app/models/ai_raw_response.py`
   - `app/models/skin_part_detection.py`
   - `app/models/skin_metric_value.py`
3. `app/services/multivalue_parser.py` 작성 ✅ Phase 1-2 완료
   - `parse_annotations(parts)` → `List[SkinPartResult]`
   - `parse_equipment(parts)` → `List[SkinMetricValue]` (metric_key 파싱 규칙 적용)
   - `parse_detections(detected_parts, parts)` → `List[SkinPartDetection]`
   - 더미 판별 로직 (`is_dummy`, `dummy_reason`, `source` 자동 설정)
   - grade → severity 변환 함수

   `parse_equipment` 구현 시 `metric_key`를 파싱해 `metric_group`과 `metric_name`을 분리한다.  
   equipment 응답 key 구조는 `{부위}_{그룹}_{세부파라미터}` 패턴이며, 아래 규칙을 적용한다.

   | equipment key 패턴 | metric_group | metric_name | 비고 |
   |--------------------|-------------|-------------|------|
   | `forehead_moisture` | `moisture` | `moisture` | 수분 |
   | `l_cheek_moisture`, `r_cheek_moisture` | `moisture` | `moisture` | |
   | `forehead_elasticity_R0` ~ `R9` | `elasticity` | `R0` ~ `R9` | 탄력 R파라미터 |
   | `forehead_elasticity_Q0` ~ `Q3` | `elasticity` | `Q0` ~ `Q3` | 탄력 Q파라미터 |
   | `l_cheek_elasticity_R*`, `r_cheek_elasticity_R*` | `elasticity` | `R0` ~ `R9` | |
   | `chin_elasticity_R*`, `chin_elasticity_Q*` | `elasticity` | `R*` / `Q*` | |
   | `l_perocular_wrinkle_Ra`, `_Rmax`, `_Rt`, `_Rz=Rtm`, `_Rp`, `_Rv`, `_Rq`, `_R3z` | `wrinkle` | `Ra`, `Rmax`, `Rt`, `Rz`, `Rp`, `Rv`, `Rq`, `R3z` | 눈가 거칠기 |
   | `r_perocular_wrinkle_*` | `wrinkle` | 동일 | |
   | `l_cheek_pore` (count) | `pore` | `pore_count` | |
   | `r_cheek_pore` (count) | `pore` | `pore_count` | |
   | `pigmentation_count` | `pigmentation` | `pigmentation_count` | part0 equipment |
   | `acne_count` | `acne` | `acne_count` | part0 equipment |
   | `chin_moisture` | `moisture` | `moisture` | is_dummy=True |

   구현 상태:
   - `parse_multivalue_response(payload, session_id, user_id, image_id=None)`는 `AiRawResponse`, `SkinPartResult`, `SkinMetricValue`, `SkinPartDetection` ORM 객체를 생성해 dict로 반환한다.
   - DB session add/commit은 수행하지 않는다.
   - `part0.annotations.acne = null`은 저장 제외한다.
   - unknown annotation/equipment key, invalid bbox, non-numeric equipment value는 warning log 후 skip한다.
   - `l_perocular_wrinkle_Rz=Rtm`은 원본 `metric_key`를 유지하고 `metric_name="Rz"`로 정규화한다.
   - facepart 0 full face bbox는 detections 저장 제외하고 `raw_json`에만 보존한다.
   - `chin_moisture`는 항상 dummy row로 저장용 객체를 만든다.

4. `app/schemas/image_upload.py` — `PartResult.confidence_score`를 `Optional[float] = None`으로 변경 ✅ Phase 1-3 완료
   - multivalue annotations는 confidence score를 별도 제공하지 않음
   - 기존 mock/remote 흐름은 float 값을 그대로 전달하므로 backwards compatible
5. `image_service.py`에 `AI_INFERENCE_MODE=multivalue` 분기 추가 ✅ Phase 1-3 완료
   - `_run_multivalue_mode()`: multivalue_parser 호출 → ai_raw_responses / skin_part_results / skin_metric_values / skin_part_detections 저장 → recommendation_service 호출
   - `_run_flat_mode()`: 기존 mock/remote 저장 로직 (변경 없음)
   - `inference_service.run_multivalue_inference()`: 원본 dict 반환 (InferenceResult 변환 없음)
   - `app/core/config.py` — `AI_MULTIVALUE_INFERENCE_URL` 추가

**완료 기준 달성**: 이미지 업로드 1회 → `ai_raw_responses` 1행, `skin_part_results` 11행, `skin_metric_values` 80행, `skin_part_detections` 8행 확인 (통합 테스트 통과)

### Phase 2 — API 확장 + 프론트 연동 + seed rule 결과 보정

#### Phase 2-1 완료 (2026-05-12) — metrics API

> **완료**: `GET /analysis/sessions/{session_id}/metrics` API 구현 및 테스트 통과.

6. API 추가:
   - `GET /analysis/sessions/{session_id}/metrics` ✅ Phase 2-1 완료
     - `app/schemas/metrics.py` — `MetricItem` / `PartMetrics` / `MetricsResponse` 스키마
     - `app/services/metric_service.py` — `get_metrics()` (facepart ASC 정렬, 부위별 그룹핑)
     - `app/routers/analysis.py` — 엔드포인트 추가
     - `tests/test_metrics_api.py` — HTTP-layer 통합 테스트 6개 통과
   - `GET /analysis/sessions/{session_id}/metrics/trends` — 미구현 (Phase 3 예정)

#### Phase 2-2 완료 (2026-05-12) — 프론트 상세 측정값 UI 연동

> **완료**: 프론트 리포트 화면에서 metrics API 연동 및 상세 측정값 UI 추가.

7. 프론트 연동:
   - `frontend/services/analysis_api.py` — `get_session_metrics()` 추가
   - `frontend/views/report.py` — 리포트 로드 후 metrics API 소프트 호출, 부위별 상세 측정값 렌더링, 전문가 모드 토글
   - `frontend/styles/report.css` — 측정값 행/배지 스타일 추가
   - 기본 모드: 수분/모공/색소침착/탄력 R2/R7/주름 Ra/Rmax 표시
   - 전문가 모드: 전체 측정값 + dummy [모델 미학습] 배지 표시
   - mock/remote flat 세션(`parts=[]`) / metrics API 실패 시 기존 리포트 유지

#### Phase 2-3A 완료 (2026-05-12) — 추천 보정용 DB/ORM 준비

> **완료**: migration 0008 적용, ORM 모델 2개 추가, 기존 추천 로직 미변경.

8. 신규 테이블 migration 추가 (`0008_create_metric_boost_tables.py`) ✅ Phase 2-3A 완료
   - `metric_threshold_rules` — 측정값 임계값 관리
   - `metric_recommendation_boost_rules` — seed rule 결과 보정 rule 관리
   - 초기값은 임상 데이터 분석 후 INSERT (미삽입, seed 미확정)

#### Phase 2-3B 완료 (2026-05-12) — 추천 보정 로직 연결

> **완료**: `recommendation_boost_service.py` 추가, `recommendation_service` 내 boost 호출 연결.

9. `recommendation_boost_service.py` 추가 ✅ Phase 2-3B 완료
   - `apply_boost()` — `SkinMetricValue`(is_dummy=False) 조회 → `MetricRecommendationBoostRule` 매칭
   - `raw_part_name IS NULL` 규칙은 모든 부위에 적용 (`or_()` 사용)
   - 규칙별 예외 격리: 단일 규칙 실패 시 skip, 전체 실패 시 원본 반환
   - boost 후 `_filter_ingredients` 적용 (allergy / sensitive 필터 순서 유지)
   - 10개 단위 테스트 (`tests/test_recommendation_metric_boost.py`), 전체 31 passed

#### Phase 2-4 완료 (2026-05-12) — metrics trends API + 추이 그래프

10. `GET /analysis/metrics/trends` API 추가 ✅ Phase 2-4 완료
    - `metric_trend_service.get_trends()` — `AnalysisSession` JOIN, `status=completed`, `is_dummy=False`
    - 최근 `limit`개 DESC 조회 후 ASC 재정렬 (그래프용)
    - `analyzed_at IS NULL` 세션은 `created_at`으로 대체
    - 결과 없으면 `trend=[]` 반환 (에러 없음)
    - 6개 DB 통합 테스트, 전체 37 passed
    - 프론트엔드: 리포트 화면 "피부 측정 추이" 섹션 추가
      - "추이 그래프 보기" 토글로 on-demand 로드
      - 기본 8개 지표 (이마 수분, 볼 모공, 눈가 Ra, 탄력 R2 등)
      - 2개 이상: `st.line_chart` / 1개: 현재 값 표시 / 0개: 안내 문구
      - API 실패 시 리포트 화면 유지 (soft fail)

#### Phase 2-5 완료 (2026-05-12) — 추천 보정 seed 후보 검증

> **완료**: seed 후보 문서 작성 + 10개 mock 기반 단위 테스트.  
> 운영 DB seed 미삽입 — 임계값 임상 확정 후 삽입 예정.

- `docs/recommendation_boost_seed_plan.md` 추가
  - 모공(pore_count ≥ 700) / 수분(moisture ≤ 35) / 주름(Ra ≥ 25) / 탄력(R2 ≤ 0.35) 후보 rule 정의
  - 운영 반영 전 확인 체크리스트 포함
  - 수동 테스트 시나리오 3개 포함
  - 운영 seed INSERT SQL (미삽입, 참고용)
- `tests/test_recommendation_boost_seed_candidates.py` 추가 (10개 mock 기반 테스트)
  - 전체 47 passed

### Phase 3 — 추이 분석 + 고도화

**목표**: 장기 데이터 축적 후 개인화 추이 분석 및 추천 정확도 개선

11. boost seed 데이터 삽입 ✅ Phase 3-A 완료 (2026-05-12)
    - `scripts/seed_metric_boost_rules.py` — 11개 1차 베타 seed (장비 해석 기준)
    - moisture ≤ 35 / pore_count ≥ 700 / wrinkle Ra ≥ 25 / elasticity R2 ≤ 0.50 / R7 ≤ 0.35
    - wrinkle Rmax/Rt/Rz/Rq / pigmentation_count ≥ 100 / acne_count ≥ 30
    - 1차 베타값 — 데이터 50건 이상 축적 후 재검토 예정
11-B. YOLO 미검출 0.0 더미 처리 ✅ Phase 3-B-1 완료 (2026-05-12)
    - `multivalue_parser.parse_equipment()` — `detected_part_names: set[str] | None = None` 파라미터 추가
    - YOLO 미검출 부위 + value=0.0 → `is_dummy=True`, `dummy_reason="yolo_miss_or_model_fallback"`
    - `parse_multivalue_response()` — `detected_parts`로 `detected_part_names` set 빌드 후 전달
    - 예외: `full_face`(acne/pigmentation count), `chin_moisture`(label_not_trained 우선), value≠0.0, `detected_part_names=None`
    - `recommendation_boost_service.apply_boost()` 기존 `is_dummy == False` 필터로 자동 차단 (변경 없음)
    - 신규 테스트 15개: `tests/test_multivalue_parser.py` (총 24), `test_recommendation_metric_boost.py` +1 (총 11)
    - **78 passed** (`pytest -q` 전체)
12. 세션 간 metric 변화율 분석 (`delta_value` 계산)
13. 사용자 피부 타입·연령 기반 정규화 임계값 적용 (user_profiles 연계)
14. 전문가 모드: 추가 지표 trends 선택 UI ✅ Phase 3-B 완료
    - `views/report.py` — `_render_expert_trend_selector()` 추가 (캐스케이딩 selectbox + "추이 조회" 버튼)
    - `_TREND_METRIC_OPTIONS`: 7개 부위 × 그룹 × metric_name 조합 정의
    - 백엔드 API 변경 없음 (기존 `GET /analysis/metrics/trends` 재사용)
15. 장기 축적 데이터 기반 임계값 자동 보정 (선택)

---

## 10. 테스트 계획

### 10.1 파서 단위 테스트

```python
# tests/test_multivalue_parser.py
def test_parse_annotations_left_eye():
    # l_perocular_wrinkle grade=3 → severity="moderate"
def test_parse_annotations_chin_sagging():
    # chin_sagging grade=0 → severity="normal"
def test_parse_equipment_chin_moisture_is_dummy():
    # chin_moisture → is_dummy=True, dummy_reason="label_not_trained"
def test_parse_equipment_missing_label():
    # results dict에 없는 키 → is_dummy=True, dummy_reason="model_output_missing"
def test_parse_detections_yolo_vs_fallback():
    # detected_parts에 있으면 bbox_source="yolo"
    # 없으면 bbox_source="full_image_fallback"
```

Phase 1-2 테스트 결과:

- `../.venv/bin/python -m compileall app tests` 통과
- `../.venv/bin/python -m pytest tests/test_multivalue_parser.py -q` 통과 (`9 passed`)
- `../.venv/bin/python -m pytest -q` 통과 (`9 passed`)
- `../.venv/bin/python scripts/run_test.py --mode mock` 통과
  - 회원가입, 로그인, 프로필 저장, 분석 세션 생성, 이미지 업로드 성공
  - `skin_part_results` 7개 저장 확인
  - `part_recommendations` 7개 생성 확인
  - 추천 API / 리포트 API 정상 응답 확인

Phase 1-3 테스트 결과:

- `../.venv/bin/python -m compileall app tests` 통과
- `../.venv/bin/python -m pytest tests/test_multivalue_storage.py -v` 통과 (`6 passed`, DB 연결됨)
  - `test_multivalue_storage_row_counts`: ai_raw_responses=1, skin_part_results=11, skin_metric_values=80, skin_part_detections=8
  - `test_multivalue_storage_raw_json_preserved`: raw_json 보존 및 server_type="multivalue" 확인
  - `test_multivalue_storage_chin_moisture_dummy`: is_dummy=True, dummy_reason="label_not_trained" 확인
  - `test_multivalue_storage_yolo_detections`: bbox_source="yolo", left_eye class_name="l_eye" 확인
  - `test_multivalue_storage_severity_correctness`: forehead_pigmentation grade=2 → severity="moderate" 확인
  - `test_multivalue_storage_reupload_idempotent`: 재저장 시 ai_raw_responses 1개만 유지 확인
- `../.venv/bin/python -m pytest` 전체 통과 (`15 passed`)
- 기존 mock mode 흐름 (`_run_flat_mode`) 변경 없음: `image_service`, `recommendation_service`, report API 구조 유지

### 10.2 저장 통합 테스트 (AI 서버 없이)

- `multivalue_ai_server.py` 목 응답 JSON 파일 준비
- `AI_INFERENCE_MODE=multivalue` + mock 응답으로 전체 저장 흐름 확인
- DB row count 검증: skin_part_results 11개, skin_metric_values ~80개, skin_part_detections ≤8개, ai_raw_responses 1개

### 10.3 E2E 통합 테스트 (AI 서버 포함) ✅ Phase 3-D 완료 (2026-05-12)

실환경 E2E 테스트 완료:

- `multivalue_ai_server.py` port 9001 기동 (sys.path dinov3 버그 수정 포함)
- `.env` `AI_INFERENCE_MODE=multivalue` / `AI_MULTIVALUE_INFERENCE_URL=http://localhost:9001/inference/skin`
- session_id=88 (100×100 test image, user_id=69)

| 검증 항목 | 결과 |
|-----------|------|
| `ai_raw_responses` 1건 저장 | ✅ (5431 bytes) |
| `skin_part_results` 11건 저장 | ✅ |
| `skin_metric_values` 80건 저장 | ✅ |
| `skin_part_detections` 8건 저장 | ✅ (YOLO miss → all `full_image_fallback`) |
| `part_recommendations` 8건 생성 | ✅ |
| `chin_moisture` is_dummy=true | ✅ |
| report / metrics / trends / recommendations API | ✅ |
| pytest 47 passed | ✅ |

### 10.4 실제 얼굴 이미지 YOLO bbox 검증 ✅ Phase 3-E 완료 (2026-05-12)

- 테스트 이미지: 940×1410 정면 얼굴 (session_id=104)
- YOLO 검출: forehead(0.766) / lips(0.770) / chin(0.913) — 3개 `bbox_source=yolo`
- 미검출 5개 부위: `full_image_fallback` 정상 fallback
- 실제 추론값: `forehead_moisture=50.64`, `forehead_elasticity_R2=0.438`, `chin_elasticity_R2=0.826`
- 실제 grade: forehead pigmentation=3(severe), forehead wrinkle=4(severe), chin sagging=2(mild), lips dryness=2(mild)
- trends API: 2개 세션 추이 반영 (session 88: 0.0 → session 104: 0.438) ✅

### 10.4 회귀 테스트

- 기존 `AI_INFERENCE_MODE=mock/remote` (dummy_ai_server 기반) 흐름 그대로 동작하는지 확인
- `skin_part_results` 기반 추천이 multivalue 모드 이후에도 정상 동작하는지 확인

---

## 11. 프론트엔드 활용 설계

### 11.1 상세 보기 (파트별 측정값 카드)

세션 결과 화면에서 파트를 선택하면 해당 파트의 `skin_metric_values` row를 표시한다.

```
[이마 상세]
  수분:      63.2%     (양호)
  탄력 R2:   0.52      (주의)
  탄력 R7:   0.71      (양호)
  색소침착:  grade 1   (mild)
  주름:      grade 0   (정상)
```

### 11.2 전문가 모드 (equipment raw 값 전체 표시)

전문가 사용자 또는 의료진이 `skin_metric_values` 전체를 볼 수 있는 토글 모드.

```
이마 탄력:
  R0: 0.91  R1: 0.83  R2: 0.52  R3: 0.78
  R4: 0.69  R5: 0.81  R6: 0.74  R7: 0.71
  R8: 0.65  R9: 0.59
  Q0: 0.44  Q1: 0.61  Q2: 0.39  Q3: 0.72
```

### 11.3 추이 그래프 (시계열 측정값)

복수 세션의 `skin_metric_values`를 조회해 꺾은선 그래프로 표시.  
대표 지표(moisture, R2, Ra 등)만 기본 표시하고, 나머지는 전문가 모드에서 접근 가능.

```
수분 추이 (이마):
  2026-04-01: 52.1
  2026-04-15: 55.3
  2026-05-01: 63.2   ← 최근
```

### 11.4 API 명세 (Phase 2 구현 대상)

#### `GET /analysis/sessions/{session_id}/metrics`

파트별 equipment 상세 측정값 조회.

**응답 예시:**
```json
{
  "session_id": 42,
  "parts": [
    {
      "raw_part_name": "forehead",
      "display_part_name": "이마",
      "metrics": [
        {
          "metric_group": "moisture",
          "metric_name": "moisture",
          "metric_key": "forehead_moisture",
          "value": 63.2,
          "value_type": "reg",
          "is_dummy": false
        },
        {
          "metric_group": "elasticity",
          "metric_name": "R2",
          "metric_key": "forehead_elasticity_R2",
          "value": 0.52,
          "value_type": "reg",
          "is_dummy": false
        }
      ]
    }
  ]
}
```

#### `GET /analysis/sessions/{session_id}/metrics/trends`

복수 세션의 대표 metric 추이 조회. `?part=forehead&metric_group=moisture` 등 필터 지원.

**응답 예시:**
```json
{
  "user_id": 7,
  "raw_part_name": "forehead",
  "metric_group": "moisture",
  "metric_name": "moisture",
  "trend": [
    {"session_id": 10, "created_at": "2026-04-01", "value": 52.1},
    {"session_id": 18, "created_at": "2026-04-15", "value": 55.3},
    {"session_id": 42, "created_at": "2026-05-01", "value": 63.2}
  ]
}
```

---

## 12. 사용자 프로필 반영 방향

### 12.1 `user_profiles` 활용 원칙

AI 응답의 `info.gender`, `info.age`, `info.skin_type`, `info.sensitive`는 **모두 더미값**이다.  
실제 사용자 프로필은 `user_profiles` 테이블에서 읽는다.

```
AI 응답 info.*  →  저장 안 함 (더미, 무시)
user_profiles.*  →  추천·정규화·리포트에 활용
```

user_profiles에서 사용하는 항목:

| 컬럼 | 추천·분석 활용 방식 |
|------|----------------|
| `skin_type` | 지성/건성 피부 기준 임계값 분기 |
| `age` | 연령대별 탄력·주름 기준 임계값 정규화 |
| `gender` | 성별 평균 기준 비교 (선택) |
| `sensitive` | 민감 성분 제외 추천 |

### 12.2 AI 예측 프로필 원칙 (Phase 3 고도화 대상)

multivalue 모델이 피부 상태를 장기 추적하면 피부 타입 등을 간접 추정할 수 있다.  
단, AI 예측 프로필은 `user_profiles`를 **절대 덮어쓰지 않는다**.

| 원칙 | 내용 |
|------|------|
| **분리 저장** | AI 추정 피부 타입은 `ai_predicted_profiles` 별도 테이블에 저장 |
| **덮어쓰기 금지** | `user_profiles` 레코드를 AI 결과로 UPDATE하지 않는다 |
| **참고 신호** | AI 예측은 추천 보정·리포트 인사이트에만 참고, 사용자 설정 우선 |
| **투명성** | 프론트에서 "AI 분석 기반 추정값입니다" 명시 후 표시 |

**`ai_predicted_profiles` 테이블 (Phase 3 검토)**

```sql
CREATE TABLE ai_predicted_profiles (
    id                   BIGINT       PRIMARY KEY AUTO_INCREMENT,
    user_id              BIGINT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id           BIGINT       NOT NULL REFERENCES analysis_sessions(id) ON DELETE CASCADE,
    predicted_skin_type  TINYINT      NULL,
    predicted_sensitive  TINYINT      NULL,
    model_version        VARCHAR(100) NULL,
    confidence           FLOAT        NULL,
    created_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ai_predicted_profiles_user (user_id)
);
```

> 이 테이블은 현재 미구현이다. multivalue 모델이 skin_type 예측 라벨을 직접 출력하도록 확장되거나, 장기 추이 기반 규칙 엔진이 구현되면 도입한다.

---

## 13. 최종 요약

```
저장 매핑:
  annotations.*        → skin_part_results      (등급/이슈/severity, 추천 기준)
  equipment.*          → skin_metric_values      (상세 측정값, 추이 분석용)
  images.bbox / YOLO   → skin_part_detections   (bbox 기록)
  전체 응답 JSON        → ai_raw_responses        (디버깅/재처리)
  info.gender/age 등   → 저장 안 함 → user_profiles 사용

더미 처리:
  chin_moisture        → is_dummy=true, dummy_reason="label_not_trained"
  미학습/미검출 폴백값  → is_dummy=true, dummy_reason="model_output_missing"
  YOLO 미검출 bbox     → bbox_source="full_image_fallback"

추천 로직:
  현재: DB seed rule 기반 (recommendation_rules + ingredient_rules)
        skin_part_results.severity → recommendation_rules 조회 → 결과 저장
        코드 변경 없이 그대로 동작

  Phase 2: skin_metric_values 기반 seed rule 결과 보정 추가
        기존 추천 결과를 대체하지 않고 보정만 수행
        성분 우선순위 조정 / 보조 성분 후보 추가 / care_tips 문구 추가
        allergy / sensitive 필터링은 보정 이후 마지막에 적용

  추가 테이블 (Phase 2 migration):
        metric_threshold_rules              (임계값 관리)
        metric_recommendation_boost_rules   (seed rule 보정 rule 관리)

Migration:
  Phase 1: 신규 0007 migration 1개 (3개 테이블 추가, 기존 테이블 변경 없음)
  Phase 2: 신규 0008 migration 1개 (2개 보정 테이블 추가)
```
