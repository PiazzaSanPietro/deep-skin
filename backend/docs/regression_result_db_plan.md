# 회귀 분석 결과 DB 반영 계획

## 1. 배경

AI 피부 분석 모델은 크게 두 가지 출력 방식을 가질 수 있다.

- **분류(classification) 방식**: 결과를 이미 등급(0, 1, 2, 3 등 정수)으로 내보내며, 백엔드는 이 등급을 severity 문자열로 변환한다.
- **회귀(regression) 방식**: 모델이 연속형 실수(예: 0.0~1.0 또는 0.0~100.0)를 출력하고, 백엔드 또는 AI 서버가 이 수치를 등급/severity로 매핑한다.

현재 백엔드는 분류 방식 기준의 `grade_value(int)`와 `severity(string)`만을 inference 계약에 포함한다. 향후 회귀 모델 결과(연속형 수치)를 받아 저장하거나 UI에서 활용하려면 추가 설계가 필요하다. 이 문서는 현재 코드/문서 상태를 조사하고, 회귀값 DB 반영 방안을 제시한다.

---

## 2. 현재 문서/코드 상태 요약

| 항목 | 현재 상태 |
|---|---|
| inference contract 스키마 | `grade_value(int)`, `severity(str)`, `confidence_score(float)` — 회귀 연속값 필드 없음 |
| `PartResult` Pydantic 스키마 | 동일. `regression_value` 또는 `measured_value` 필드 없음 |
| `json_parser.py` | AI-Hub annotation 값을 `int(raw_value)`로 파싱 → `grade_value`로 저장. 연속형 float 파싱 경로 없음 |
| `SkinPartResult` ORM 모델 | `grade_value(int)`, `measured_value(float)`, `predicted_value(float)` 컬럼 존재 (nullable). `confidence_score(float)` 있음 |
| `image_service.py` 저장 로직 | `part.grade_value`, `part.severity`, `part.confidence_score`만 저장. `measured_value`, `predicted_value`는 저장하지 않음 |
| `report.py` 스키마 `IssueItem` | `grade_value(Optional[int])` 포함. 회귀 연속값 필드 없음 |
| Alembic migration 이력 | `measured_value`, `predicted_value` 컬럼이 0003에서 이미 생성됨. 별도의 `regression_value` 컬럼은 없음 |

---

## 3. 현재 DB 구조 (skin_part_results 관련 컬럼 목록)

`skin_part_results` 테이블 전체 컬럼 (migration 0003 기준):

| 컬럼 | 타입 | Nullable | 설명 |
|---|---|---|---|
| `id` | BigInteger | No | PK |
| `session_id` | BigInteger | No | FK → analysis_sessions |
| `user_id` | BigInteger | No | FK → users |
| `image_id` | BigInteger | Yes | FK → uploaded_images (이미지 기반 결과) |
| `json_record_id` | BigInteger | Yes | FK → skin_json_records (개발용 JSON 기반 결과) |
| `raw_part_name` | String(50) | No | 모델 원본 부위명 |
| `display_part_name` | String(50) | No | UI 표시용 부위명 |
| `metric_name` | String(50) | No | 지표 key |
| `metric_display_name` | String(50) | No | 지표 표시명 |
| `grade_value` | Integer | Yes | 분류 등급 정수값 (0, 1, 2, 3) |
| `measured_value` | Float(53) | Yes | **회귀 연속값 저장 후보 A** — 측정/예측 실수값 |
| `predicted_value` | Float(53) | Yes | **회귀 연속값 저장 후보 B** — 예측 실수값 |
| `confidence_score` | Float(53) | Yes | 모델 신뢰도 |
| `severity` | String(30) | No | normal / mild / moderate / severe |
| `issue_type` | String(100) | No | 이슈 종류 key |
| `reason_text` | Text | Yes | 현재 미사용 |
| `model_name` | String(100) | Yes | 추론 모델명 |
| `model_version` | String(100) | Yes | 추론 모델 버전 |
| `created_at` | DateTime | No | 생성 시각 |

**핵심 발견**: `measured_value`와 `predicted_value` 컬럼이 이미 테이블에 존재한다(nullable). 이 컬럼은 회귀 연속값 저장을 위해 미리 설계된 자리다. 현재 어떤 서비스 코드에서도 이 컬럼에 값을 쓰지 않는다.

---

## 4. AI inference 응답에서 회귀값 구조 (현재 schema 기준)

`app/schemas/image_upload.py`의 `PartResult` 클래스:

```python
class PartResult(BaseModel):
    raw_part_name: str
    display_part_name: str
    metric_name: str
    metric_display_name: str
    issue_type: str
    grade_value: int        # 분류 등급 정수
    severity: str           # normal / mild / moderate / severe
    confidence_score: float # 신뢰도
```

현재 schema에는 회귀 연속값 필드가 없다.

현재 AI inference contract(`ai_inference_contract.md`)에 정의된 응답 필드도 동일하며,
`regression_value`, `measured_value`, `predicted_value` 등의 연속형 수치 필드를 포함하지 않는다.

mock 결과(`inference_service._run_mock()`)도 모두 정수 `grade_value`와 문자열 `severity`만 사용한다.

즉, 현재 백엔드 inference 응답 구조는 아래 값만 받는 상태다.

```
grade_value       → 등급화된 정수값
severity          → UI/추천용 심각도
confidence_score  → 모델 신뢰도
```

반면 피부 측정 장비 기반 데이터 또는 AI-Hub JSON에는 수분, 탄력, 주름, 모공처럼
연속형 수치로 해석해야 하는 값이 포함될 수 있다.

예를 들어 아래 값들은 단순 등급값이라기보다 원본 측정값 또는 연속형 분석값일 가능성이 있다.

```
forehead_moisture, l_cheek_moisture
R0 ~ R9, Q0 ~ Q3
Ra, Rmax, Rt, Rz, Rp, Rv, Rq, R3z
l_cheek_pore
```

따라서 현재 schema만으로는 이런 연속형 수치를 보존하기 어렵다.
회귀값을 실제로 반영하려면 `grade_value`와 별도로 `measured_value` 또는 `predicted_value`를 받을 수 있도록 확장해야 한다.

---

## 5. grade_value로 처리 가능한지 검토 (Case A / Case B 판단)

### Case A: 회귀값이 이미 grade_value에 등급으로 변환되어 들어온다

이 경우 AI 서버 또는 AI-Hub 파이프라인이 연속형 수치를 이미 0/1/2/3 등급으로 매핑한 뒤 `grade_value`로 전달한다.

예시:
```json
{
  "metric_name": "pore",
  "grade_value": 2,
  "severity": "moderate"
}
```

이 경우 현재 백엔드 구조(PartResult → SkinPartResult)로도 처리할 수 있다.
다만 원본 연속형 수치는 저장되지 않으므로, 세밀한 분석값은 손실된다.

### Case B: 연속형 수치가 별도로 존재한다

AI 서버 또는 AI-Hub JSON에 `grade_value`와 별도로 연속형 실수 수치가 존재하는 경우다.

예시 (장비 기반 원본 측정값):
```json
{
  "metric_name": "moisture",
  "measured_value": 55.667,
  "grade_value": 1,
  "severity": "mild"
}
```

예시 (이미지 기반 모델 예측 회귀값):
```json
{
  "metric_name": "moisture",
  "predicted_value": 55.667,
  "grade_value": 1,
  "severity": "mild"
}
```

이 값은 세밀한 피부 상태 변화 추적, 게이지 시각화, 추이 그래프, 정밀 분석에 활용될 수 있다.

현재 DB에는 `skin_part_results.measured_value`, `skin_part_results.predicted_value` 컬럼이 이미 존재하지만,
현재 schema와 service 저장 로직에서는 이 값을 받거나 저장하지 않는다.

### 현재 코드 기준 판단: **현재는 Case A 상태, 향후 Case B 확장 필요**

현재 inference contract, PartResult 스키마, mock 결과, json_parser 모두 분류 등급 정수인 `grade_value` 기반이다.
**따라서 현재 코드 기준으로는 Case A 상태이다.**

하지만 현재 JSON에 들어오는 일부 값이 피부 측정 장비 기반 연속형 수치라면,
`grade_value`만으로 저장하는 것은 정보 손실이 발생할 수 있다.

피드백 반영을 위해 회귀 연속값을 실제로 저장하려면 **Case B 확장이 필요하다.**

다행히 DB에는 이미 `measured_value`, `predicted_value` 컬럼이 존재하므로
**신규 migration 없이 기존 컬럼을 활용하는 방향이 적절하다.**

권장 방향:

```
원본 장비 측정값 / AI-Hub 원천 수치 → measured_value
딥러닝 모델 예측 회귀 수치          → predicted_value
등급화된 정수값                     → grade_value
UI 표시 및 추천용 심각도            → severity
```

---

## 5-1. 피부 측정 장비 기반 연속형 수치 검토

현재 JSON에 들어오는 일부 값은 단순 분류 등급이 아니라 **피부 측정 장비 기반의 연속형 수치**로 볼 수 있다.
수분, 탄력, 주름, 모공 관련 값은 `0~3` 범위의 등급값이 아니라 장비 측정값 또는 영상 분석 기반 수치일 가능성이 높다.
따라서 이런 값들을 모두 `grade_value`에만 저장하면 **원본 수치 정보가 손실**될 수 있다.

### 측정 항목별 예시

#### 수분 (`moisture`)
- 관련 키: `forehead_moisture`, `l_cheek_moisture` 등
- 각질층 수분량을 나타내는 연속형 측정값으로 볼 수 있다.
- Corneometer 계열 장비 측정값과 유사한 형태의 임의 단위 수치(예: 0~120 범위)일 가능성이 있다.

#### 탄력 (`elasticity`)
- 관련 키: `R0` ~ `R9`, `Q0` ~ `Q3`
- 피부 탄력, 회복력, 점탄성 등을 나타내는 연속형 측정 파라미터로 볼 수 있다.
- Cutometer 계열 장비에서 사용하는 R parameter, Q parameter와 유사한 형태다.
- 각 파라미터의 의미와 범위는 데이터 명세 확인이 필요하다.

#### 주름 (`wrinkle`)
- 관련 키: `Ra`, `Rmax`, `Rt`, `Rz`, `Rp`, `Rv`, `Rq`, `R3z`
- 피부 표면 거칠기 또는 주름 깊이 관련 연속형 파라미터로 볼 수 있다.
- 3D 표면 측정 장비나 피부 표면 분석 장비에서 사용하는 roughness 계열 지표와 유사한 형태다.

#### 모공 (`pore`)
- 관련 키: `l_cheek_pore` 등
- 영상 분석 기반 모공 개수, 면적, 픽셀값 등으로 볼 수 있는 연속형 또는 계수형 수치일 가능성이 있다.

### DB 저장 방향 (컬럼 매핑 권장안)

| 저장 대상 | 권장 컬럼 | 예시 |
|---|---|---|
| 원본 장비 측정값 / AI-Hub JSON 원천 수치 | `measured_value` | 수분값 `55.667`, 탄력 R2 `0.73` |
| 딥러닝 모델이 예측한 회귀 수치 | `predicted_value` | 이미지 추론 결과 `0.731` |
| 등급화된 정수값 | `grade_value` | `0`, `1`, `2`, `3` |
| UI 표시 및 추천 로직용 심각도 | `severity` | `"normal"`, `"mild"`, `"moderate"`, `"severe"` |

### 저장 예시 JSON

**원본 측정값을 저장하는 경우 (`measured_value` 활용):**

```json
{
  "display_part_name": "이마",
  "metric_name": "moisture",
  "metric_display_name": "수분",
  "measured_value": 55.667,
  "predicted_value": null,
  "grade_value": 1,
  "severity": "mild"
}
```

**모델 예측 회귀값을 저장하는 경우 (`predicted_value` 활용):**

```json
{
  "display_part_name": "이마",
  "metric_name": "moisture",
  "metric_display_name": "수분",
  "measured_value": null,
  "predicted_value": 55.667,
  "grade_value": 1,
  "severity": "mild"
}
```

---

## 6. DB 변경 필요 여부 및 근거

### 결론: **DB 컬럼 추가는 불필요. 이미 준비된 컬럼을 활용하면 된다.**

근거:

1. `skin_part_results.measured_value (Float, nullable)` — 측정된 연속형 회귀값 저장에 즉시 사용 가능
2. `skin_part_results.predicted_value (Float, nullable)` — 모델 예측 연속형 회귀값 저장에 즉시 사용 가능
3. 두 컬럼 모두 migration 0003에서 생성되었으며 현재 DB에 실제로 존재한다

**회귀값을 `measured_value` 또는 `predicted_value` 중 어느 컬럼에 저장할지만 결정하면 된다.**

권장 매핑:
- `measured_value`: 장비/센서/이미지 분석에서 직접 측정된 수치 (AI-Hub 데이터셋 등)
- `predicted_value`: 딥러닝 모델이 예측한 회귀 수치 (실시간 추론 결과)

이미지 업로드 기반 추론에서는 `predicted_value`가 더 의미적으로 적합하다.

---

## 7. 권장 DB 설계안

### 7-1. 현재 컬럼 활용 (신규 migration 불필요)

기존 `skin_part_results` 테이블의 `predicted_value` 컬럼을 회귀 연속값 저장 용도로 공식 지정한다.

| 컬럼 | 저장 값 | 예시 |
|---|---|---|
| `grade_value` | 분류 등급 정수 (AI 서버 또는 파서가 변환) | `2` |
| `predicted_value` | 회귀 모델 연속 수치 (AI 서버가 직접 출력) | `0.731` |
| `measured_value` | 장비/측정 기반 수치 (AI-Hub 원본 데이터 등) | `45.3` |
| `severity` | grade_value 또는 predicted_value 기반 변환 | `"moderate"` |
| `confidence_score` | 모델 신뢰도 | `0.82` |

### 7-2. severity 결정 로직

회귀값(`predicted_value`)에서 severity를 결정하는 로직을 백엔드에서 담당한다. 예시 임계값 (지표별로 조정 필요):

```
predicted_value < 0.25  → normal
predicted_value < 0.50  → mild
predicted_value < 0.75  → moderate
predicted_value >= 0.75 → severe
```

또는 AI 서버가 회귀값과 함께 severity를 직접 반환하도록 contract를 정한다 (현재 방식과 동일한 구조 유지 가능).

---

## 8. 향후 코드 수정이 필요한 파일 목록과 각 수정 내용 요약

우선순위 높은 순서로 정리한다.

### 1순위: `app/schemas/image_upload.py`

`PartResult`에 회귀값 필드를 추가한다.

```python
# 추가할 필드 (Optional로 하위 호환 유지)
predicted_value: Optional[float] = None   # 회귀 모델 연속 수치
measured_value: Optional[float] = None    # 측정 기반 수치
```

이 변경이 없으면 AI 서버가 회귀값을 응답해도 Pydantic validation에서 무시되거나 오류가 발생한다.

### 2순위: `app/services/image_service.py`

`SkinPartResult` 저장 블록에 `predicted_value`, `measured_value` 필드를 추가한다.

```python
db.add(SkinPartResult(
    ...
    grade_value=part.grade_value,
    predicted_value=part.predicted_value,   # 추가
    measured_value=part.measured_value,     # 추가
    severity=part.severity,
    confidence_score=part.confidence_score,
    ...
))
```

현재 이 두 필드는 저장되지 않으므로 DB에서 항상 NULL이다.

### 3순위: `app/utils/json_parser.py`

AI-Hub annotation 값이 float인 경우를 처리할 수 있도록 수정한다. 현재 `int(raw_value)`로만 변환하므로, 회귀 연속값이 annotation에 포함될 경우 소수점이 잘린다.

`ParsedPartResult`에도 `predicted_value: float | None` 필드 추가가 필요하다.

### 4순위: `docs/ai_inference_contract.md`

AI 서버가 회귀값을 응답할 경우 계약 문서에 `predicted_value` 필드를 공식 추가한다. 타입, 필수 여부, 범위, 의미를 명시해야 한다.

### 5순위: `app/schemas/report.py` 또는 `app/schemas/analysis.py`

리포트 API 응답에 사용 중인 실제 schema에 `predicted_value`, `measured_value` Optional 필드를 추가한다.

```python
class IssueItem(BaseModel):
    ...
    grade_value: Optional[int]
    predicted_value: Optional[float] = None   # 추가
    measured_value: Optional[float] = None    # 추가
    reason: Optional[str]
```

**주의**: 실제 리포트 응답이 `app/schemas/report.py` 기준인지 `app/schemas/analysis.py` 기준인지는 구현 전에 반드시 확인해야 한다. import 경로와 `response_model`을 확인하여 실제 사용 중인 schema를 수정해야 한다.

### 6순위: `app/services/report_service.py` 또는 `app/routers/analysis.py`

리포트 응답 생성 위치를 확인한 뒤, `SkinPartResult.predicted_value` / `measured_value`를 읽어 응답에 포함시켜야 한다.

- `report_service.py`가 존재하면 해당 파일의 `IssueItem` 생성 블록에서 두 필드를 채운다.
- `report_service.py`가 없고 `analysis.py` router 내부에서 직접 응답을 조립한다면, 해당 위치에서 수정한다.
- 두 경우 모두 `SkinPartResult.predicted_value` / `measured_value` ORM 필드를 읽어 응답에 매핑하는 로직이 필요하다.

---

## 9. API 응답 변경안

### `POST /analysis/sessions/{session_id}/images` 응답

`inference_result.parts[]` 안의 각 파트 항목에 `predicted_value` 필드를 추가한다.

```json
{
  "inference_result": {
    "parts": [
      {
        "raw_part_name": "left_cheek",
        "issue_type": "pore",
        "grade_value": 2,
        "predicted_value": 0.731,
        "severity": "moderate",
        "confidence_score": 0.82
      }
    ]
  }
}
```

`predicted_value`는 Optional로 설정하여 AI 서버가 제공하지 않을 경우 null 허용.

### `GET /analysis/sessions/{session_id}/report` 응답

`part_reports[].issues[]`의 각 `IssueItem`에 `predicted_value`를 추가한다.

```json
{
  "part_reports": [
    {
      "issues": [
        {
          "issue_type": "pore",
          "severity": "moderate",
          "grade_value": 2,
          "predicted_value": 0.731,
          "reason": null
        }
      ]
    }
  ]
}
```

`predicted_value`가 null이면 기존 클라이언트와의 하위 호환이 유지된다.

---

## 10. 프론트 리포트 반영 방향

프론트엔드에서 회귀값 활용 방안:

1. **게이지/미터 시각화**: `predicted_value`(0.0~1.0)를 progress bar나 반원 게이지로 표시하여 단순 등급보다 세밀한 상태를 직관적으로 전달
2. **추이 그래프**: 세션별 `predicted_value` 비교를 통해 피부 개선/악화 추이를 연속형 그래프로 표현 가능 (`grade_value`만으로는 단계적 변화밖에 표현 불가)
3. **퍼센트 표기**: `predicted_value * 100`을 정수로 표기 (예: "73% 수준의 모공 상태")

현재는 `grade_value`와 `severity`만 응답에 포함되므로 프론트는 단계적 등급 표현만 가능하다. `predicted_value` 추가 후 선택적으로 사용하도록 한다.

---

## 11. 작업 순서 (우선순위 포함)

아래는 회귀값 DB 반영 전체 작업의 권장 실행 순서다.

### Phase 1: AI 서버 계약 확정 (선행 필수)

**AI 팀과 먼저 확인해야 할 사항:**
- 실제 모델이 회귀(연속형) 출력을 제공하는가, 분류(등급) 출력을 제공하는가?
- 회귀 출력이면 범위는 0~1인가, 0~100인가, 기타인가?
- `grade_value`와 `predicted_value`를 동시에 응답할 것인가, 아니면 `predicted_value`만 응답하고 백엔드에서 변환할 것인가?

이 결정 이전에 백엔드 코드를 수정하면 불필요한 재작업이 발생한다.

### Phase 2: 스키마 및 서비스 수정 (코드 변경)

1. `app/schemas/image_upload.py` — `PartResult`에 `predicted_value`, `measured_value` 추가 (Optional)
2. `app/services/image_service.py` — `SkinPartResult` 저장 시 두 필드 채우기
3. `app/utils/json_parser.py` — `ParsedPartResult`에 `predicted_value` 추가, float 파싱 지원
4. `app/schemas/report.py` — `IssueItem`에 `predicted_value` 추가
5. `app/services/report_service.py` — `IssueItem` 생성 시 `predicted_value` 채우기

### Phase 3: 문서 업데이트

6. `docs/ai_inference_contract.md` — `predicted_value` 필드 계약 추가
7. `docs/agent_db_design_fixed.md` — `measured_value`, `predicted_value` 컬럼 설명 업데이트

### Phase 4: 테스트 및 검증

8. mock 데이터에 `predicted_value` 추가 (`inference_service._run_mock()`)
9. dummy AI 서버(`scripts/dummy_ai_server.py`)에 `predicted_value` 필드 추가
10. report API 응답에 `predicted_value`가 올바르게 포함되는지 확인

---

## 12. 확인 필요 / TODO

### 구현 전 필수 확인 항목

#### 1. 리포트 응답을 생성하는 실제 파일 확인
- `app/services/report_service.py` — 파일이 존재하는지, 존재한다면 어떻게 `SkinPartResult`를 조회하는지
- `app/routers/analysis.py` — `GET /analysis/sessions/{session_id}/report` endpoint의 `response_model`이 무엇인지
- `app/schemas/analysis.py` — `part_reports`, `issues` 구조에서 `grade_value`가 어디에 포함되는지
- `app/schemas/report.py` — `IssueItem`이 실제로 사용되는 router가 어디인지

#### 2. 리포트 응답의 issues 구조 확인
- `grade_value`가 현재 어느 파일에서 응답에 포함되는지
- `SkinPartResult` ORM에서 어떤 필드를 읽고 있는지
- `predicted_value` / `measured_value`를 추가할 정확한 위치가 어디인지

#### 3. AI 서버 응답 계약 확인 (AI 팀과 협의 필요)
- `predicted_value`만 내려줄지, `measured_value`도 함께 내려줄지
- `grade_value`와 `severity`도 동시에 내려줄지
- `predicted_value` 값의 범위: 0~1인지, 0~100인지, 지표별로 다른지

#### 4. JSON parser 회귀값 처리 가능 여부 확인
- AI-Hub annotation 값(`"l_cheek_pore": 2` 등)이 정수 등급인지, 소수점 회귀값인지 데이터 명세 확인
- 현재 `int(raw_value)` 처리로 소수점 값이 들어올 경우 절삭되는지 검증

---

### 개별 TODO

1. **`report_service.py` 미확인**: 이 파일을 읽지 않아 리포트 생성 서비스에서 `SkinPartResult`를 어떻게 읽는지 정확히 파악하지 못했다. Phase 2 작업 전 `app/services/report_service.py`를 반드시 확인해야 한다.

2. **AI 서버 출력 형식 미확정**: 현재 AI 팀과의 계약 문서에 회귀값 관련 내용이 없다. AI 서버가 실제로 어떤 형태로 결과를 내보낼지 확정이 필요하다.

3. **`measured_value` vs `predicted_value` 용도 구분**: 두 컬럼이 이미 DB에 있지만 어떤 컬럼에 어떤 종류의 회귀값을 넣을지 팀 내 합의가 필요하다. 현재 문서 어디에도 두 컬럼의 차이가 명시되어 있지 않다.

4. **severity 변환 임계값**: 회귀 수치를 severity로 변환할 임계값은 지표별로 다를 수 있다 (예: 모공과 주름의 0.5가 동일한 의미를 갖지 않을 수 있음). 지표별 임계값 테이블이 필요하다.

5. **AI-Hub JSON annotation의 회귀값 여부**: 현재 AI-Hub JSON에서 annotation 값(예: `"l_cheek_pore": 2`)이 정수 등급인지, 아니면 연속형 실수인지 데이터 명세 확인이 필요하다. `json_parser.py`는 현재 `int(raw_value)`로만 처리하므로 소수점 값이 들어오면 소수점이 잘린다.

6. **장비 기반 연속형 수치 데이터 명세 확인**: AI-Hub JSON의 수분, 탄력, 주름, 모공 값이 실제 장비 측정값인지 데이터 명세로 확인 필요하다.

7. **지표별 값의 범위 확인**:
   - `moisture` (수분): 값 범위가 0~120인지, 다른 단위인지
   - `elasticity` R/Q parameter: 각 파라미터의 의미와 범위
   - `wrinkle` roughness parameter (`Ra`, `Rmax`, `Rt`, `Rz` 등): 단위 및 범위
   - `pore` 값: 개수인지, 면적인지, 픽셀값인지

8. **지표별 방향성 확인**: 각 연속형 수치에서 값이 클수록 나쁜 상태인지, 작을수록 나쁜 상태인지 방향성을 지표별로 확인해야 severity 변환 임계값을 정의할 수 있다.

9. **연속형 수치 → grade_value / severity 변환 임계값 정의**: 장비 측정값 또는 회귀값에서 등급(0~3)과 severity(normal/mild/moderate/severe)로 변환하는 지표별 임계값 테이블이 별도로 필요하다.

---

## 13. 수정이 필요한 기존 문서 목록과 변경할 내용 요약

| 문서 경로 | 변경할 내용 |
|---|---|
| `docs/ai_inference_contract.md` | `PartResult` 응답 필드 목록에 `predicted_value: float (Optional)` 추가. `grade_value`와 `predicted_value` 중 어느 것이 필수인지 명시. 회귀값 범위(0~1 등) 명시 |
| `docs/agent_db_design_fixed.md` | `skin_part_results` 핵심 필드 목록에 `measured_value`, `predicted_value` 설명 추가. 현재 표에서 두 컬럼이 누락되어 있음 |
| `docs/agent_api_design_fixed.md` | `GET /analysis/sessions/{session_id}/report` 응답의 `IssueItem` 예시에 `predicted_value` 필드 추가. `POST /analysis/sessions/{session_id}/images` 응답의 `parts[]` 예시에 `predicted_value` 필드 추가 |
| `docs/agent_image_upload.md` | Response 예시의 `inference_result.parts[]` 항목에 `predicted_value` 필드 추가 |

---

## 결론 요약

결론적으로 **DB migration은 현재 단계에서 필요하지 않다.**  
이미 존재하는 `skin_part_results.measured_value` / `predicted_value` 컬럼을 활용하는 방향이 적절하다.

다만 현재 코드는 `grade_value` 기반의 Case A 상태이므로,  
회귀 연속값을 실제로 반영하려면 inference schema, image 저장 service, JSON parser, report response 생성 로직을 Case B 방식으로 확장해야 한다.

특히 **report response 생성 위치는 아직 확정되지 않았으므로**,  
구현 전에 `report_service.py`, analysis router, report/analysis schema의 실제 사용 관계를 반드시 확인해야 한다.

추가로, AI-Hub JSON 또는 피부 측정 데이터에는 수분, 탄력, 주름, 모공 관련 **장비 기반 연속형 수치**가 포함될 수 있다.  
이 값들은 단순 분류 등급이 아니므로 `grade_value`만으로 저장하면 정보 손실이 발생할 수 있다.  
따라서 아래와 같이 컬럼을 분리하는 방향이 적절하다.

- 원본 측정값 → `measured_value`
- 모델 예측 회귀값 → `predicted_value`
- 등급화된 결과 → `grade_value`
- 화면 표시 및 추천용 단계 → `severity`
