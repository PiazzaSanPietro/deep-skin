
# 7. `frontend/docs/frontend_report_design.md`

# Frontend Report Design Guide

## 목적

분석 리포트 화면에서 백엔드 응답을 사용자 친화적으로 표시하는 기준을 정의한다.

## 사용 API

```http
GET /analysis/sessions/{session_id}/report
```

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
  "part_reports": []
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
metric_display_name
severity
grade_value
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

## 문서 갱신 규칙

리포트 API 응답 구조나 화면 표시 기준이 변경되면 이 문서를 즉시 수정한다.
