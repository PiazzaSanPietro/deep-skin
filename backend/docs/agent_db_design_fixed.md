# Agent DB Design

## DBMS

MySQL을 사용한다.

## ORM

SQLAlchemy를 사용한다.

## Migration

Alembic을 사용한다.

---

# 1. DB 설계 원칙

## 핵심 규칙

- 사용자 정보와 분석 결과는 분리한다.
- 개인정보는 `user_profiles`에 저장한다.
- 원본 이미지는 파일 시스템에 저장하고 DB에는 경로만 저장한다.
- 모델 분석 결과는 `skin_part_results`에 세부 단위로 저장한다.
- 추천 규칙은 `recommendation_rules`에 미리 저장한다.
- 성분 주의사항은 `ingredient_rules`에 미리 저장한다.
- 사용자 화면용 최종 추천 결과는 `part_recommendations`에 부위별로 저장한다.
- AI-Hub JSON은 개발/테스트용으로 `skin_json_records`에 저장한다.
- JWT refresh token을 사용할 경우 `refresh_tokens`에 저장한다.
- 모든 분석 데이터는 `user_id`를 통해 로그인 사용자와 연결한다.
- 분석 세션, 이미지, 분석 결과, 추천 결과는 사용자 삭제 시 함께 삭제한다.
- `issue_type`에는 상태를 포함하지 않고, 상태는 `severity` 컬럼으로 구분한다.

---

# 2. 주요 테이블

- `users`
- `user_profiles`
- `refresh_tokens`
- `analysis_sessions`
- `uploaded_images`
- `skin_json_records`
- `skin_part_results`
- `ingredient_rules`
- `recommendation_rules`
- `part_recommendations`
- `products`

---

# 3. 테이블 관계

```text
users
├── user_profiles
├── refresh_tokens
└── analysis_sessions
    ├── uploaded_images
    ├── skin_json_records
    ├── skin_part_results
    └── part_recommendations

ingredient_rules
└── recommendation_rules.recommend_ingredients에서 성분 key로 참조

recommendation_rules
└── part_recommendations.rule_id
```

---

# 4. issue_type / severity 저장 규칙

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

상태는 `issue_type`에 포함하지 않는다.

---

# 5. users

로그인 계정 정보이다.

```sql
CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    last_login_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_users_email (email)
);
```

---

# 6. user_profiles

사용자의 추가 개인정보이다.

```sql
CREATE TABLE user_profiles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,

    age INT NULL,
    birth_year INT NULL,
    gender VARCHAR(20) NULL,
    skin_type INT NULL,
    sensitive INT NULL,

    main_concerns JSON NULL,
    allergy_ingredients JSON NULL,
    preferred_product_types JSON NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_user_profiles_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,

    INDEX idx_user_profiles_user_id (user_id)
);
```

## 컬럼 설명

| 컬럼 | 설명 |
|---|---|
| `age` | 사용자가 입력한 나이 |
| `birth_year` | 출생연도, 선택값 |
| `gender` | 성별 |
| `skin_type` | 피부 타입 코드 |
| `sensitive` | 민감 여부 |
| `main_concerns` | 주요 피부 고민 |
| `allergy_ingredients` | 피해야 할 성분 key 배열 |
| `preferred_product_types` | 선호 제품 타입 |

---

# 7. refresh_tokens

Refresh Token 관리 테이블이다.

로그인 응답에서 `refresh_token`을 내려줄 경우 사용하는 것이 좋다.

```sql
CREATE TABLE refresh_tokens (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    expires_at DATETIME NOT NULL,
    revoked_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_refresh_tokens_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,

    INDEX idx_refresh_tokens_user_id (user_id),
    INDEX idx_refresh_tokens_expires_at (expires_at)
);
```

## 주의

Refresh Token 원문은 DB에 저장하지 않는다.  
해시값만 저장한다.

---

# 8. analysis_sessions

피부 분석 1회를 나타내는 테이블이다.

```sql
CREATE TABLE analysis_sessions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,

    session_name VARCHAR(255) NOT NULL,
    input_type VARCHAR(30) NOT NULL DEFAULT 'image',
    status VARCHAR(30) NOT NULL DEFAULT 'pending',

    overall_status VARCHAR(30) NULL,
    summary_message TEXT NULL,
    error_message TEXT NULL,

    analyzed_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_analysis_sessions_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,

    INDEX idx_analysis_sessions_user_id (user_id),
    INDEX idx_analysis_sessions_status (status),
    INDEX idx_analysis_sessions_created_at (created_at)
);
```

## status 값

```text
pending
processing
completed
failed
```

## input_type 값

```text
image
dev_json
mixed
```

---

# 9. uploaded_images

사용자가 업로드한 얼굴 이미지 메타데이터를 저장한다.

이미지 파일 자체는 DB에 저장하지 않는다.

```sql
CREATE TABLE uploaded_images (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,

    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    file_size INT NOT NULL,

    width INT NULL,
    height INT NULL,

    angle INT NULL,
    facepart INT NULL,

    upload_status VARCHAR(30) NOT NULL DEFAULT 'uploaded',
    failure_reason TEXT NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_uploaded_images_session
        FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_uploaded_images_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,

    INDEX idx_uploaded_images_session_id (session_id),
    INDEX idx_uploaded_images_user_id (user_id),
    INDEX idx_uploaded_images_status (upload_status)
);
```

## upload_status 값

```text
uploaded
processing
processed
failed
```

---

# 10. skin_json_records

개발/테스트용 AI-Hub JSON 저장 테이블이다.

운영 서비스의 핵심 테이블은 아니다.

```sql
CREATE TABLE skin_json_records (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,

    filename VARCHAR(255) NULL,
    raw_subject_id VARCHAR(100) NULL,

    device INT NULL,
    angle INT NULL,
    facepart INT NULL,

    width INT NULL,
    height INT NULL,

    bbox_x INT NULL,
    bbox_y INT NULL,
    bbox_w INT NULL,
    bbox_h INT NULL,

    raw_json JSON NOT NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_skin_json_records_session
        FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_skin_json_records_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,

    INDEX idx_skin_json_records_session_id (session_id),
    INDEX idx_skin_json_records_user_id (user_id),
    INDEX idx_skin_json_records_raw_subject_id (raw_subject_id)
);
```
---

# 10-1. AI-Hub JSON → 내부 표준 지표 매핑

AI-Hub JSON의 annotation key는 그대로 `issue_type`으로 저장하지 않는다.

`json_parser.py`에서 내부 표준 지표명으로 변환한 뒤 `skin_part_results`에 저장한다.

| AI-Hub annotation key | raw_part_name | display_part_name | issue_type | metric_display_name |
|---|---|---|---|---|
| `l_cheek_pore` | `left_cheek` | `볼` | `pore` | `모공` |
| `r_cheek_pore` | `right_cheek` | `볼` | `pore` | `모공` |
| `l_cheek_pigmentation` | `left_cheek` | `볼` | `pigmentation` | `색소침착` |
| `r_cheek_pigmentation` | `right_cheek` | `볼` | `pigmentation` | `색소침착` |
| `forehead_wrinkle` | `forehead` | `이마` | `wrinkle` | `주름` |
| `forehead_pigmentation` | `forehead` | `이마` | `pigmentation` | `색소침착` |
| `glabellus_wrinkle` | `glabella` | `미간` | `wrinkle` | `주름` |
| `l_perocular_wrinkle` | `left_eye` | `눈가` | `wrinkle` | `주름` |
| `r_perocular_wrinkle` | `right_eye` | `눈가` | `wrinkle` | `주름` |
| `lip_dryness` | `lips` | `입술` | `dryness` | `건조` |
| `chin_sagging` | `chin` | `턱` | `sagging` | `처짐` |
| `acne` | `full_face` | `전체 얼굴` | `acne` | `여드름` |

---

## grade_value → severity 변환 기준

초기 구현에서는 다음 기준으로 변환한다.

| grade_value | severity | 의미 |
|---:|---|---|
| 0 | `normal` | 정상 / 양호 |
| 1 | `mild` | 경미 |
| 2 | `moderate` | 보통 / 관리 필요 |
| 3 이상 | `severe` | 심함 / 집중 관리 필요 |

단, annotation 항목마다 최대값이 다르므로 추후 metric별 기준으로 세분화할 수 있다.

---

## 저장 예시

AI-Hub JSON이 다음과 같이 들어온 경우:

```json
{
  "images": {
    "facepart": 5
  },
  "annotations": {
    "l_cheek_pore": 3
  }
}
```

### skin_part_results에는 다음과 같이 저장한다.
```
raw_part_name = left_cheek
display_part_name = 볼
metric_name = pore
metric_display_name = 모공
issue_type = pore
grade_value = 3
severity = severe
```

자세한 AI-Hub annotation key 매핑 기준은 `agent_db_design_fixed.md`의 “AI-Hub JSON → 내부 표준 지표 매핑” 섹션을 따른다.

---

# 11. skin_part_results

모델이 분석한 부위별 피부 지표 결과를 저장한다.

이 테이블은 사용자 화면용 응답이 아니라, 세부 분석 결과 저장용이다.

```sql
CREATE TABLE skin_part_results (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    image_id BIGINT NULL,
    json_record_id BIGINT NULL,

    raw_part_name VARCHAR(50) NOT NULL,
    display_part_name VARCHAR(50) NOT NULL,

    metric_name VARCHAR(50) NOT NULL,
    metric_display_name VARCHAR(50) NOT NULL,

    grade_value INT NULL,
    measured_value DOUBLE NULL,
    predicted_value DOUBLE NULL,
    confidence_score DOUBLE NULL,

    severity VARCHAR(30) NOT NULL,
    issue_type VARCHAR(100) NOT NULL,
    reason_text TEXT NULL,

    model_name VARCHAR(100) NULL,
    model_version VARCHAR(100) NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_skin_part_results_session
        FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_skin_part_results_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_skin_part_results_image
        FOREIGN KEY (image_id) REFERENCES uploaded_images(id)
        ON DELETE SET NULL,

    CONSTRAINT fk_skin_part_results_json_record
        FOREIGN KEY (json_record_id) REFERENCES skin_json_records(id)
        ON DELETE SET NULL,

    INDEX idx_skin_part_results_session_id (session_id),
    INDEX idx_skin_part_results_user_id (user_id),
    INDEX idx_skin_part_results_part (display_part_name),
    INDEX idx_skin_part_results_metric (metric_name),
    INDEX idx_skin_part_results_issue (issue_type),
    INDEX idx_skin_part_results_severity (severity)
);
```

## 컬럼 설명

| 컬럼 | 설명 |
|---|---|
| `raw_part_name` | 모델 원본 부위명, 예: left_cheek |
| `display_part_name` | 화면 표시 부위명, 예: 볼 |
| `metric_name` | 내부 지표명, 예: pore |
| `metric_display_name` | 화면 표시 지표명, 예: 모공 |
| `grade_value` | 등급값 |
| `measured_value` | 장비 측정값 또는 추정값 |
| `predicted_value` | 모델 예측 수치 |
| `confidence_score` | 모델 confidence |
| `severity` | normal, mild, moderate, severe |
| `issue_type` | 문제 지표명, 예: pore, wrinkle, pigmentation, moisture |
| `reason_text` | 결과 설명 |
| `model_name` | 사용 모델명 |
| `model_version` | 모델 버전 |

---

# 12. ingredient_rules

성분별 주의사항을 저장하는 테이블이다.

추천 성분 필터링 시 사용자 알레르기 성분 또는 민감성 피부 여부와 함께 사용한다.

```sql
CREATE TABLE ingredient_rules (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    ingredient_name VARCHAR(100) NOT NULL,
    display_name VARCHAR(100) NOT NULL,

    caution_for_sensitive BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uq_ingredient_rules_name (ingredient_name),
    INDEX idx_ingredient_rules_sensitive (caution_for_sensitive)
);
```

---

# 13. recommendation_rules

부위, 문제 지표, 심각도에 따른 추천 기준을 저장한다.

추천 문구, 화장품 카테고리, 추천 성분, 관리법은 이 테이블에 미리 저장한다.

```sql
CREATE TABLE recommendation_rules (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    display_part_name VARCHAR(50) NOT NULL,
    issue_type VARCHAR(100) NOT NULL,
    issue_display_name VARCHAR(100) NOT NULL,
    severity VARCHAR(30) NOT NULL,

    reason_template TEXT NOT NULL,
    recommend_categories JSON NOT NULL,
    recommend_ingredients JSON NOT NULL,
    care_tips JSON NULL,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uq_recommendation_rules_part_issue_severity (
        display_part_name,
        issue_type,
        severity
    ),
    INDEX idx_recommendation_rules_part_issue (display_part_name, issue_type),
    INDEX idx_recommendation_rules_severity (severity),
    INDEX idx_recommendation_rules_active (is_active)
);
```

## 컬럼 설명

| 컬럼 | 설명 |
|---|---|
| `display_part_name` | 추천 대상 부위, 예: 볼, 눈가 |
| `issue_type` | 문제 지표명, 예: pore, wrinkle |
| `issue_display_name` | 화면 표시 문제명, 예: 모공, 주름 |
| `severity` | normal, mild, moderate, severe |
| `reason_template` | 추천 이유 문구 |
| `recommend_categories` | 추천 화장품 카테고리 |
| `recommend_ingredients` | 추천 성분 |
| `care_tips` | 관리법 |
| `is_active` | 규칙 사용 여부 |

---

# 14. part_recommendations

부위별 최종 추천 결과를 저장한다.

이 테이블은 추천 규칙 자체가 아니라, 특정 사용자와 특정 분석 세션에서 실제로 생성된 추천 결과를 저장한다.

```sql
CREATE TABLE part_recommendations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    rule_id BIGINT NULL,

    display_part_name VARCHAR(50) NOT NULL,

    issue_type VARCHAR(100) NOT NULL,
    issue_display_name VARCHAR(100) NOT NULL,
    severity VARCHAR(30) NOT NULL,

    reason TEXT NOT NULL,

    recommend_categories JSON NOT NULL,
    recommend_ingredients JSON NOT NULL,
    excluded_ingredients JSON NULL,
    exclusion_reason TEXT NULL,
    care_tips JSON NULL,

    recommendation_source VARCHAR(50) NOT NULL DEFAULT 'rule_based',

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_part_recommendations_session
        FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_part_recommendations_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_part_recommendations_rule
        FOREIGN KEY (rule_id) REFERENCES recommendation_rules(id)
        ON DELETE SET NULL,

    INDEX idx_part_recommendations_session_id (session_id),
    INDEX idx_part_recommendations_user_id (user_id),
    INDEX idx_part_recommendations_part (display_part_name),
    INDEX idx_part_recommendations_issue (issue_type),
    INDEX idx_part_recommendations_severity (severity)
);
```

## 컬럼 설명

| 컬럼 | 설명 |
|---|---|
| `rule_id` | 사용된 추천 규칙 ID |
| `display_part_name` | 추천 대상 부위 |
| `issue_type` | 문제 지표명, 예: pore, wrinkle |
| `issue_display_name` | 화면 표시 문제명 |
| `severity` | normal, mild, moderate, severe |
| `reason` | 추천 이유 |
| `recommend_categories` | 추천 화장품 카테고리 |
| `recommend_ingredients` | 최종 추천 성분 |
| `excluded_ingredients` | 사용자 알레르기 또는 조건으로 제외한 성분 |
| `exclusion_reason` | 성분 제외 이유 |
| `care_tips` | 관리법 |
| `recommendation_source` | rule_based, product_based 등 추천 방식 |

---

# 15. products

추천할 화장품 후보를 저장한다.

초기에는 실제 상품보다 카테고리/성분 중심으로 구성해도 된다.

```sql
CREATE TABLE products (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(255) NOT NULL,
    brand_name VARCHAR(255) NULL,
    category VARCHAR(100) NOT NULL,

    target_issue VARCHAR(100) NOT NULL,
    target_part VARCHAR(50) NULL,

    ingredients JSON NULL,
    excluded_for_sensitive BOOLEAN NOT NULL DEFAULT FALSE,

    description TEXT NULL,
    product_url VARCHAR(500) NULL,
    image_url VARCHAR(500) NULL,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_products_target_issue (target_issue),
    INDEX idx_products_target_part (target_part),
    INDEX idx_products_category (category),
    INDEX idx_products_is_active (is_active)
);
```

---

# 16. DB 설계 주의사항

## JSON 컬럼 사용 기준

다음 값은 JSON 컬럼으로 둔다.

- `main_concerns`
- `allergy_ingredients`
- `preferred_product_types`
- `recommend_categories`
- `recommend_ingredients`
- `excluded_ingredients`
- `care_tips`
- `ingredients`
- `raw_json`

단, 자주 검색해야 하는 값은 별도 컬럼으로 분리한다.

예:

```text
issue_type
severity
display_part_name
metric_name
target_issue
target_part
```

---

## 이미지 저장 기준

이미지 파일은 DB에 저장하지 않는다.

```text
uploads/skin_images/{user_id}/{session_id}/{uuid_filename}.jpg
```

DB에는 다음만 저장한다.

- 파일명
- 저장 경로
- MIME type
- 파일 크기
- width
- height

---

## 삭제 기준

사용자가 삭제되면 다음 데이터도 함께 삭제된다.

- user_profiles
- refresh_tokens
- analysis_sessions
- uploaded_images
- skin_json_records
- skin_part_results
- part_recommendations

단, 실제 이미지 파일은 DB cascade만으로 삭제되지 않으므로 별도 파일 삭제 로직이 필요하다.
