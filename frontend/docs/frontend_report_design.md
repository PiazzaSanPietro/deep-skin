
# 7. `frontend/docs/frontend_report_design.md`

# Frontend Report Design Guide

## 목적

분석 리포트 화면에서 백엔드 응답을 사용자 친화적으로 표시하는 기준을 정의한다.

## 사용 API

```http
GET /analysis/sessions/{session_id}/report
```

재로그인 후처럼 프론트의 `current_session_id`가 없는 경우에는 아래 API로 최신 완료 리포트를 먼저 복구한다.

```http
GET /analysis/reports/latest
```

복구 성공 시 응답의 `session_id`를 `st.session_state["current_session_id"]`에 저장하고, 전체 응답을 `st.session_state["last_report"]`에 저장한 뒤 동일한 리포트 UI로 렌더링한다. 404가 반환될 때만 "분석 결과 없음" 상태를 표시한다.

## 리포트 응답 구조

주요 응답 구조는 다음과 같다.
```json
{
  "session_id": 1,
  "status": "completed",
  "overall_summary": {
    "status": "집중 관리 필요",
    "main_message": "눈가 부위의 주름, 볼 부위의 모공 관리가 필요합니다.",
    "main_issues": []
  },
  "part_reports": [
    {
      "display_part_name": "볼",
      "summary": "모공 관리가 필요합니다.",
      "issues": [
        {
          "metric_name": "pore",
          "metric_display_name": "모공",
          "issue_type": "pore",
          "severity": "moderate",
          "grade_value": 2,
          "predicted_value": 0.62,
          "measured_value": null,
          "reason": null
        }
      ],
      "recommendation": null
    }
  ]
}
```

## 화면 구성

### 1. 전체 요약 영역

표시 항목:
```
전체 상태
주요 메시지
주요 관리 필요 지표
분석 완료 상태
```

예시:
```
전체 분석 결과
집중 관리 필요
눈가 부위의 주름, 볼 부위의 모공 관리가 필요합니다.
```
### 2. 부위별 분석 결과

part_reports를 반복하여 카드로 표시한다.

각 카드 표시 항목:
```
display_part_name
summary
issues
recommendation
```

### 3. issue 표시 기준

issue에는 다음 값을 표시한다.
```
metric_display_name   ← 사용자에게 표시할 지표명
severity              ← 상태 배지
grade_value           ← 등급 숫자 (보조 표시)
predicted_value       ← 예측 수치 (있으면 표시)
measured_value        ← 측정 수치 (있으면 표시)
```

사용자에게는 issue_type보다 metric_display_name을 우선 표시한다.

예:
```
모공
주름
건조
처짐
색소침착
```

### 3-1. 상세 수치 표시 정책

`predicted_value`와 `measured_value`는 사용자 친화적 라벨로 표시한다.

**표시 우선순위:**

1. `measured_value`가 null이 아니면 → "측정값" 라벨로 표시
2. `measured_value`가 null이고 `predicted_value`가 null이 아니면 → "예측값" 라벨로 표시
3. 둘 다 null이면 → `grade_value` / `severity`만 표시 (기존과 동일)

**표시 예시 — 이미지 업로드 경로 (predicted_value 있음):**
```
모공
상태: 관리 필요
등급: 2단계
예측값: 0.62
```

**표시 예시 — dev JSON / AI-Hub 원본 측정값 경로 (measured_value 있음):**
```
모공
상태: 관리 필요
등급: 2단계
측정값: 2.73
```

**표시 예시 — 수치 없음 (기존 동작):**
```
모공
상태: 관리 필요
등급: 2단계
```

> 사용자 화면에서 `predicted_value` / `measured_value` 필드명을 그대로 노출하지 않는다. 반드시 "예측값" / "측정값" 라벨로 변환하여 표시한다.

### 4. severity 표시 기준
```
normal   → 양호
mild     → 약한 관리 필요
moderate → 관리 필요
severe   → 집중 관리 필요
```

### 컬러 기준:
```
normal   → green / blue
mild     → yellow
moderate → orange
severe   → red
```

### 5. 추천 정보 표시

recommendation 안의 값을 다음 영역으로 나누어 표시한다.

#### 추천 카테고리
```
recommendation.categories
```

chip 형태로 표시한다.

#### 추천 성분
```
recommendation.ingredients
```

성분명 기준 chip으로 표시한다.

#### 제외 성분
```
recommendation.excluded_ingredients
```

제외 성분이 있으면 붉은 계열 chip으로 표시한다.

reason_type이 있으면 다음처럼 표시한다.
```
allergy   → 알레르기 등록 성분
sensitive → 민감 피부 주의 성분
```

#### 관리 팁
```
recommendation.care_tips
```

체크리스트 형태로 표시한다.

### 6. normal 상태 표시

normal 상태도 리포트에 포함한다.

normal 상태는 “문제 없음”이 아니라 “현재 상태 유지 관리”로 표현한다.

예:
```
이마 부위는 전반적으로 양호한 상태입니다.
현재 상태 유지를 위해 보습과 자외선 차단을 권장합니다.
```

### 7. 표시하지 않을 값

아래 값은 사용자 화면에 기본 노출하지 않는다.
```
session_id
raw_part_name
model_name
model_version
confidence_score
```

confidence_score는 추후 “분석 신뢰도” 영역이 필요할 때만 표시한다.

아래 값은 **표시 가능** 값으로 분류하되, 사용자 친화적 라벨로 변환하여 표시한다.
```
predicted_value  →  “예측값”으로 표시
measured_value   →  “측정값”으로 표시
```

표시 여부는 3-1절 우선순위 기준을 따른다. 두 값이 모두 null이면 표시하지 않는다.

### 8. 리포트 없음 처리

리포트 API 응답 status가 pending, processing, failed일 수 있다.

#### pending
```
분석이 아직 시작되지 않았습니다.
```
#### processing
```
AI가 피부 상태를 분석 중입니다.
```

#### failed
```
분석에 실패했습니다. 이미지를 다시 업로드해주세요.
```

## Phase 2-2 상세 측정값 UI (2026-05-12 추가)

### 사용 API

```http
GET /analysis/sessions/{session_id}/metrics
```

리포트 조회 성공 후 동일 `session_id`로 호출한다. 실패해도 리포트 화면은 유지된다.

### 기본 모드 표시 항목

`is_dummy=false`인 메트릭 중 아래 항목만 표시한다.

| metric_group | metric_name | 표시명 |
|---|---|---|
| moisture | moisture | 수분 |
| pore | pore_count | 모공 개수 |
| pigmentation | pigmentation_count | 색소침착 개수 |
| acne | acne_count | 여드름 개수 |
| wrinkle | Ra | 주름 Ra |
| wrinkle | Rmax | 주름 Rmax |
| elasticity | R2 | 탄력 R2 |
| elasticity | R7 | 탄력 R7 |

### 전문가 모드 표시 항목

전문가 모드 토글(`st.toggle`)을 켜면 모든 metric을 표시한다.

- `is_dummy=true` 항목도 포함하되, `[모델 미학습]` 배지를 표시한다.
- R0~R9, Q0~Q3, Ra/Rmax/Rt/Rz/Rp/Rv/Rq/R3z 등 전체 표시.

### 좌우 부위 구분

동일한 `display_part_name`(예: 볼)에 `left_cheek` + `right_cheek` 두 부위가 합산될 경우
 "(좌)" / "(우)" 접미사를 붙인다.

예: "수분 (좌)" / "수분 (우)"

단방향 부위(이마, 턱, 미간 등)는 접미사 없이 표시한다.

### metric 값 포맷

- `value_type="count"` → 정수 표시 (예: `12`)
- 그 외 → 소수 셋째 자리 (예: `0.832`)

### 표시하지 않는 경우

- `parts=[]` (mock/remote flat 세션)
- metrics API 실패
- 해당 부위에 metric이 없음

이 경우 "상세 측정값" 섹션 자체를 숨기고, 기존 리포트는 그대로 표시한다.

## Phase 2-4 추이 그래프 UI (2026-05-12 추가)

### 사용 API

```http
GET /analysis/metrics/trends?raw_part_name=...&metric_group=...&metric_name=...&limit=10
```

### 표시 위치

상세 분석 expanders 아래, 맞춤 추천 결과 위에 "피부 측정 추이" 섹션을 배치한다.

### 기본 모드 표시 지표

| raw_part_name | metric_group | metric_name | 표시명 |
|---|---|---|---|
| forehead | moisture | moisture | 이마 수분 |
| left_cheek | pore | pore_count | 왼쪽 볼 모공 개수 |
| right_cheek | pore | pore_count | 오른쪽 볼 모공 개수 |
| left_eye | wrinkle | Ra | 왼쪽 눈가 주름 Ra |
| right_eye | wrinkle | Ra | 오른쪽 눈가 주름 Ra |
| forehead | elasticity | R2 | 이마 탄력 R2 |
| left_cheek | elasticity | R2 | 왼쪽 볼 탄력 R2 |
| right_cheek | elasticity | R2 | 오른쪽 볼 탄력 R2 |

전문가 모드에서 더 많은 지표를 선택할 수 있도록 향후 확장 예정.

### 표시 기준

| 상황 | 동작 |
|---|---|
| trend 2개 이상 | `st.line_chart` (x=날짜, y=값) |
| trend 1개 | 현재 측정값과 날짜 표시 + "2회 이상 분석 필요" 안내 |
| trend 0개 | "분석 데이터가 없습니다." 안내 |
| API 실패 | "데이터를 불러오지 못했습니다." 안내, 리포트 유지 |

### 로딩 방식

"추이 그래프 보기" 토글을 켤 때 한 번만 로드한다 (`st.session_state[f"trends_{session_id}"]` 캐시).

### 전문가 모드 지표 선택 UI (Phase 3-B 추가, 2026-05-12)

"추이 그래프 보기" 토글이 켜진 상태에서 전문가 모드 토글도 켜져 있으면
기본 8개 차트 아래에 **지표 직접 선택** 섹션이 표시된다.

구성:

| 요소 | 내용 |
|---|---|
| 부위 selectbox | `_TREND_METRIC_OPTIONS` 키 목록 (이마/왼쪽 볼/…) |
| 지표 그룹 selectbox | 선택 부위에 맞는 그룹 목록 (수분/탄력/주름/…) |
| 세부 지표 selectbox | 선택 그룹에 맞는 metric_name 목록 |
| 추이 조회 버튼 | 선택된 조합으로 `GET /analysis/metrics/trends` 호출 |
| 결과 차트 | `_render_trend_chart()` 재사용 |

캐스케이딩 동작:
- 부위가 바뀌면 그룹·세부 지표 selectbox를 index 0으로 초기화
- 그룹이 바뀌면 세부 지표 selectbox를 index 0으로 초기화

결과는 `st.session_state[f"expert_trend_chart_{session_id}"]`에 캐시하여
버튼 재클릭 전까지 마지막 조회 차트를 유지한다.

전문가 모드가 꺼지면 이 섹션 자체가 렌더링되지 않는다.

### API 파라미터 주의 (Phase 3-D 검증, 2026-05-12)

`GET /analysis/metrics/trends` 호출 시 `metric_name` 파라미터는
DB `skin_metric_values.metric_name` 컬럼값 기준이다 (`metric_key`가 아님).

| `_TREND_METRIC_OPTIONS` metric_name | 실제 DB metric_name | raw_part_name |
|-------------------------------------|---------------------|---------------|
| `moisture` | `moisture` | `forehead` / `left_cheek` / `right_cheek` / `chin` |
| `R0`…`R9`, `Q0`…`Q3` | 동일 | `forehead` 등 |
| `Ra`, `Rmax`, `Rt`, `Rz`, `Rp`, `Rv`, `Rq`, `R3z` | 동일 | `left_eye` / `right_eye` |
| `pore_count` | `pore_count` | `left_cheek` / `right_cheek` |

`metric_key`(예: `forehead_moisture`)는 표시용이며 trends 쿼리 파라미터로 사용하지 않는다.

### Phase 3-E E2E 검증 (2026-05-12)

실제 940×1410 얼굴 이미지(session_id=104) 기준 전체 흐름 검증 완료.

- YOLO bbox 3건 검출(forehead/lips/chin) + fallback 5건
- 실제 추론값: `forehead_moisture=50.64`, `forehead_elasticity_R2=0.438`
- report `overall_status=집중 관리 필요` (forehead pigmentation grade 3, wrinkle grade 4)
- trends API: 2세션 추이 포인트 (session 88 value=0.0 → session 104 value=0.438) 정상 반영
- latest report API → session_id=104 정상 반환

### 미구현 항목

- 추천 보정 seed 데이터 미삽입

## Phase 3-F UI Polish (2026-05-12)

API 변경 없음. 화면 표시 방식만 변경.

### 전문가 모드 토글 위치 변경

기존: 별도 행에 `st.toggle()`  
변경: "상세 분석" 헤더 오른쪽에 같은 줄로 인라인 배치 (`st.columns([3, 1])`)

### 추천 섹션 표현 변경

| 항목 | 변경 전 | 변경 후 |
|---|---|---|
| 추천 성분 subtitle | "도움이 되는 성분이에요" | "분석 기준 기반 추천 성분" |
| 섹션 서브타이틀 | (없음) | "피부 분석 결과와 등록된 추천 기준을 바탕으로 제안된 결과입니다." |
| 섹션 하단 노트 | (없음) | "알러지·민감 피부 주의 성분은 자동으로 제외됩니다." 안내 노트 |

### 전문가 모드 metric 그룹 표시

전문가 모드에서 80+ metric을 `metric_group`별로 묶어 그룹 레이블과 함께 표시한다.

그룹 표시 순서: `moisture` → `pore` → `pigmentation` → `acne` → `elasticity` → `wrinkle`

### 추이 그래프 카드 래퍼

추이 그래프 목록 전체를 `.ds-trend-charts-container` 카드 div로 감쌌다.

데이터 없을 때: 아이콘(📊) + 텍스트 empty state (`.ds-trend-empty-state`).  
단일 측정값: 큰 숫자 + 날짜 + 안내 텍스트 표시 (`.ds-trend-single-value`).  
API 실패: `.ds-trend-no-data` 텍스트 (기존 `st.caption` 대체).

### 전문가 추이 선택 UI 3-column

부위 / 지표 그룹 / 세부 지표 selectbox를 `st.columns(3, gap="small")` 한 줄 배치로 변경.

## Phase 3-G 리포트 UI 개선 (2026-05-13)

API 변경 없음. 화면 표시 및 로직 변경.

### 부위 카드 디자인

- 카드 요약 텍스트(부위별 "주름 관리가 필요합니다" 등) **제거**
- "상세 보기" 버튼 위치를 카드 하단으로 이동, 연한 하늘색(`#A8D8F0`) 배경, 상단 border-radius 제거
- 카드 wrapper: `border-radius: 20px`, `overflow: hidden`으로 버튼과 카드 일체형 처리

### 부위 상세 분석 패널 (`_render_selected_part_detail`)

선택된 부위 카드 클릭 시 하단에 상세 패널 표시.

구성:
- 헤더: 부위 아이콘 + 이름 + severity 배지 + 한줄 요약
- 주요 이슈 카드: 각 issue type별 컬러 좌측 보더, 등급/severity 표시
- 주요 측정 지표: bar chart 형태 (0~1 스케일 기준)
- 탭: 지표 요약 / 전문가 분석 / 측정 추이

### 맞춤 추천 결과 — concern 그룹 카드 (`_build_concern_groups`)

concern별 카드를 `issue_type` 기준으로 그룹화하여 표시한다.

#### concern → metric_group 매핑 (`_CONCERN_TO_METRIC_GROUPS`)

각 concern issue_type이 어떤 metric_group과 연결되는지를 명시적으로 정의한다.

| issue_type | 연결 metric_group | 이유 |
|---|---|---|
| wrinkle | wrinkle | 직접 대응 |
| pore | pore | 직접 대응 |
| moisture | moisture | 직접 대응 |
| dryness | moisture | 건조 이슈에 수분 측정값 표시 |
| sagging | elasticity | 처짐 이슈에 탄력 측정값 표시 |
| elasticity | elasticity | 직접 대응 |
| pigmentation | pigmentation | 직접 대응 |
| acne | acne | 직접 대응 |

#### 전체 얼굴 메트릭 포함

`pigmentation_count`, `acne_count`는 `full_face` 파트에만 저장되므로
모든 파트 메트릭 풀에 `전체 얼굴` 메트릭을 포함하여 색소침착/여드름 concern에서 조회 가능하게 한다.
해당 메트릭의 레이블은 "전체 얼굴 {metric_label}" 형태로 표시한다.

#### 카드 dim 처리 변경

기존: 측정값 없으면 항상 `ds-cg-card-dim` (흐리게)  
변경: **성분 추천이 있으면 dim 처리하지 않음** (측정값 없어도 정상 카드)  
→ 입술 건조 등 측정값이 없는 정상 케이스에서 카드가 죽어 보이는 문제 해결

#### 측정값 섹션 표시 조건

`has_metrics=True`일 때만 "측정값" 섹션을 렌더링한다.
측정값이 없을 경우 "측정값 없음" 텍스트 없이 성분 추천 섹션만 표시한다.

## 문서 갱신 규칙

리포트 API 응답 구조나 화면 표시 기준이 변경되면 이 문서를 즉시 수정한다.
