# DY 성능 최적화 메모

## 현재 문제

기존 실험은 원본 6/7등급을 그대로 예측할 때 class imbalance와 등급 경계 모호성 때문에 성능이 낮고 과적합이 나타날 수 있다.
최종 학습은 낮음/중간/높음 3등급으로 통합하고, 불균형 보정과 과적합 완화를 함께 적용하는 방향을 권장한다.

## 코드 보강 내용

- ResNet-50 backbone과 task head에 서로 다른 learning rate 적용
  - backbone: `learning_rate * backbone_lr_mult`
  - classification/regression head: `learning_rate`
- `--focal-gamma` 옵션 추가
  - 어려운/소수 class 샘플에 더 집중
- `--grad-clip-norm` 옵션 추가
  - fine-tuning 중 gradient 폭주 완화
- `--amp` 옵션 추가
  - CUDA GPU에서 mixed precision 학습 가능
- `report_assets.py` 보강
  - 최종 run 하나만 있어도 발표용 그래프 생성 가능

## 권장 최종 학습 명령

먼저 전체 crop/metadata를 재생성한다.

```powershell
.\.venv\Scripts\python.exe .\notebooks\dy\crop.py --data-root "C:\Users\Admin\Downloads\028.한국인 피부상태 측정 데이터\3.개방데이터\1.데이터" --save-samples 20
```

그 다음 최적화 실험을 실행한다.

```powershell
.\.venv\Scripts\python.exe .\notebooks\dy\train.py `
  --epochs 40 `
  --batch-size 16 `
  --weights torchvision `
  --grade-scheme three `
  --weighted-sampler `
  --sampler-power 0.5 `
  --class-weight-power 0.5 `
  --label-smoothing 0.05 `
  --focal-gamma 1.0 `
  --ordinal-loss-weight 0.2 `
  --reg-loss-weight 0.15 `
  --freeze-until layer2 `
  --backbone-lr-mult 0.05 `
  --grad-clip-norm 1.0 `
  --run-name dy_resnet50_3grade_ordinal_optimized_v2
```

CUDA GPU가 있으면 `--amp`를 추가한다.

```powershell
  --amp `
```

## 결과 확인

학습이 끝나면 다음 파일을 확인한다.

```text
checkpoints/trained/dy_forehead_glabella/dy_resnet50_3grade_ordinal_optimized_v2/history.csv
checkpoints/trained/dy_forehead_glabella/dy_resnet50_3grade_ordinal_optimized_v2/history.png
checkpoints/trained/dy_forehead_glabella/dy_resnet50_3grade_ordinal_optimized_v2/best.pth
```

발표용 그래프는 다음 명령으로 생성한다.

```powershell
.\.venv\Scripts\python.exe .\notebooks\dy\report_assets.py
```

