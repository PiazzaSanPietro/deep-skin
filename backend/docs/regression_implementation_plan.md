# 회귀값 반영 구현 계획서

## 1. 현재 구조 이해 요약

현재 백엔드는 AI 추론 결과를 분류(classification) 기반으로만 처리한다. `SkinPartResult` ORM 모델에는 `measured_value(Float, nullable)`와 `predicted_value(Float, nullable)` 컬럼이 migration 0003에서 이미 생성되어 있으나, 어떤 서비스 코드도 이 컬럼에 값을 쓰지 않아 항상 NULL이다. `PartResult` Pydantic 스키마(`image_upload.py`)에는 `grade_value(int)`와 `severity(str)`만 있고 회귀 연속값 필드가 없다. `json_parser.py`의 `parse_annotations()`는 annotation 값을 `int(raw_value)`로 강제 변환하므로 소수점 값이 입력되면 절삭된다. 리포트 응답은 `report_service.py`가 전담하며 `analysis.py` router에서 직접 조립하지 않는다.

> **구현 현황 (2026-05-11 기준)**: **1~9단계 전체 완료.** `PartResult`·`IssueItem` 스키마 확장(1·3단계), 이미지 inference 경로 DB 저장(2단계), 리포트 응답 매핑(4단계), AI-Hub JSON float 파싱·measured_value 보존(5단계), dev JSON 경로 DB 저장(6단계), mock inference predicted_value 추가(7단계), dummy AI server predicted_value 추가(8단계), ai_inference_contract.md 계약 문서 업데이트(9단계)가 모두 완료되었다.

---

## 2. 실제 코드 흐름 (이미지 업로드 → 리포트 반환)

### 1단계. 이미지 업로드 및 검증

- **파일**: `app/services/image_service.py`
- **현재 하는 일**: 파일 확장자/MIME/크기/Pillow 검증 후 `{UPLOAD_DIR}/{user_id}/{session_id}/{uuid}.jpg`에 저장. `UploadedImage` row 생성 후 `session.status = "processing"`으로 전환한다.
- **회귀값 반영 시 수정 필요 부분**: 이 단계 자체는 파일 저장이므로 수정 불필요. 다만 이후 inference 결과 저장 단계(14단계)에서 `PartResult`에 회귀값 필드가 추가되어야 이 흐름 전체가 동작한다.
- **주의할 점**: `file_path.write_bytes(content)`로 저장한 파일 경로가 `inference_service.run_inference()`에 전달된다. 파일 경로 변경 없음.

### 2단계. AI 추론 요청

- **파일**: `app/services/inference_service.py`
- **현재 하는 일**: `settings.AI_INFERENCE_MODE`가 `"mock"`이면 `_run_mock()`을 반환하고, `"remote"`이면 `_run_remote()`로 AI 서버에 multipart/form-data 요청 후 응답을 `InferenceResult(**data)`로 검증(`_validate_response()`)하여 반환한다. mock은 7개 `PartResult`를 하드코딩으로 반환한다.
- **회귀값 반영 시 수정 필요 부분**: `_run_mock()` 내 `PartResult` 생성 시 `predicted_value` 필드가 없다. `PartResult` 스키마에 필드 추가 후 mock 데이터에도 `predicted_value` 값을 추가해야 테스트 가능하다. `_validate_response()`는 `InferenceResult(**data)` 호출이므로 스키마만 수정되면 자동으로 검증된다.
- **주의할 점**: AI 서버가 `predicted_value`를 응답하지 않더라도 `Optional[float] = None`으로 정의하면 Pydantic이 누락 필드를 `None`으로 처리하므로 기존 remote AI 서버와의 하위 호환이 유지된다.

### 3단계. 추론 결과 DB 저장

- **파일**: `app/services/image_service.py` (라인 126~141)
- **현재 하는 일**: `result.parts` 루프에서 `SkinPartResult(...)` 객체를 생성하고 `db.add()` 후 `db.commit()`. 현재 `grade_value`, `severity`, `confidence_score`, `model_name`, `model_version`만 저장. `measured_value`와 `predicted_value`는 저장하지 않아 항상 NULL.
- **회귀값 반영 시 수정 필요 부분**: 라인 127~141의 `SkinPartResult(...)` 생성 블록에 `predicted_value=part.predicted_value`와 `measured_value=part.measured_value`를 추가해야 한다.
- **주의할 점**: `part`는 `PartResult` Pydantic 객체다. `PartResult`에 해당 필드가 먼저 추가되어야 이 코드가 동작한다. 순서 의존: `image_upload.py` 수정 → `image_service.py` 수정.

### 4단계. 추천 생성

- **파일**: `app/services/recommendation_service.py`
- **현재 하는 일**: `SkinPartResult`를 `session_id`로 조회한 뒤 `(display_part_name, issue_type)` 조합의 최고 severity를 선택, `RecommendationRule`을 매칭하여 `PartRecommendation`에 저장한다. `severity` 기반으로만 동작한다.
- **회귀값 반영 시 수정 필요 부분**: 현재는 `severity` 문자열만 사용하므로 `measured_value` / `predicted_value`를 직접 사용하지 않는다. 회귀값 기반 severity 변환 로직을 추가하려면 이 서비스를 수정해야 하지만, AI 서버가 severity를 직접 내려주는 경우에는 수정 불필요.
- **주의할 점**: `r.severity`로 `worst` 딕셔너리를 구성하므로, `predicted_value`에서 severity를 재계산하는 로직을 추가할 경우 `worst` 선택 전 단계에서 처리해야 한다.

### 5단계. 리포트 조회

- **파일**: `app/services/report_service.py` (리포트 생성 전담), `app/routers/analysis.py` (라우터), `app/schemas/report.py` (응답 스키마)
- **현재 하는 일**: `report_service.get_report()`가 `SkinPartResult`를 조회하고 `IssueItem`을 생성. `analysis.py` router의 `get_session_report()`는 단순히 `report_service.get_report(db, session_id, user_id)`를 호출하고 `ReportResponse`를 `response_model`로 사용한다. `IssueItem` 생성은 `report_service.py` 라인 66~75에서 이루어진다.
- **회귀값 반영 시 수정 필요 부분**: `report_service.py` 라인 66~75에서 `IssueItem(...)` 생성 시 `predicted_value=r.predicted_value`와 `measured_value=r.measured_value`를 추가해야 한다. `app/schemas/report.py`의 `IssueItem`에도 해당 필드가 먼저 추가되어야 한다.
- **주의할 점**: 현재 `IssueItem`은 `grade_value: Optional[int]`만 포함. `predicted_value`와 `measured_value`는 `Optional[float] = None`으로 추가해야 기존 클라이언트 호환이 유지된다. `analysis.py` router는 수정 불필요.

### 6단계. AI-Hub JSON 직접 입력 — parser (개발용)

- **파일**: `app/utils/json_parser.py`
- **현재 하는 일**: `parse_annotations()`에서 `int(raw_value)`로 annotation 값을 `grade_value`로 변환. `ParsedPartResult` 데이터클래스에는 회귀값 필드 없음.
- **회귀값 반영 시 수정 필요 부분**: `ParsedPartResult`에 `measured_value: float | None = None` 추가. `parse_annotations()`에서 float 파싱 경로 추가. 현재 `grade_to_severity(grade: int)` 함수에 의존하므로 회귀값을 별도 파싱 경로로 처리해야 한다.
- **주의할 점**: 현재 `int(raw_value)` 코드(라인 121)에서 소수점이 **실제로 절삭**된다. `float("2.7")`을 `int()`로 변환하면 `2`가 되므로 원본 연속형 수치가 손실된다. 수정 시 `float(raw_value)`로 먼저 파싱하고 `int()`는 `grade_value` 전용으로 별도 처리해야 한다.

### 6-1단계. AI-Hub JSON 직접 입력 — DB 저장 (개발용)

- **파일**: `app/routers/dev.py` (router 위임만), `app/services/dev_json_service.py` (실제 저장 로직)
- **현재 하는 일**: `dev.py` router는 `dev_json_service.upload_dev_json()`에 완전히 위임한다. `dev_json_service.py` 라인 57에서 `parse_annotations(item.annotations)`를 호출하고, 라인 59~72에서 `SkinPartResult(...)` 객체를 생성·저장한다. 현재 생성 블록에는 `measured_value` 필드가 없어 dev JSON 경로로 저장해도 항상 NULL이 된다.
- **회귀값 반영 시 수정 필요 부분**: `dev_json_service.py` 라인 59~72의 `SkinPartResult(...)` 생성 블록에 `measured_value=part.measured_value` 추가. `json_parser.py` 수정이 선행되어야 `part.measured_value` 접근이 가능하다.
- **주의할 점**: `dev.py` router 자체는 수정 불필요 — 위임 호출만 있다. 이미지 업로드 경로(`image_service.py`)와 dev JSON 경로(`dev_json_service.py`) 양쪽에서 모두 `measured_value`를 저장해야 두 흐름이 일관성을 유지한다.

---

## 3. 구현 대상 파일별 판단

### `app/schemas/image_upload.py`

- **수정 필요 여부**: **완료 (1단계)**
- **수정 이유**: `PartResult`에 회귀값 필드가 없어 AI 서버가 `predicted_value`를 응답해도 Pydantic이 해당 필드를 무시하거나 validation 오류를 낸다. 모든 후속 로직이 이 스키마에 의존한다.
- **예상 수정 내용**:
  ```python
  class PartResult(BaseModel):
      ...
      grade_value: int
      predicted_value: Optional[float] = None   # 추가
      measured_value: Optional[float] = None    # 추가
      severity: str
      confidence_score: float
  ```
- **테스트 포인트**: `PartResult(grade_value=2, severity="moderate", confidence_score=0.82, predicted_value=0.731)`이 정상 생성되는지 확인. `predicted_value` 누락 시 `None`으로 처리되는지 확인.

### `app/services/image_service.py`

- **수정 필요 여부**: **완료 (2단계)**
- **수정 이유**: 라인 127~141의 `SkinPartResult(...)` 생성 블록에 `predicted_value`, `measured_value` 필드가 없어 DB에 항상 NULL이 저장된다.
- **예상 수정 내용**:
  ```python
  db.add(SkinPartResult(
      session_id=session_id,
      user_id=user_id,
      image_id=image_record.id,
      raw_part_name=part.raw_part_name,
      display_part_name=part.display_part_name,
      metric_name=part.metric_name,
      metric_display_name=part.metric_display_name,
      issue_type=part.issue_type,
      grade_value=part.grade_value,
      predicted_value=part.predicted_value,   # 추가
      measured_value=part.measured_value,     # 추가
      severity=part.severity,
      confidence_score=part.confidence_score,
      model_name=result.model_name,
      model_version=result.model_version,
  ))
  ```
- **테스트 포인트**: 이미지 업로드 후 `SELECT predicted_value, measured_value FROM skin_part_results WHERE session_id=?`로 NULL 여부 확인.

### `app/utils/json_parser.py`

- **수정 필요 여부**: **완료 (5단계)**
- **수정 이유**: 라인 121의 `grade = int(raw_value)`는 소수점을 절삭한다. AI-Hub annotation 값이 `"l_cheek_pore": 2.73` 형태의 float일 경우 `2`로 잘린다. 회귀값 저장을 위해서는 원본 float를 별도 보존해야 한다.
- **예상 수정 내용**:
  ```python
  @dataclass
  class ParsedPartResult:
      ...
      grade_value: int
      measured_value: float | None   # 추가: 원본 float 수치 보존
      severity: str
  
  # parse_annotations() 내부:
  raw_float = float(raw_value)         # 원본 float 보존
  grade = int(raw_float)               # 기존과 동일
  results.append(
      ParsedPartResult(
          ...
          grade_value=grade,
          measured_value=raw_float,    # 추가
          severity=grade_to_severity(grade),
      )
  )
  ```
- **테스트 포인트**: `parse_annotations({"l_cheek_pore": 2.7})`이 `grade_value=2, measured_value=2.7`을 반환하는지 확인.

### `app/services/dev_json_service.py`

- **수정 필요 여부**: **완료 (6단계)**
- **수정 이유**: 라인 59~72의 `SkinPartResult(...)` 생성 블록에 `measured_value` 필드가 없어, dev JSON 경로로 저장해도 항상 NULL이 된다. 이미지 업로드 경로(`image_service.py`)와 일관성을 맞춰야 한다.
- **예상 수정 내용**: 라인 59~72 `SkinPartResult(...)` 블록에 `measured_value=part.measured_value` 추가
  ```python
  result = SkinPartResult(
      session_id=session_id,
      user_id=user_id,
      json_record_id=json_record.id,
      raw_part_name=part.raw_part_name,
      display_part_name=part.display_part_name,
      metric_name=part.metric_name,
      metric_display_name=part.metric_display_name,
      grade_value=part.grade_value,
      measured_value=part.measured_value,   # 추가
      severity=part.severity,
      issue_type=part.issue_type,
      model_name="ai_hub_annotation",
      model_version="1.0",
  )
  ```
- **순서 의존**: `json_parser.py`의 `ParsedPartResult`에 `measured_value` 필드가 먼저 추가되어야 이 코드가 동작한다.
- **테스트 포인트**: `POST /dev/analysis/sessions/{id}/json`에 `{"annotations": {"l_cheek_pore": 2.73}}` 전송 후 `SELECT grade_value, measured_value FROM skin_part_results`로 `grade_value=2, measured_value=2.73` 확인.

### `app/schemas/report.py`

- **수정 필요 여부**: **완료 (3단계)**
- **수정 이유**: `IssueItem`에 `grade_value: Optional[int]`만 있고 회귀값 필드가 없어, `report_service.py`에서 `predicted_value`를 읽어도 응답에 포함할 수 없다.
- **예상 수정 내용**:
  ```python
  class IssueItem(BaseModel):
      metric_name: str
      metric_display_name: str
      issue_type: str
      severity: str
      grade_value: Optional[int]
      predicted_value: Optional[float] = None   # 추가
      measured_value: Optional[float] = None    # 추가
      reason: Optional[str]
  ```
- **테스트 포인트**: 리포트 API 응답 JSON에 `"predicted_value": null` 또는 실제 float 값이 포함되는지 확인.

### `app/services/report_service.py`

- **수정 필요 여부**: **완료 (4단계)**
- **수정 이유**: 라인 66~75에서 `IssueItem(...)` 생성 시 `r.predicted_value`와 `r.measured_value`를 읽지 않아 응답에서 항상 누락된다.
- **예상 수정 내용**: `get_report()` 내 `issues` 리스트 컴프리헨션 수정
  ```python
  issues = [
      IssueItem(
          metric_name=r.metric_name,
          metric_display_name=r.metric_display_name,
          issue_type=r.issue_type,
          severity=r.severity,
          grade_value=r.grade_value,
          predicted_value=r.predicted_value,   # 추가
          measured_value=r.measured_value,     # 추가
          reason=r.reason_text,
      )
      for r in part_results
  ]
  ```
- **테스트 포인트**: `GET /analysis/sessions/{id}/report` 응답의 `part_reports[].issues[].predicted_value`가 DB에 저장된 값과 일치하는지 확인.

### `app/services/inference_service.py`

- **수정 필요 여부**: **완료 (7단계)**
- **수정 이유**: `_run_mock()`의 `PartResult` 생성 시 `predicted_value` 필드가 없다. `PartResult` 스키마 수정 후 `Optional` 기본값이 `None`이므로 코드 자체는 오류가 나지 않지만, mock에서 회귀값 흐름 전체를 검증하려면 실제 값을 추가해야 한다.
- **예상 수정 내용**: `_run_mock()` 내 각 `PartResult()`에 `predicted_value=0.xx` 추가 (예: `predicted_value=0.73`)
- **테스트 포인트**: mock 모드 이미지 업로드 후 `skin_part_results.predicted_value`가 NULL이 아닌 실제 float 값으로 저장되는지 확인.

### `scripts/dummy_ai_server.py`

- **수정 필요 여부**: **완료 (8단계)**
- **수정 이유**: `_MOCK_PARTS` 딕셔너리에 `predicted_value` 키가 없다. remote 모드 end-to-end 테스트 시 회귀값 흐름 전체를 검증하려면 추가해야 한다.
- **예상 수정 내용**: `_MOCK_PARTS` 내 각 항목에 `"predicted_value": 0.xx` 추가
  ```python
  {
      "raw_part_name": "left_cheek",
      ...
      "grade_value": 2,
      "predicted_value": 0.73,   # 추가
      "severity": "moderate",
      "confidence_score": 0.82,
  },
  ```
- **테스트 포인트**: remote 모드(`AI_INFERENCE_MODE=remote`)로 이미지 업로드 후 `predicted_value`가 정상 저장되는지 확인.

### `app/services/recommendation_service.py`

- **수정 필요 여부**: 불필요 (현재 단계)
- **수정 이유**: 현재 추천 로직은 `r.severity` 문자열 기반으로만 동작하므로 `predicted_value`나 `measured_value`를 직접 사용하지 않는다. AI 서버 또는 json_parser에서 severity를 결정해 저장하는 현재 구조에서는 수정 불필요.
- **예상 수정 내용**: 없음. 단, 향후 "predicted_value 기반 severity 재계산" 로직이 필요해지면 `worst` 딕셔너리 구성 전 단계에서 추가한다.
- **테스트 포인트**: 회귀값 반영 후에도 추천 생성이 기존과 동일하게 동작하는지 회귀 테스트.

### `app/models/skin_part_result.py`

- **수정 필요 여부**: 불필요
- **수정 이유**: `measured_value`(라인 33), `predicted_value`(라인 34) 컬럼이 이미 `Float(precision=53), nullable=True`로 정의되어 있다. DB migration 및 ORM 모델 모두 준비 완료 상태.
- **예상 수정 내용**: 없음.
- **테스트 포인트**: `alembic upgrade head` 재실행 없이 기존 DB 컬럼을 그대로 사용.

### `app/routers/analysis.py`

- **수정 필요 여부**: 불필요
- **수정 이유**: `get_session_report()`는 `report_service.get_report(db, session_id, current_user.id)`를 호출하고 `response_model=ReportResponse`만 선언한다. 실제 응답 조립은 `report_service.py`가 전담하므로 router 수정 불필요.
- **예상 수정 내용**: 없음.
- **테스트 포인트**: 없음.

### `app/schemas/analysis.py`

- **수정 필요 여부**: 불필요
- **수정 이유**: `SessionCreateRequest`와 `SessionCreateResponse`만 포함하며 리포트 응답 구조와 무관하다.
- **예상 수정 내용**: 없음.
- **테스트 포인트**: 없음.

### `scripts/run_test.py`

- **수정 필요 여부**: 조건부 (검증 강화 목적)
- **수정 이유**: 현재 6단계 DB 조회에서 `display_part_name, issue_type, severity`만 출력한다. 회귀값 검증을 위해 `predicted_value, measured_value` 컬럼 조회를 추가하면 유용하다.
- **예상 수정 내용**: 라인 121~125의 SQL 쿼리에 `predicted_value, measured_value` 컬럼 추가 및 출력.
- **테스트 포인트**: 이미지 업로드 후 스크립트 실행 시 `predicted_value` 값이 표시되는지 확인.

---

## 4. 구현 순서

### ✅ 1단계 완료: `app/schemas/image_upload.py` — PartResult 스키마 확장

`PartResult`에 `predicted_value: Optional[float] = None`과 `measured_value: Optional[float] = None` 추가 완료. 이 수정이 선행되지 않으면 이후 모든 단계가 동작하지 않는다.

### ✅ 2단계 완료: `app/services/image_service.py` — SkinPartResult 저장 블록 수정

라인 127~141의 `SkinPartResult(...)` 생성 블록에 `predicted_value=part.predicted_value`, `measured_value=part.measured_value` 추가 완료.

### ✅ 3단계 완료: `app/schemas/report.py` — IssueItem 스키마 확장

`IssueItem`에 `predicted_value: Optional[float] = None`과 `measured_value: Optional[float] = None` 추가 완료.

### ✅ 4단계 완료: `app/services/report_service.py` — IssueItem 생성 블록 수정

`get_report()` 내 라인 66~75의 `IssueItem(...)` 생성 블록에 `predicted_value=r.predicted_value`, `measured_value=r.measured_value` 추가 완료.

### ✅ 5단계 완료: `app/utils/json_parser.py` — float 파싱 및 measured_value 필드 추가

**목적**: AI-Hub JSON annotation에서 소수점 원본 수치를 `measured_value`로 보존하면서, 기존 `grade_value` 등급 로직을 유지한다.

**수정 내용**:
- `ParsedPartResult` 데이터클래스에 `measured_value: float | None = None` 필드 추가
- `parse_annotations()` 내 라인 121의 `grade = int(raw_value)`를 아래와 같이 변경:
  ```python
  raw_float = float(raw_value)          # 원본 float 보존
  grade     = int(raw_float)            # 기존 grade_value 생성 방식 유지
  ```
- `ParsedPartResult` 생성 시 `measured_value=raw_float` 추가

**severity 계산**: 기존과 동일하게 `grade_to_severity(grade)`를 사용한다. `measured_value` 기준 재계산은 이번 단계에서 진행하지 않는다.

**주의**: `json_parser.py` 수정 후 6단계(`dev_json_service.py`)를 반드시 이어서 수행해야 DB에 반영된다. parser만 수정하면 `ParsedPartResult`에는 값이 있지만 DB에는 저장되지 않는다.

### ✅ 6단계 완료: `app/services/dev_json_service.py` — SkinPartResult 저장 블록 수정 (dev JSON 경로)

**목적**: 5단계에서 `json_parser.py`가 파싱한 `measured_value`를 실제 DB에 저장한다. 이미지 inference 경로(`image_service.py`, 2단계 완료)와 dev JSON 경로의 저장 결과를 일관되게 만든다.

**수정 내용**: `dev_json_service.py` 라인 59~72의 `SkinPartResult(...)` 생성 블록에 `measured_value=part.measured_value` 추가. 5단계 완료 후 수행.

**주의**: `dev.py` router 자체는 수정 불필요 — 위임 호출만 있다. dev JSON 경로에서는 `predicted_value`가 아닌 `measured_value` 중심으로 저장한다. `predicted_value`는 이미지 기반 AI 모델 예측 경로에서 사용하는 컬럼이다.

---

## 4-1. 5~6단계 구현 전 재확인 항목 (1~4단계 완료 현황)

5단계(`json_parser.py`)와 6단계(`dev_json_service.py`) 구현 전, 아래 1~4단계 완료 항목을 재확인한다. 모두 확인된 상태여야 5~6단계 구현 후 dev JSON 경로의 `measured_value`가 파싱 → DB 저장 → 리포트 응답 전체 흐름에서 일관되게 동작한다.

1. **`app/schemas/image_upload.py` (1단계 완료)**
   - `PartResult`에 `predicted_value: Optional[float] = None` 있는지 확인
   - `PartResult`에 `measured_value: Optional[float] = None` 있는지 확인

2. **`app/services/image_service.py` (2단계 완료)**
   - `SkinPartResult(...)` 블록에 `predicted_value=part.predicted_value` 있는지 확인
   - `SkinPartResult(...)` 블록에 `measured_value=part.measured_value` 있는지 확인

3. **`app/schemas/report.py` (3단계 완료)**
   - `IssueItem`에 `predicted_value: Optional[float] = None` 있는지 확인
   - `IssueItem`에 `measured_value: Optional[float] = None` 있는지 확인

4. **`app/services/report_service.py` (4단계 완료)**
   - `IssueItem(...)` 생성 블록에 `predicted_value=r.predicted_value` 있는지 확인
   - `IssueItem(...)` 생성 블록에 `measured_value=r.measured_value` 있는지 확인

---

### ✅ 7단계 완료: `app/services/inference_service.py` — mock 데이터에 predicted_value 추가

`_run_mock()`의 7개 `PartResult()`에 `predicted_value` 추가 완료. grade별 범위 기준: grade 0 → 0.18, grade 1 → 0.35~0.38, grade 2 → 0.62~0.67, grade 3 → 0.87.

### ✅ 8단계 완료: `scripts/dummy_ai_server.py` — 더미 서버 응답에 predicted_value 추가

`_MOCK_PARTS` 딕셔너리 7개 항목 전체에 `"predicted_value": 0.xx` 추가 완료. 7단계 mock 값과 동일.

### ✅ 9단계 완료: `docs/ai_inference_contract.md` — 계약 문서 업데이트

`parts[]` 필드 목록에 `predicted_value: float (Optional)`, `measured_value: float (Optional)` 추가, 두 필드 차이 설명, 하위 호환성 명시, severity 계산 기준, 값 범위 TODO 섹션 추가 완료.

---

## 5. 주요 주의사항

### 하위 호환 유지

`PartResult.predicted_value`와 `IssueItem.predicted_value`를 반드시 `Optional[float] = None`으로 정의해야 한다. 기존 AI 서버 또는 클라이언트가 해당 필드를 포함하지 않아도 동작해야 한다. `None`이 JSON 응답에 `null`로 직렬화되므로 기존 프론트엔드 코드는 영향받지 않는다.

### json_parser.py의 소수점 절삭 문제

현재 `int(raw_value)` 코드는 소수점을 **실제로 절삭**한다. Python에서 `int(2.7)`은 `2`이며 반올림이 아닌 절삭(truncation)이다. AI-Hub annotation에 `"l_cheek_pore": 2.73`이 들어오면 `grade_value=2`가 되고 `0.73`의 정보는 완전히 손실된다. 수정 시 반드시 `float()` 먼저 파싱 후 `int()` 변환 순서를 따라야 한다.

### dev_json_service.py — 확인 완료, 수정 필요

`app/routers/dev.py`는 라우터 위임만 하며 수정 불필요. 실제 `ParsedPartResult` → `SkinPartResult` 저장은 `app/services/dev_json_service.py` 라인 59~72에서 이루어진다. 해당 블록에 `measured_value` 필드가 없어 dev JSON 경로에서 항상 NULL이 저장된다. `json_parser.py` 수정 후 6단계에서 반드시 함께 수정해야 이미지 업로드 경로와 dev JSON 경로의 저장 결과가 일치한다.

### SkinPartResult ORM과 DB migration

ORM 모델(`skin_part_result.py`)과 DB 테이블 모두 이미 `measured_value`, `predicted_value` 컬럼이 존재하므로 **Alembic migration 추가 불필요**. `alembic upgrade head` 재실행 없이 바로 저장 가능.

### recommendation_service.py는 severity 기반이므로 무관

현재 추천 로직은 `r.severity` 문자열만 사용한다. `predicted_value` 저장이 완료되어도 추천 결과는 변하지 않는다. 향후 predicted_value → severity 재계산이 필요하면 별도 단계로 분리하여 구현한다.

### report_service.py가 리포트 응답의 실제 생성 위치

`analysis.py` router의 `get_session_report()`는 `report_service.get_report()` 호출만 하고 응답을 직접 조립하지 않는다. 따라서 `IssueItem` 생성 코드는 반드시 `report_service.py`에서만 수정한다. router는 수정 불필요.

### grade_value는 현 단계에서 필수(required) 유지

`PartResult.grade_value`는 `int`(필수)로 유지한다. AI 서버와의 인터페이스 계약이 아직 확정되지 않았으며, 현재 모든 경로(mock, remote, dev JSON)에서 정수 grade 값이 항상 제공된다. 순수 회귀 모델로 전환하여 grade를 제공하지 않는 경우가 생기면 그 시점에 AI 팀과 합의 후 `Optional[int] = None`으로 변경한다. 이 구현에서는 `predicted_value`와 `measured_value`만 `Optional[float] = None`으로 추가한다.

### recommendation_service.py는 이 구현 범위에서 제외

`app/services/recommendation_service.py`는 `r.severity` 문자열 기반으로만 동작하며, 이 구현에서 수정하지 않는다. `predicted_value`/`measured_value` 저장이 완료되어도 추천 결과는 변하지 않는다. 향후 predicted_value → severity 재계산이 필요하면 별도 구현 계획을 수립한다.

### grade_value 필드의 nullable 여부 (향후 참고)

ORM 모델에서 `grade_value: Mapped[int | None] = mapped_column(Integer, nullable=True)`로 DB 컬럼은 nullable이다. 그러나 `PartResult` Pydantic 스키마는 `grade_value: int`(필수)다. 이 불일치는 현재 의도된 설계이며, AI 계약이 바뀌기 전까지 스키마 쪽을 필수로 유지한다.

### measured_value와 grade_value 관계 — 원본 수치 보존

AI-Hub JSON 또는 피부 측정 장비에서 `2.73` 같은 소수점 값이 들어오면, 단순히 `grade_value=2`로만 저장해서는 안 된다.

- `grade_value=2`: **등급값**. `int(2.73) = 2`로 생성. 추천 로직 및 severity 계산에 사용한다. 기존 서비스 흐름 호환용이다.
- `measured_value=2.73`: **원본 측정값**. `float(raw_value)`로 보존. 추후 프론트 리포트에서 사용자에게 직접 표시할 수 있다.

```json
{
  "metric_name": "pore",
  "metric_display_name": "모공",
  "measured_value": 2.73,
  "grade_value": 2,
  "severity": "moderate"
}
```

두 값은 독립적이므로 반드시 별도 컬럼에 저장한다. `grade_value`만 저장하면 `0.73`의 정보는 완전히 손실된다.

### json_parser.py와 dev_json_service.py의 역할 구분

두 파일은 반드시 함께(5단계 → 6단계 순서로) 구현해야 한다.

**`json_parser.py` (5단계)의 역할:**
- AI-Hub JSON annotation 값을 파싱한다.
- `raw_value`를 `float(raw_value)`로 먼저 변환하여 원본 수치를 보존한다.
- `grade_value`는 `int(raw_float)`로 기존 방식대로 생성한다.
- `measured_value`에는 `raw_float` 원본 값을 저장한다.
- 결과물: `ParsedPartResult(grade_value=2, measured_value=2.73, severity="moderate")`

**`dev_json_service.py` (6단계)의 역할:**
- `json_parser.py`가 만든 `ParsedPartResult`를 `SkinPartResult`로 DB에 저장한다.
- `ParsedPartResult.measured_value`를 `SkinPartResult.measured_value`로 매핑한다.

**경계 주의:** `json_parser.py`만 수정하면 파싱 결과 객체에만 `measured_value`가 존재하고 DB에는 저장되지 않는다. 6단계 `dev_json_service.py`가 함께 수정되어야 DB에 반영된다. 두 단계를 분리해서 구현하면 안 된다.

### severity 계산 기준 — 현재 단계

현재 단계에서는 **`severity`를 `measured_value` 기준으로 새로 계산하지 않는다.**

이유:
- `recommendation_service`가 `severity` 기반으로 동작하고 있다.
- 지표별 `measured_value` 임계값이 아직 확정되지 않았다.
- 수분, 탄력, 주름, 모공은 값이 클수록 좋은지/나쁜지가 지표별로 다를 수 있다 (수분: 낮을수록 건조, 주름 roughness: 높을수록 심함).
- 이번 구현에서는 기존 `grade_value → grade_to_severity(grade)` 흐름을 유지한다.

**추후 고도화:** 지표별 임계값과 방향성이 확정되면 `measured_value` 또는 `predicted_value` 기준으로 severity를 더 정교하게 계산할 수 있다. 이 작업은 별도 구현 계획에서 진행한다.

### TODO — 이번 구현 범위에서 제외되는 항목

- `measured_value` 프론트 표시 UI 정책 미결정: 게이지, 텍스트 표시, 전문가 모드 등 프론트 활용 방식이 미정이다.
- `measured_value` 기준 severity 재계산: 지표별 임계값 확정 후 별도 작업으로 진행한다.
- dev JSON 경로의 `predicted_value` 컬럼: dev JSON 경로에서는 `measured_value` 중심으로 저장한다. `predicted_value`는 이미지 기반 AI 모델 예측 경로용 컬럼이다.

---

## 6. 테스트 계획

### 단계 1~2 완료 후 (스키마 + DB 저장 수정)

1. 서버 재시작 (`python -m uvicorn app.main:app --reload`)
2. 이미지 업로드 API 호출: `POST /analysis/sessions/{id}/images`
3. 응답 `inference_result.parts[].predicted_value`가 null 또는 float 값인지 확인
4. DB 직접 조회:
   ```sql
   SELECT id, display_part_name, issue_type, grade_value, predicted_value, measured_value
   FROM skin_part_results WHERE session_id = ?;
   ```
5. `predicted_value` 컬럼에 NULL이 아닌 값이 저장되는지 확인 (mock 데이터 수정 후)

### 단계 3~4 완료 후 (리포트 응답 수정)

1. `GET /analysis/sessions/{id}/report` 호출
2. 응답 JSON의 `part_reports[].issues[].predicted_value`가 존재하는지 확인
3. DB의 `skin_part_results.predicted_value`와 응답값이 일치하는지 비교

### 단계 5~6 완료 후 (json_parser + dev_json_service 수정)

**float 보존 테스트 — dev JSON 경로:**

```
POST /dev/analysis/sessions/{session_id}/json
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "json_items": [
    {
      "info": {"filename": "test.jpg", "id": "0001", "gender": "F", "age": 28},
      "images": {"facepart": 5, "angle": 0, "width": 2136, "height": 3216, "bbox": [712, 676, 1835, 1139]},
      "annotations": {
        "l_cheek_pore": 2.73,
        "r_cheek_pore": 1.0,
        "l_perocular_wrinkle": 3.91
      }
    }
  ]
}
```

**기대 결과 (DB 직접 조회):**

```sql
SELECT display_part_name, grade_value, measured_value
FROM skin_part_results
WHERE session_id = ?
ORDER BY id;
```

| display_part_name | grade_value | measured_value |
|---|---|---|
| 왼쪽 볼 | 2 | 2.73 |
| 오른쪽 볼 | 1 | 1.0 |
| 왼쪽 눈가 | 3 | 3.91 |

`grade_value=2`이고 `measured_value=2.73`이어야 한다 — `int(2.73)=2` 절삭이 발생하더라도 원본 float은 별도 보존된다. `measured_value=2.0`(잘못된 반올림)이나 `NULL`이 나오면 수정 실패다.

### 단계 7~8 완료 후 (mock/remote 서버 데이터 추가)

1. mock 모드: `AI_INFERENCE_MODE=mock`으로 이미지 업로드 후 `predicted_value` 저장 확인
2. remote 모드: dummy AI 서버 실행 후 `AI_INFERENCE_MODE=remote`로 이미지 업로드 후 `predicted_value` 저장 확인
3. `scripts/run_test.py` 실행 후 전체 항목 통과 확인

### 전체 회귀 테스트

`scripts/run_test.py --mode mock` 실행 후 기존 기능(인증, 세션 생성, 이미지 업로드, 추천 생성, 리포트 조회) 전체가 정상 동작하는지 확인.

---

## 7. 문서 업데이트 대상

| 문서 경로 | 변경 내용 |
|---|---|
| `docs/ai_inference_contract.md` | `parts[]` 필드 목록에 `predicted_value: float (Optional)`, `measured_value: float (Optional)` 추가. 타입, 필수 여부, 범위(예: 0.0~1.0), 의미 명시. severity 계약 섹션에 회귀값 기반 매핑 옵션 추가. |
| `docs/agent_db_design_fixed.md` | `skin_part_results` 핵심 필드 목록에 `measured_value`와 `predicted_value` 항목 추가(현재 표에서 두 컬럼이 누락됨). `issue_type`에는 심각도 정보를 섞지 않는다는 기존 규칙과 함께 컬럼별 저장 목적 명시. |
| `docs/agent_api_design_fixed.md` | `POST /analysis/sessions/{session_id}/images` 응답 예시의 `parts[]`에 `predicted_value` 필드 추가. `GET /analysis/sessions/{session_id}/report` 응답 예시의 `issues[]`에 `predicted_value` 필드 추가. |
| `docs/agent_image_upload.md` | Response 섹션의 `inference_result.parts[]` 예시에 `predicted_value` 필드 추가. |
| `backend/AGENTS.md` | 현재 상태 항목에 회귀값 필드 저장 기능이 추가되었음을 반영. `measured_value`, `predicted_value` 컬럼 활용 상태로 업데이트. |
