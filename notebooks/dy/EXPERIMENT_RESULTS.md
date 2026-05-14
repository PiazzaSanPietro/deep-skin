# DY 이마/미간 ResNet-50 실험 요약

## 데이터 사용 범위

- 샘플만 사용한 것이 아니라, 원천 데이터에서 이마와 미간 이미지를 전체 크롭해 학습했습니다.
- 학습 데이터: 8,580장
  - 이마: 4,290장
  - 미간: 4,290장
- 검증 데이터: 1,070장
  - 이마: 535장
  - 미간: 535장
- 샘플 이미지는 발표용 crop 확인, 추론 리포트, Grad-CAM 검증에만 사용했습니다.

## 적용한 개선 우선순위

1. 등급 통합
   - 기존 세부 등급을 낮음/중간/높음 3등급으로 통합했습니다.
   - 매핑: 원본 0~1 -> 0, 원본 2~3 -> 1, 원본 4 이상 -> 2
2. 클래스 불균형 보정
   - class weight와 WeightedRandomSampler를 함께 적용했습니다.
   - 소수 등급이 학습에서 더 자주 보이도록 했습니다.
3. 소수 클래스 augmentation
   - sampler로 반복 노출되는 소수 클래스 이미지에 매번 random crop, color jitter, affine, blur, random erasing이 적용됩니다.
4. crop 품질 확인
   - crop width, crop height, aspect ratio 분포를 리포트와 그래프로 저장했습니다.
5. 과적합 완화
   - early stopping, weight decay, dropout, 낮은 learning rate, backbone 일부 freeze를 적용했습니다.
6. ordinal classification
   - 등급이 순서형 라벨이라는 점을 반영하기 위해 `--ordinal-loss-weight` 옵션을 추가했습니다.
   - 최종 실험에서는 `--ordinal-loss-weight 0.2`를 사용했습니다.

## 주요 실험 결과

| 실험 | 라벨 구조 | Best epoch | Val Macro F1 | Val Accuracy |
| --- | --- | ---: | ---: | ---: |
| `dy_resnet50_cuda_full` | 원본 6/7등급 | 10 | 0.343 | 0.344 |
| `dy_resnet50_regularized_v2` | 원본 6/7등급 | 11 | 0.404 | 0.511 |
| `dy_resnet50_3grade_v1` | 3등급 통합 | 7 | 0.671 | 0.730 |
| `dy_resnet50_3grade_ordinal_v1` | 3등급 통합 + ordinal loss | 7 | 0.685 | 0.741 |

## 최종 추천 모델

- 최종 추천 checkpoint:
  `checkpoints/trained/dy_forehead_glabella/dy_resnet50_3grade_ordinal_v1/best.pth`
- 최종 검증 성능:
  - 평균 Macro F1: 0.685
  - 평균 Accuracy: 0.741
- 태스크별 성능:
  - 이마 색소침착: Macro F1 0.608, Accuracy 0.735
  - 이마 주름: Macro F1 0.690, Accuracy 0.675
  - 미간 주름: Macro F1 0.758, Accuracy 0.815

## 발표용 산출물

- `results/dy_forehead_glabella/presentation_assets/10_model_comparison_3grade.png`
- `results/dy_forehead_glabella/presentation_assets/11_3grade_ordinal_training_curves.png`
- `results/dy_forehead_glabella/presentation_assets/12_3grade_ordinal_task_metrics.png`
- `results/dy_forehead_glabella/presentation_assets/09_crop_quality_check.png`
- `results/dy_forehead_glabella/presentation_assets/crop_quality_report.csv`

## 발표 때 말할 핵심 문장

이전에는 원본 세부 등급을 그대로 맞추려다 데이터 불균형과 라벨 모호성 때문에 성능이 낮았습니다. 그래서 서비스 관점에서 의미가 더 분명한 낮음/중간/높음 3등급으로 통합했고, class weight와 WeightedRandomSampler로 불균형을 보정했습니다. 여기에 augmentation, early stopping, weight decay, dropout, backbone 일부 freeze를 적용해 과적합을 줄였고, 마지막으로 등급의 순서를 반영하는 ordinal loss를 추가해 최종 Macro F1을 0.685까지 올렸습니다.
