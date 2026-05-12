# Remote AI E2E 테스트 계획서

> 작성일: 2026-05-11  
> 대상 브랜치: exp/jm-prep  
> 코드 수정 없음 — 이 문서는 계획서만이다.

---

## 1. 목적

프론트엔드에서 이미지를 업로드했을 때, 백엔드가 실제 AI 서버(DINOv3 기반)를 호출하고,  
**눈가(left_eye / l_perocular_wrinkle) 추론 결과**가 DB에 저장되어 리포트 화면까지 표시되는지 확인한다.

이번 테스트는 실제 AI 모델 검증 대상이 눈가 Part 3 하나임을 전제로 한다.

---

## 2. 현재 테스트 범위

### 이번 테스트에서 실제 AI 검증 대상

| 부위 | raw_part_name | metric | 검증 기준 |
|---|---|---|---|
| 눈가 | `left_eye` | wrinkle (l_perocular_wrinkle) | 실제 DINOv3 추론값 확인 |

### 이번 테스트에서 제외되는 부위

| 부위 | raw_part_name | metric | 현재 상태 | 제외 이유 |
|---|---|---|---|---|
| 볼 (좌) | `left_cheek` | pore | mock 고정값 | 해당 checkpoint 없음 |
| 볼 (우) | `right_cheek` | pore | mock 고정값 | 해당 checkpoint 없음 |
| 이마 | `forehead` | wrinkle | mock 고정값 | 해당 checkpoint 없음 |
| 미간 | `glabella` | wrinkle | mock 고정값 | 해당 checkpoint 없음 |
| 입술 | `lips` | dryness | mock 고정값 | 해당 checkpoint 없음 |
| 턱 | `chin` | sagging | mock 고정값 | 해당 checkpoint 없음 |

나머지 부위의 mock 값이 응답에 함께 내려오더라도, 이번 테스트의 성공/실패 기준으로 사용하지 않는다.

---

## 3. 현재 구조 이해

### 3-1. 전체 흐름

```
[프론트 analysis.py]
  └─ 사진 업로드 / 촬영
  └─ analysis_api.create_session() → POST /analysis/sessions
  └─ analysis_api.upload_image()   → POST /analysis/sessions/{session_id}/images

[백엔드 image_service.py]
  └─ 이미지 파일 저장 (uploads/skin_images/)
  └─ inference_service.run_inference(image_path, ...)
       ├─ AI_INFERENCE_MODE=mock  → _run_mock() (고정값 반환)
       └─ AI_INFERENCE_MODE=remote → _run_remote() → POST http://localhost:9000/inference/skin

[AI 서버 dummy_ai_server.py]
  └─ /inference/skin 수신 (전체 얼굴 이미지)
  └─ bbox는 AI 서버 내부에서 담당 (현재는 자동 추출 준비 중 → bbox 없으면 전체 이미지 기준 추론)
  └─ left_eye만 engine.predict(image, bbox)로 실제 추론
  └─ 나머지 부위는 _MOCK_PARTS_TEMPLATE에서 복사
  └─ InferenceResult 형식으로 반환

[백엔드 image_service.py 계속]
  └─ _validate_response() → InferenceResult Pydantic 파싱
  └─ SkinPartResult DB 저장

[백엔드 report_service.py]
  └─ GET /analysis/sessions/{session_id}/report
  └─ DB에서 SkinPartResult 조회 → 응답 구성

[프론트 report.py]
  └─ analysis_api.get_report() 호출
  └─ 눈가 grade_value / severity / predicted_value 표시
```

### 3-2. 주요 파일-역할 매핑

| 단계 | 파일 |
|---|---|
| 프론트 업로드 트리거 | `frontend/views/analysis.py` — `_run_analysis()` |
| 프론트 API 호출 | `frontend/services/analysis_api.py` |
| 백엔드 라우터 | `backend/app/routers/analysis.py` (추정) |
| 이미지 저장 + 추론 호출 | `backend/app/services/image_service.py` |
| 추론 모드 분기 | `backend/app/services/inference_service.py` — `run_inference()` |
| AI 서버 진입점 | `backend/scripts/dummy_ai_server.py` — `/inference/skin` |
| 모델 로드 + 실제 추론 | `backend/scripts/inference_engine.py` — `DinoInferenceEngine.predict()` |
| DB 저장 | `backend/app/services/image_service.py` (SkinPartResult 저장) |
| 리포트 조회 | `backend/app/services/report_service.py` (추정) |
| 프론트 리포트 렌더링 | `frontend/views/report.py` — `_issue_row_html()` |

### 3-3. bbox 처리 책임 명확화

| 레이어 | bbox 처리 역할 |
|---|---|
| 프론트엔드 | 전체 얼굴 이미지만 업로드. bbox를 생성하거나 전달하지 않는다. 사용자에게 bbox 입력을 요구하지 않는다. |
| 백엔드 | 프론트에서 받은 이미지를 그대로 AI 서버로 전달. bbox를 직접 계산하거나 생성하지 않는다. |
| AI 서버 | bbox 자동 추출을 최종적으로 담당한다. 현재는 자동 추출 모델/로직이 준비 중이므로, bbox가 없으면 전체 이미지 기준으로 임시 추론한다. |

`bbox_left_eye`는 **AI 서버 단독 디버깅용 선택 파라미터**다.  
프론트 E2E 테스트에서는 전달하지 않는다.  
최종 구조에서는 AI 서버가 입력 이미지에서 눈가 영역을 자동으로 추출하는 방향으로 진행한다.

---

### 3-4. 주의: lru_cache로 인한 백엔드 재시작 필요

`backend/app/core/config.py`:
```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`get_settings()`는 프로세스 시작 시 한 번만 실행된다.  
**.env 파일을 수정해도 백엔드를 재시작하지 않으면 변경이 반영되지 않는다.**

### 3-5. 주의: predicted_value는 AI 서버가 반환하지 않음

`inference_engine.py`의 `predict()` 반환값:
```python
return {
    "grade_value": pred_class,
    "severity": self.severity_map.get(pred_class, "unknown"),
    "confidence_score": round(float(probs_np[pred_class]), 4),
}
```

`predicted_value`는 반환하지 않는다.  
`dummy_ai_server.py`에서 `left_eye`에 `new_p.update(eye_result)`를 적용하므로,  
`grade_value` / `severity` / `confidence_score`는 실제 추론값으로 교체되지만,  
**`predicted_value`는 `_MOCK_PARTS_TEMPLATE`의 고정값 `0.87`이 그대로 유지된다.**

따라서 remote 모드에서 눈가 실제 AI 검증 기준은 다음과 같다:
- `grade_value`: 실제 모델 예측값 (0~6, num_classes=7)
- `severity`: grade_value 기반 실제 매핑값
- `confidence_score`: 실제 모델 확률값
- `predicted_value`: 0.87 고정 (이번 범위에서 실제 AI 검증 아님)

---

## 4. 테스트 전제 조건

테스트 시작 전 아래 조건이 모두 만족되어야 한다.

| 항목 | 요구 상태 |
|---|---|
| MySQL 서버 | 실행 중 (localhost:3306) |
| AI 서버 backbone | `backend/scripts/dinov3_vits16plus_pretrain_lvd1689m-4057cbaa.pth` 존재 |
| AI 서버 heads | `backend/ckpt_kfold_vits_part3/head_fold1~5.pth` 존재 (각 20KB) |
| dinov3 소스 | `backend/scripts/dinov3/` 디렉토리 존재 |
| GPU | CUDA 사용 가능 권장 (CPU도 동작하나 느림) |
| 백엔드 .env | `AI_INFERENCE_MODE=remote` 적용 필요 |

---

## 5. 설정 확인 항목

### 5-1. AI 서버 실행 여부 확인

```bash
curl http://localhost:9000/health
```

기대 응답:
```json
{
  "status": "ok",
  "service": "ai-inference",
  "device": "cuda",
  "models_loaded": true
}
```

확인 기준:
- `status`: `"ok"` 이어야 함
- `models_loaded`: `true` 이어야 함 (`false`면 backbone/heads 로드 실패)
- `device`: `"cuda"` 권장 (CPU면 추론 속도 매우 느림)

### 5-2. 백엔드 AI_INFERENCE_MODE 확인

`backend/.env` 현재 값:
```env
AI_INFERENCE_MODE=mock   ← 이것을 remote로 변경 후 백엔드 재시작 필요
AI_INFERENCE_URL=http://localhost:9000/inference/skin
AI_INFERENCE_TIMEOUT_SECONDS=30
```

변경 후:
```env
AI_INFERENCE_MODE=remote
```

**반드시 백엔드 uvicorn 프로세스를 재시작해야 lru_cache가 새 설정을 읽는다.**

### 5-3. 포트 충돌 확인

```bash
# Windows
netstat -ano | findstr :9000
netstat -ano | findstr :8000
```

- 9000: AI 서버
- 8000: 백엔드 서버

두 포트 모두 정상 점유 상태인지 확인한다.

### 5-4. 프론트 BACKEND_API_URL 확인

`frontend/.env`:
```env
BACKEND_API_URL=http://localhost:8000
```

---

## 6. 테스트 범위

### 6-1. AI 서버 단독 테스트

**목적**: AI 서버가 이미지를 직접 받아 눈가 실제 추론 결과를 반환하는지 확인

**확인 항목**:
- `/health` 응답 정상 여부
- `/inference/skin`에 이미지 전송 시 응답 구조
- `parts[]` 배열에 `left_eye` 항목 존재 여부
- `left_eye`의 `grade_value` (0~6 정수, mock 고정값 3과 다를 수 있음)
- `left_eye`의 `severity` (grade 기반 매핑, mock 고정값 `"severe"`와 다를 수 있음)
- `left_eye`의 `confidence_score` (실수값, mock 고정값 0.88과 다를 수 있음)
- `model_name`: `"skin_dinov3_ensemble_model"`
- `model_version`: `"0.2.0"`

**성공 기준**: `left_eye` 항목이 존재하고, `grade_value` / `severity` / `confidence_score`가 정상 반환됨

> **bbox 관련**: AI 서버 단독 테스트 시 `bbox_left_eye`를 수동으로 전달해 crop 정확도를 확인할 수 있다.  
> 단, 이 파라미터는 디버깅 전용이며, 프론트 E2E 흐름에서는 전달하지 않는다.

### 6-2. 백엔드 remote inference 테스트

**목적**: 백엔드가 AI 서버를 호출하고 눈가 결과를 DB에 저장하는지 확인

**확인 항목**:
- `AI_INFERENCE_MODE=remote` 적용 후 백엔드 재시작 완료 여부
- `POST /analysis/sessions/{session_id}/images` 성공 (200 응답)
- 백엔드 로그에서 AI 서버 호출 로그 확인
- DB `skin_part_results` 테이블에 눈가 결과 저장 여부
- `GET /analysis/sessions/{session_id}/report` 응답에 눈가 포함 여부
- 눈가 `predicted_value`가 응답에 포함되는지 (0.87 고정값으로라도)
- `measured_value`가 null인지 (이미지 업로드 경로)

### 6-3. 프론트 E2E 테스트

**목적**: 사용자가 프론트에서 이미지를 업로드했을 때 눈가 결과가 리포트 화면에 표시되는지 확인

**확인 항목**:
1. 로그인 성공
2. 프로필 완성 여부 확인 (→ 분석 화면 이동)
3. 이미지 업로드 또는 카메라 촬영
4. "분석 시작" 버튼 클릭
5. AI 분석 중 진행 화면 표시
6. 분석 완료 후 "리포트 확인하기" 버튼 표시
7. 리포트 화면에서 눈가 카드 표시
8. 눈가 `severity` 배지 표시
9. 눈가 "예측값: X.XX" 표시 (predicted_value 기반)
10. 눈가 외 부위(볼/이마/미간/입술/턱) 카드도 표시됨 (mock 고정값, 이번 검증 기준 아님)

---

## 7. 단계별 테스트 계획

### 단계 1: 업로드 파일

**관련 파일**: `frontend/views/analysis.py` — `_run_analysis()`  
**확인할 값**: `image_data["bytes"]`, `image_data["name"]`  
**성공 기준**: 이미지가 bytes로 메모리에 올라와 있음  
**실패 시 의심 원인**: `st.camera_input` 또는 `st.file_uploader` 미동작, 이미지 미선택 상태로 분석 시작

---

### 단계 2: 백엔드 UploadedImage 저장

**관련 파일**: `backend/app/services/image_service.py`  
**확인할 값**: `uploads/skin_images/{user_id}/{session_id}/` 경로에 파일 저장 여부  
**성공 기준**: 파일이 디스크에 존재함  
**실패 시 의심 원인**: 업로드 디렉토리 권한 문제, `UPLOAD_DIR` 설정 오류

---

### 단계 3: inference_service.run_inference() 호출

**관련 파일**: `backend/app/services/inference_service.py`  
**확인할 값**: `settings.AI_INFERENCE_MODE` 값이 `"remote"` 인지  
**성공 기준**: `_run_remote()`가 호출됨 (백엔드 로그에서 "AI inference 요청" 로그 확인)  
**실패 시 의심 원인**:
- `.env`를 수정했으나 백엔드 미재시작 → `lru_cache` 때문에 여전히 `mock` 모드
- `.env` 파일 경로가 `backend/` 기준이 아닌 다른 위치에서 uvicorn 실행

---

### 단계 4: AI 서버 /inference/skin 호출

**관련 파일**: `backend/app/services/inference_service.py` — `_run_remote()`  
**확인할 값**: `settings.AI_INFERENCE_URL` = `http://localhost:9000/inference/skin`  
**성공 기준**: AI 서버 로그에 수신 로그 출력 (`[ai-server] 수신 | filename=...`)  
**실패 시 의심 원인**:
- AI 서버 포트 9000 미실행 또는 포트 충돌
- `AI_INFERENCE_URL` 설정 오류 (포트 번호, 경로 오타)
- `AI_INFERENCE_TIMEOUT_SECONDS=30` 초과 (모델 로드가 느린 경우)

---

### 단계 5: AI 서버 응답 InferenceResult

**관련 파일**: `backend/scripts/dummy_ai_server.py`  
**확인할 값**:
```json
{
  "model_name": "skin_dinov3_ensemble_model",
  "model_version": "0.2.0",
  "parts": [
    {
      "raw_part_name": "left_eye",
      "display_part_name": "눈가",
      "metric_name": "wrinkle",
      "grade_value": <실제 추론값, 0~6>,
      "severity": <실제 추론값>,
      "confidence_score": <실제 추론값>,
      "predicted_value": 0.87   ← mock 고정값 유지됨 (현재 구조상 정상)
    },
    ...나머지 6개 부위는 mock 고정값...
  ]
}
```
**성공 기준**: `left_eye` 항목이 있고 `grade_value` / `severity` / `confidence_score`가 정상 반환됨  
**실패 시 의심 원인**:
- `engine.heads`가 비어 있음 (`models_loaded=false` 상태)
- `dinov3/` 소스 디렉토리 임포트 실패 → `DinoVisionTransformer` 로드 불가
- bbox 없이 전체 이미지로 추론 → 기능상 정상 동작. 이번 테스트는 통신 흐름 검증이므로 추론 정확도는 성공 기준에서 제외

---

### 단계 6: SkinPartResult DB 저장

**관련 파일**: `backend/app/services/image_service.py`  
**확인할 값**: `skin_part_results` 테이블 레코드  
**성공 기준**: 세션에 해당하는 눈가 레코드가 DB에 저장됨  
**실패 시 의심 원인**:
- AI 서버 응답이 Pydantic `InferenceResult` 스키마 파싱 실패 (`_validate_response()` 예외)
- DB 연결 오류
- `predicted_value` 필드가 AI 서버 응답에 없어서 null로 저장됨 (이는 정상 동작)

---

### 단계 7: report_service.get_report() 조회

**관련 파일**: `backend/app/services/report_service.py` (추정)  
**확인할 값**: `GET /analysis/sessions/{session_id}/report` 응답의 `part_reports[]`  
**성공 기준**: 눈가 항목이 `issues[]` 안에 존재하고 `grade_value` / `severity`가 정상 값  
**실패 시 의심 원인**:
- 세션 상태가 `completed`가 아닌 경우 리포트 조회 불가
- `session_id` 불일치 (프론트에서 잘못된 id 저장)

---

### 단계 8: 프론트 report 화면 표시

**관련 파일**: `frontend/views/report.py` — `_issue_row_html()`, `_get_detail_value_label()`  
**확인할 값**:
- 눈가 카드가 화면에 표시되는지
- severity 배지 표시
- "예측값: 0.87" 표시 (predicted_value=0.87 기반)
**성공 기준**: 리포트 화면에 눈가 카드가 렌더링되고 예측값 레이블이 표시됨  
**실패 시 의심 원인**:
- `st.session_state["current_session_id"]`가 없거나 잘못된 값
- report API가 401 반환 → 자동으로 로그인 화면으로 이동

---

## 8. 눈가 실제 AI 결과 확인 방법

### 8-1. AI 서버 직접 호출 테스트

프론트 E2E 흐름과 동일하게 bbox 없이 전체 이미지만 전달한다.

```bash
# 표준 호출 — 프론트 E2E와 동일한 방식 (bbox 없음)
curl -X POST http://localhost:9000/inference/skin \
  -F "file=@테스트이미지.jpg" \
  | python -m json.tool
```

bbox 없이 호출하면 AI 서버가 전체 이미지 기준으로 눈가 추론한다.  
이번 테스트의 성공 기준은 통신 흐름과 결과 저장이므로, crop 정확도는 판단하지 않는다.

**[디버깅 전용] bbox 수동 전달** — AI 서버 단독 정확도 비교 시에만 사용:
```bash
# bbox_left_eye는 AI 서버 단독 디버깅 파라미터 — 프론트 E2E에서는 사용하지 않음
curl -X POST http://localhost:9000/inference/skin \
  -F "file=@테스트이미지.jpg" \
  -F "bbox_left_eye=[191, 1432, 411, 1817]"
```

### 8-2. DB에서 눈가 결과 확인

```sql
SELECT
  spr.display_part_name,
  spr.raw_part_name,
  spr.metric_name,
  spr.grade_value,
  spr.predicted_value,
  spr.measured_value,
  spr.severity,
  spr.confidence_score,
  spr.model_name,
  spr.model_version
FROM skin_part_results spr
WHERE spr.session_id = ?      -- 테스트 세션 ID 입력
ORDER BY spr.id;
```

눈가 결과 확인 기준:
- `display_part_name = '눈가'` 레코드 존재 여부
- `grade_value`: 0~6 정수 (mock=3과 다를 수 있음 → 다르면 실제 추론 확인됨)
- `severity`: grade 기반 문자열 (mock=`severe`와 다를 수 있음)
- `confidence_score`: 실수 (mock=0.88과 다를 수 있음)
- `predicted_value`: 0.87 고정 (현재 구조상 정상)
- `measured_value`: NULL (이미지 업로드 경로에서 정상)
- `model_name`: `'skin_dinov3_ensemble_model'`

---

## 9. 이번 범위에서 제외되는 부위

| 부위 | metric | 현재 테스트 기준 | 확인 방법 | 기대 결과 |
|---|---|---|---|---|
| 눈가 | wrinkle / l_perocular_wrinkle | **실제 AI 검증 대상** | AI 서버 응답, DB, report API, 프론트 확인 | 실제 추론값 |
| 볼 | pore | 이번 범위 제외 | 나중에 볼 모델 연결 후 테스트 | 현재 판단하지 않음 |
| 이마 | wrinkle | 이번 범위 제외 | 나중에 이마 모델 연결 후 테스트 | 현재 판단하지 않음 |
| 미간 | wrinkle | 이번 범위 제외 | 나중에 미간 모델 연결 후 테스트 | 현재 판단하지 않음 |
| 입술 | dryness | 이번 범위 제외 | 나중에 입술 모델 연결 후 테스트 | 현재 판단하지 않음 |
| 턱 | sagging | 이번 범위 제외 | 나중에 턱 모델 연결 후 테스트 | 현재 판단하지 않음 |

mock 데이터가 응답에 함께 포함되더라도, 이번 테스트의 성공/실패 판단에 사용하지 않는다.

---

## 10. DB / API / 프론트 확인 포인트

### DB 확인 쿼리

```sql
-- 1. 세션 목록 확인 (가장 최근 테스트 세션 id 찾기)
SELECT id, session_name, status, created_at
FROM analysis_sessions
ORDER BY id DESC
LIMIT 5;

-- 2. 눈가 포함 전체 part 결과 확인
SELECT
  display_part_name,
  raw_part_name,
  metric_name,
  grade_value,
  predicted_value,
  measured_value,
  severity,
  confidence_score,
  model_name,
  model_version
FROM skin_part_results
WHERE session_id = ?
ORDER BY id;

-- 3. 눈가만 빠르게 확인
SELECT grade_value, severity, confidence_score, predicted_value, measured_value, model_name
FROM skin_part_results
WHERE session_id = ? AND raw_part_name = 'left_eye';
```

### report API 응답 확인

```bash
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8000/analysis/sessions/<session_id>/report \
  | python -m json.tool
```

눈가 항목 확인:
```json
"part_reports": [
  {
    "display_part_name": "눈가",
    "issues": [
      {
        "metric_name": "wrinkle",
        "raw_part_name": "left_eye",
        "grade_value": <실제값>,
        "predicted_value": 0.87,
        "measured_value": null,
        "severity": <실제값>,
        "confidence_score": <실제값>
      }
    ]
  }
]
```

### 프론트 확인 포인트

1. 리포트 화면 → 눈가 카드 존재 여부
2. 눈가 severity 배지 색상 (mock=`severe`=빨강 vs 실제 추론값)
3. 눈가 "예측값: 0.87" 텍스트 표시 여부 (subdued 색상, 11px)

---

## 11. 예상 실패 케이스와 대응

| 실패 케이스 | 원인 | 확인 방법 |
|---|---|---|
| AI 서버 포트 9000 충돌 | 이전 프로세스가 살아 있음 | `netstat -ano \| findstr :9000` |
| `models_loaded=false` | backbone/heads 로드 실패 | AI 서버 시작 로그 확인. dinov3/ 디렉토리 존재 여부 확인 |
| `AI_INFERENCE_MODE`가 여전히 mock | lru_cache로 인해 재시작 안 함 | 백엔드 재시작 필수. 로그에서 `_run_mock` 호출 여부 확인 |
| 백엔드가 9000 대신 다른 URL 호출 | `.env`의 `AI_INFERENCE_URL` 오류 | `cat backend/.env \| grep AI_INFERENCE_URL` |
| `/inference/skin` 422 오류 | 요청 form 필드 타입 불일치 | AI 서버 로그, `inference_service.py`의 `data=form_data` 확인 |
| 눈가 part가 응답에 없음 | `_MOCK_PARTS_TEMPLATE`에서 left_eye 항목 누락 | `dummy_ai_server.py` 직접 확인 |
| `predicted_value`가 DB에 null | AI 서버 응답에 없어서 Pydantic이 None으로 파싱 | 현재 구조상 정상 (0.87 고정값은 template에서 옴) |
| 눈가 grade_value가 mock(3)과 동일 | 실제 추론이 아닌 mock이 적용된 경우 | AI 서버 로그 확인, `models_loaded` 재확인 |
| DB에는 저장됐지만 report API에 없음 | report_service 조회 로직 문제, 세션 status 미완료 | `analysis_sessions.status` 확인 |
| report API에 있지만 프론트에 표시 안 됨 | `_issue_row_html()` 렌더링 오류 | 브라우저 개발자 도구, Streamlit 터미널 로그 확인 |
| bbox 없어서 눈 영역 정확도 낮음 | bbox 자동 추출이 아직 준비 중 | **이번 테스트 성공 기준 아님**. 통신 흐름만 검증. bbox 정확도는 자동 추출 연결 후 별도 검증 |
| AI 서버 추론 시간 30초 초과 | CPU 모드 또는 모델 로드 지연 | `AI_INFERENCE_TIMEOUT_SECONDS` 값 늘리기 |

---

## 12. 실행 명령어 계획

```bash
# 1. AI 서버 실행 (backend/ 디렉토리에서)
cd C:\PROJECT\Deep_skin\backend
python -m uvicorn scripts.dummy_ai_server:app --port 9000

# 2. AI 서버 health 확인
curl http://localhost:9000/health

# 3. backend/.env 수정
# AI_INFERENCE_MODE=mock → AI_INFERENCE_MODE=remote 로 변경

# 4. 백엔드 실행 (반드시 재시작 — lru_cache 때문)
cd C:\PROJECT\Deep_skin\backend
python -m uvicorn app.main:app --reload

# 5. 프론트 실행
cd C:\PROJECT\Deep_skin\frontend
streamlit run app.py

# 6. AI 서버 직접 테스트 (이미지 파일 있을 때)
curl -X POST http://localhost:9000/inference/skin -F "file=@test.jpg" | python -m json.tool

# 7. DB 확인 (MySQL)
mysql -u root -pzxasqw12 deep_skin -e "
  SELECT display_part_name, raw_part_name, grade_value, severity, confidence_score,
         predicted_value, measured_value, model_name
  FROM skin_part_results
  WHERE session_id = (SELECT MAX(id) FROM analysis_sessions)
  ORDER BY id;
"
```

---

## 13. 성공 기준

### 이번 테스트 통과 조건 (모두 만족해야 성공)

- [ ] AI 서버 `GET /health` → `status: ok`
- [ ] AI 서버 `models_loaded: true`
- [ ] AI 서버 `device: cuda` (또는 cpu — 동작은 함)
- [ ] 백엔드 `AI_INFERENCE_MODE=remote` 적용 확인 (재시작 후)
- [ ] 프론트에서 이미지 업로드 성공 (200 응답)
- [ ] 백엔드 로그에 "AI inference 요청" 로그 출력
- [ ] DB `skin_part_results`에 `raw_part_name='left_eye'` 레코드 존재
- [ ] `model_name='skin_dinov3_ensemble_model'` (mock=`'mock_skin_model'`과 다름)
- [ ] `report API`에 눈가 항목 포함
- [ ] 프론트 리포트 화면에 눈가 카드 표시
- [ ] 프론트 리포트 화면에 눈가 "예측값: 0.87" 표시

### 실제 AI 추론 확인 추가 기준 (mock과의 차이)

- [ ] `model_name`이 `'mock_skin_model'`이 아닌 `'skin_dinov3_ensemble_model'`
- [ ] 눈가 `confidence_score`가 0.88과 다른 값 (실제 추론 확률)
- [ ] 눈가 `grade_value`가 입력 이미지에 따라 0~6 범위로 변동 가능

### 이번 테스트 성공 기준에서 제외

- 볼 / 이마 / 미간 / 입술 / 턱 실제 AI 추론 여부
- 전체 얼굴 bbox 기반 다부위 분석
- `predicted_value`가 실제 회귀값인지 여부 (현재 0.87 고정 — 추후 개선 대상)
- bbox 자동 추출 정확도
- 눈가 crop 정확도 (bbox 없이 전체 이미지 기준 추론 — 정확도 낮을 수 있으나 이번 범위 아님)
- 전체 이미지 대비 crop 추론 성능 비교
- 다른 부위 bbox 생성 및 추론

---

## 14. TODO

### 눈가 추론 개선
- [ ] `inference_engine.py`의 `predict()`에서 `predicted_value` 반환 추가 (현재 반환 안 함)
  - 현재: `confidence_score`만 반환
  - 개선안: `probs_np[pred_class]` 또는 기대값 기반 회귀값을 `predicted_value`로 추가

### bbox 자동 추출 (AI 서버 담당)
- [ ] AI 서버 내부 bbox 자동 추출 모델/로직 연결
  - 현재: bbox 없으면 전체 이미지 기준 추론 (임시)
  - 목표: 전체 얼굴 이미지 입력 → AI 서버 내부 눈가 bbox 자동 추출 → 눈가 crop 추론 구조로 개선
- [ ] bbox 자동 추출 완료 후 눈가 모델 정확도 재검증
- [ ] 프론트/백엔드는 bbox를 생성하거나 전달하지 않는 구조 유지 확인

### 다부위 확장
- [ ] 볼/이마/미간/입술/턱 각 부위 checkpoint 준비 후 실제 추론 연결
- [ ] 이후 각 부위별 bbox 자동 추출 및 모델 연결 확장
- [ ] 다부위 연결 후 각 부위별 E2E 테스트 계획 별도 수립

### 운영 설정
- [ ] 테스트 완료 후 `.env`의 `AI_INFERENCE_MODE`를 `mock`으로 복원할지 `remote`로 유지할지 팀 결정 필요
