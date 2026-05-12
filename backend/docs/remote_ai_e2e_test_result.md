# Remote AI E2E 테스트 완료 보고

> 작성일: 2026-05-11  
> 작성자: bellra-jin  
> 대상 브랜치: exp/jm-prep

---

## 개요

DINOv3 기반 실제 AI 서버와 프론트엔드를 연결하는 전체 통신 흐름 테스트를 완료했습니다.
이번 테스트 목적은 **모델 정확도 검증이 아니라 프론트 → 백엔드 → AI 서버 → DB → 리포트까지의 통신 흐름 검증**입니다.

---

## 테스트 환경

| 항목 | 값 |
|---|---|
| AI 서버 | `http://localhost:9000` |
| 백엔드 | `http://localhost:8000` |
| 프론트 | `http://localhost:8501` |
| AI 추론 모드 | `remote` (테스트 전 `mock` → `remote` 변경) |
| GPU | CUDA 사용 확인 |
| 모델 로드 | `models_loaded: true` |

---

## 현재 AI 모델 구조

| 부위 | 상태 | 비고 |
|---|---|---|
| **눈가 (left_eye)** | ✅ **실제 DINOv3 추론** | `ckpt_kfold_vits_part3` 5-fold 앙상블 |
| 볼 / 이마 / 미간 / 입술 / 턱 | mock 고정값 | 해당 checkpoint 미준비, 추후 연결 예정 |

현재는 눈가 Part 3(`l_perocular_wrinkle`)만 실제 모델로 추론하며, 나머지 부위는 임시 고정값을 사용합니다.

---

## 흐름 검증 결과

```
프론트 이미지 업로드
→ 백엔드 POST /analysis/sessions/{id}/images
→ inference_service.run_inference() [remote 모드]
→ AI 서버 POST /inference/skin (bbox 없이 전체 이미지 전달)
→ DINOv3 실제 추론 (눈가)
→ 백엔드 skin_part_results DB 저장
→ GET /analysis/sessions/{id}/report
→ 프론트 리포트 화면 눈가 결과 표시
```

**전 구간 정상 동작 확인** ✅

---

## 눈가 실제 추론 결과 (session_id=47)

| 항목 | mock 고정값 | 실제 AI 추론값 |
|---|---|---|
| `model_name` | `mock_skin_model` | **`skin_dinov3_ensemble_model`** |
| `grade_value` | 3 | **0** |
| `severity` | `severe` | **`normal`** |
| `confidence_score` | 0.88 | **0.8224** |
| `predicted_value` | 0.87 | 0.87 (※ 현재 고정값, 하단 참고) |
| `measured_value` | — | **NULL** (이미지 업로드 경로 정상) |

`grade_value`, `severity`, `confidence_score` 세 값이 모두 mock과 달라 **실제 모델 추론이 동작하고 있음을 확인**했습니다.

---

## bbox 처리 방향

| 레이어 | 역할 |
|---|---|
| 프론트 | 전체 얼굴 이미지만 전달. bbox 생성 없음 |
| 백엔드 | 이미지를 AI 서버로 그대로 전달. bbox 생성 없음 |
| AI 서버 | bbox 처리 담당. 현재 자동 추출 준비 중 → bbox 없으면 전체 이미지 기준 추론 |

이번 테스트는 bbox 없이 진행했으며 통신 흐름은 정상입니다.
bbox 자동 추출 모델 연결 후 눈가 crop 정확도를 별도로 검증할 예정입니다.

---

## `predicted_value` 현재 상태

현재 `inference_engine.py`의 `predict()`는 `grade_value`, `severity`, `confidence_score`만 반환하고 `predicted_value`는 반환하지 않습니다.
때문에 눈가의 `predicted_value`는 AI 서버 응답 템플릿의 고정값(`0.87`)이 그대로 유지됩니다.
이 부분은 이후 `predict()`에서 확률 기반 회귀값을 `predicted_value`로 추가하는 작업이 필요합니다.

---

## 성공 기준 체크리스트

- [x] AI 서버 health 정상 (`status: ok`, `models_loaded: true`, `device: cuda`)
- [x] 백엔드 `AI_INFERENCE_MODE=remote` 적용
- [x] 프론트 이미지 업로드 성공
- [x] 백엔드가 AI 서버 `/inference/skin` 호출
- [x] DB `skin_part_results`에 `left_eye` 저장, `model_name=skin_dinov3_ensemble_model`
- [x] report API에 눈가 결과 포함
- [x] 프론트 리포트 화면에 눈가 카드 및 예측값 표시
- [x] `measured_value = NULL` (이미지 업로드 경로 정상)

**결론: 통신 흐름 E2E 테스트 성공**

---

## 다음 단계 TODO

1. **`predicted_value` 실제화** — `inference_engine.predict()`에서 확률 기반 회귀값 반환 추가
2. **bbox 자동 추출 연결** — AI 서버 내부에서 눈가 bbox 자동 추출 모델/로직 구현
3. **bbox 정확도 재검증** — 자동 추출 완료 후 눈가 crop 기반 추론 정확도 별도 테스트
4. **다부위 확장** — 볼/이마/미간/입술/턱 checkpoint 및 bbox 준비 후 순차 연결
5. **`.env` 확인** — 개발 중 mock/remote 모드 전환 시 백엔드 재시작 필수 (`lru_cache` 적용됨)
