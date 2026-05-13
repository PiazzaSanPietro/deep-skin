# dy: Forehead/Glabella ResNet-50 Multitask Pipeline

이 폴더는 이마와 미간 파트 전용 작업물입니다. 흐름은 `crop.py`로 필요한 부위 이미지를 만들고, `train.py`로 ResNet-50 공유 백본 기반 멀티태스크 모델을 학습한 뒤, `predict.py`로 등급·회귀 수치·추천 근거·Grad-CAM을 생성하는 구조입니다.

## 0. Python Environment

현재 레포에는 `.venv`가 생성되어 있고, Python 3.12.13 / PyTorch CUDA 환경이 설치되어 있습니다.

```powershell
cd C:\Users\WOO\Documents\GitHub\deep-skin
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import torch, torchvision, pandas; print(torch.__version__, torchvision.__version__, pandas.__version__)"
.\.venv\Scripts\python.exe -c "import torch; print(torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

새 터미널에서 `uv`가 바로 잡히지 않으면 터미널을 다시 열거나 아래처럼 현재 세션 PATH만 갱신합니다.

```powershell
$env:PATH = "C:\Users\WOO\.local\bin;$env:PATH"
uv --version
```

## 1. Crop + Metadata

```powershell
cd C:\Users\WOO\Documents\GitHub\deep-skin
.\.venv\Scripts\python.exe notebooks\dy\crop.py --data-root "C:\Users\WOO\Downloads\028.한국인 피부상태 측정 데이터" --save-samples 20
```

생성 결과:

- `data/cropped/dy_forehead_glabella/{train,val}/{forehead,glabella}`
- `data/processed/dy_forehead_glabella_train_metadata.csv`
- `data/processed/dy_forehead_glabella_val_metadata.csv`
- `results/dy_forehead_glabella/crop_summary.json`
- `results/dy_forehead_glabella/crop_samples`

현재 전체 크롭 생성 결과는 train 8,580장, val 1,070장입니다.

기본 각도는 정면 계열 `F`, `Ft`, `Fb`입니다. 측면 각도까지 쓰려면 `--include-side-angles`를 추가합니다.

## 2. Multitask Training

```powershell
cd C:\Users\WOO\Documents\GitHub\deep-skin
.\.venv\Scripts\python.exe notebooks\dy\train.py --epochs 40 --batch-size 16 --weights local_or_none
```

학습 태스크:

- `forehead_pigmentation`: 이마 색소침착 0~5 등급 분류
- `forehead_wrinkle`: 이마 주름 0~6 등급 분류
- `glabella_wrinkle`: 미간 주름 0~6 등급 분류
- 회귀: 이마 수분 및 주요 탄력 수치

체크포인트와 학습 로그는 `checkpoints/trained/dy_forehead_glabella/{run}` 아래에 저장됩니다.

ImageNet ResNet-50 가중치 파일이 `checkpoints/pretrained/resnet50-0676ba61.pth`에 있으면 자동 사용합니다. 없으면 `local_or_none` 설정에서 랜덤 초기화로 진행합니다. 캐시나 네트워크 사용이 가능하면 `--weights torchvision`도 쓸 수 있습니다.

## 3. Inference + XAI + Recommendation

```powershell
.\.venv\Scripts\python.exe notebooks\dy\predict.py `
  --checkpoint checkpoints\trained\dy_forehead_glabella\{run}\best.pth `
  --image data\cropped\dy_forehead_glabella\val\forehead\sample.jpg `
  --part forehead `
  --output-json results\dy_forehead_glabella\sample_report.json `
  --gradcam-dir results\dy_forehead_glabella\gradcam
```

응답에는 백엔드 계약에 맞춘 `parts` 배열, 회귀 수치, 수치 기반 설명, 추천 카테고리/성분, Grad-CAM 이미지 경로가 포함됩니다.

## 4. Design Notes

- 단일 등급 모델 대신 하나의 ResNet-50 백본에서 분류 head 3개와 회귀 head 1개를 동시에 학습합니다.
- 크롭 CSV에는 raw JSON, annotation, equipment 값을 같이 보존해 추후 분석과 오류 추적이 쉽도록 했습니다.
- 회귀 수치는 설명 가능성을 위한 보조 근거입니다. 예를 들어 이마 수분 예측값이 낮으면 보습/장벽 성분 추천 근거로 사용합니다.
- Grad-CAM은 분류 등급별로 모델이 주목한 영역을 저장해 "왜 이 등급이 나왔는가"를 시각적으로 확인하는 용도입니다.
