# Remote AI E2E 테스트 완료 보고

> 최초 작성: 2026-05-11 (remote 단일값 서버)
> 업데이트: 2026-05-13 (multivalue 서버 전환 및 전체 필드 검증 완료)
> 대상 브랜치: exp/jm-prep

---

## 개요

DINOv3 + MultiTaskSkinModel 기반 multivalue AI 서버와 프론트엔드를 연결하는
전체 통신 흐름 및 DB 저장 검증을 완료했습니다.

---

## 최종 테스트 환경

| 항목 | 값 |
|---|---|
| AI 서버 (multivalue) | `http://localhost:9001` |
| 백엔드 | `http://localhost:8000` |
| 프론트 | `http://localhost:8501` |
| AI 추론 모드 | `multivalue` |
| 모델 | DINOv3 ViT-S/16 + MultiTaskSkinModel |
| Device | CPU (CUDA 미지원 환경) |

---

## 모델 구조

| 파일 | 역할 |
|---|---|
| `model/face_multivalue_inf_best_v2.pt` | MultiTaskSkinModel head (13MB) |
| `model/yolo_facecrop_best.pt` | YOLO 얼굴 부위 검출 (18MB) |
| `scripts/dinov3_vits16plus_pretrain_lvd1689m-4057cbaa.pth` | DINOv3 ViT-S backbone (110MB) |

모든 facepart(이마/미간/눈가/볼/입술/턱) 에 대해 실제 모델 추론 동작.

---

## 흐름 검증 결과

```
프론트 이미지 업로드
→ 백엔드 POST /analysis/sessions/{id}/images
→ image_service._run_multivalue_mode()
→ inference_service.run_multivalue_inference() [multivalue 모드]
→ multivalue_ai_server :9001 POST /inference/skin
    → YOLO 얼굴 부위 검출 (미검출 부위는 full_image_fallback)
    → DINOv3 feature 추출 → MultiTaskSkinModel 추론
→ multivalue_parser.parse_multivalue_response()
    → skin_part_results 저장 (등급값 11개)
    → skin_metric_values 저장 (연속 측정값 79개, 더미 0개)
    → skin_part_detections 저장 (YOLO 검출 기록 8개)
    → ai_raw_responses 저장 (원본 JSON)
→ recommendation_service.generate_and_save()
→ GET /analysis/sessions/{id}/report → 프론트 리포트 표시
```

**전 구간 정상 동작 확인** ✅

---

## DB 저장 검증 (session_id=161 기준)

### skin_part_results — 등급/이슈값 (11개)

| 부위 | 이슈 | 등급 | severity |
|---|---|---|---|
| chin | sagging | 3 | moderate |
| forehead | pigmentation | 3 | severe |
| forehead | wrinkle | 2 | mild |
| glabella | wrinkle | 2 | severe |
| left_cheek | pore | 1 | mild |
| left_cheek | pigmentation | 1 | mild |
| left_eye | wrinkle | 1 | mild |
| lips | dryness | 2 | mild |
| right_cheek | pore | 1 | mild |
| right_cheek | pigmentation | 1 | mild |
| right_eye | wrinkle | 1 | mild |

### skin_metric_values — 연속 측정값 (79개, 더미 0개)

| 부위 | metric_group | 개수 |
|---|---|---|
| chin | elasticity | 14 |
| forehead | elasticity | 14 |
| forehead | moisture | 1 |
| full_face | pigmentation | 1 (pigmentation_count=165) |
| full_face | acne | 1 (acne_count=0, 실제 모델 예측) |
| left_cheek | elasticity | 14 |
| left_cheek | moisture | 1 |
| left_cheek | pore | 1 (pore_count=551) |
| left_eye | wrinkle | 8 (Ra/Rmax/Rt 등) |
| right_cheek | elasticity | 14 |
| right_cheek | moisture | 1 |
| right_cheek | pore | 1 (pore_count=650) |
| right_eye | wrinkle | 8 |

### skin_part_detections — YOLO 검출 기록 (8개)

| 부위 | bbox_source | 비고 |
|---|---|---|
| chin | yolo | conf=0.930 |
| forehead | yolo | conf=0.778 |
| glabella | yolo | conf=0.815 |
| left_cheek | yolo | conf=0.871 |
| lips | yolo | conf=0.860 |
| right_cheek | yolo | conf=0.829 |
| left_eye | full_image_fallback | YOLO 미검출, 전체 이미지 사용 |
| right_eye | full_image_fallback | YOLO 미검출, 전체 이미지 사용 |

---

## YOLO 검출률 특성

테스트 이미지들에서 확인된 YOLO 검출 패턴:

- **안정적 검출**: chin, lips (대부분 이미지에서 검출)
- **조건부 검출**: forehead, glabella, left_cheek, right_cheek (이미지 품질에 따라)
- **거의 미검출**: left_eye, right_eye (현재 테스트 이미지에서 신뢰도 0)

미검출 부위는 `full_image_fallback` 처리되어 전체 이미지 crop으로 추론을 수행합니다.
등급값 0(예: wrinkle=0)은 더미가 아닌 **실제 "이상 없음" 모델 예측값**입니다.

---

## chin_moisture 제거

`chin_moisture`는 LABEL_REGISTRY에 학습 라벨이 없어 항상 0이었습니다.
2026-05-13에 AI 서버 응답 및 DB 저장 대상에서 완전히 제거했습니다.
(`scripts/multivalue_ai_server.py` `_build_part8()` 함수에서 제거)

---

## 성공 기준 체크리스트

- [x] AI 서버 health 정상 (`models_loaded: true`, `face_detector_loaded: true`)
- [x] `AI_INFERENCE_MODE=multivalue` 적용
- [x] 프론트 이미지 업로드 성공
- [x] 백엔드가 AI 서버 `:9001/inference/skin` 호출
- [x] 9개 facepart 모두 추론 (미검출 부위는 fallback)
- [x] skin_part_results 11개 정상 저장 (더미 없음)
- [x] skin_metric_values 79개 정상 저장 (더미 없음)
- [x] skin_part_detections 8개 정상 저장
- [x] 리포트 API에서 전 부위 결과 포함
- [x] 프론트 리포트 화면 정상 표시

**결론: MultiValue AI E2E 테스트 성공**

---

## 다음 단계 TODO

1. **YOLO 검출률 개선** — 눈가(left_eye/right_eye) 검출이 안 되는 원인 분석 및 모델 개선
2. **chin_moisture 모델 학습** — 필요 시 LABEL_REGISTRY에 추가 후 재학습
3. **이미지 품질 가이드** — 정면 얼굴, 밝은 조명 조건에서의 검출률 최적화 가이드 작성
