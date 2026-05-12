# 볼 부위 학습 전 테스트 및 검증 가이드

## 1. 문서 목적

본 문서는 ResNet-50 기반 볼 부위 모공/색소침착 등급 분류 모델을 본격적으로 학습하기 전에, 데이터 전처리와 학습 파이프라인이 정상적으로 동작하는지 확인하기 위한 테스트 및 검증 기준을 정리한다.

1차 목표는 전체 데이터를 바로 학습하는 것이 아니라, 소량 샘플을 이용해 다음 과정을 먼저 확인하는 것이다.

```text
raw JSON / image
→ bbox crop
→ metadata CSV 생성
→ Dataset 로딩
→ DataLoader 확인
→ ResNet-50 forward 테스트
→ 1 epoch 미니 학습 테스트
→ validation 지표 확인
```

---

## 2. 테스트가 필요한 이유

AI-Hub 피부 이미지 데이터는 이미지, JSON 라벨, bbox, annotation, metadata가 함께 사용된다.

따라서 바로 전체 학습을 시작하면 다음과 같은 문제가 늦게 발견될 수 있다.

```text
- 이미지 경로 매칭 실패
- bbox 좌표 해석 오류
- crop 이미지가 볼 부위가 아닌 영역으로 잘림
- 라벨 컬럼 누락
- pore_label / pigmentation_label 값 오류
- train/val CSV 구조 불일치
- Dataset에서 이미지 로딩 실패
- 모델 출력 차원 오류
- CrossEntropyLoss 입력 형태 오류
- GPU 메모리 부족
```

따라서 본격 학습 전에 반드시 작은 데이터로 전체 흐름을 검증한다.

---

## 3. 테스트 범위

테스트는 크게 3단계로 나눈다.

| 단계 | 목적 | 산출물 |
|---|---|---|
| 1단계 | Crop 테스트 | 샘플 crop 이미지, crop 로그 |
| 2단계 | Dataset/DataLoader 테스트 | batch 이미지/라벨 shape 확인 |
| 3단계 | 학습 파이프라인 테스트 | 1 epoch 학습 결과, validation 결과 |

---

## 4. 1단계: Crop 테스트

### 4.1. 목적

원본 JSON의 bbox를 기준으로 볼 영역이 정상적으로 crop되는지 확인한다.

테스트에서는 전체 데이터를 사용하지 않고, train/val 각각 일부 샘플만 사용한다.

권장 샘플 수:

```text
train: 100~300개
val: 50~100개
```

---

### 4.2. 확인 항목

Crop 결과에서 다음을 확인한다.

```text
[ ] facepart 5, 6만 사용했는가?
[ ] facepart 5는 왼쪽 볼, facepart 6은 오른쪽 볼로 저장되었는가?
[ ] bbox 좌표가 이미지 범위를 벗어나지 않는가?
[ ] crop 이미지가 실제 볼 부위를 포함하는가?
[ ] crop 이미지가 너무 작거나 깨지지 않았는가?
[ ] 원본 이미지와 JSON 경로가 정상적으로 매칭되었는가?
[ ] annotations에서 pore/pigmentation 라벨이 정상 추출되었는가?
```

---

### 4.3. Crop 테스트 산출물

테스트 실행 후 다음 파일이 생성되어야 한다.

```text
data/cropped_test/train/l_cheek/*.jpg
data/cropped_test/train/r_cheek/*.jpg
data/cropped_test/val/l_cheek/*.jpg
data/cropped_test/val/r_cheek/*.jpg

data/processed/cheek_train_metadata_test.csv
data/processed/cheek_val_metadata_test.csv

results/crop_test_samples/*.jpg
results/crop_test_error_log.csv
```

테스트용 결과는 실제 학습용 결과와 구분하기 위해 `cropped_test`, `metadata_test.csv`처럼 별도 이름을 사용한다.

---

## 5. 2단계: Metadata CSV 검증

### 5.1. 필수 컬럼 확인

`cheek_train_metadata_test.csv`, `cheek_val_metadata_test.csv`에는 다음 컬럼이 있어야 한다.

```text
image_path
original_image_path
original_filename
json_path
id
gender
age
skin_type
sensitive
device
angle
facepart
side
bbox
pore_label
pigmentation_label
split
```

---

### 5.2. 라벨 값 검증

볼 부위 라벨은 0~5 정수여야 한다.

확인 기준:

```text
[ ] pore_label 값이 0~5 범위인가?
[ ] pigmentation_label 값이 0~5 범위인가?
[ ] 라벨 값에 null, NaN, 빈 문자열이 없는가?
[ ] 라벨 dtype이 int로 변환 가능한가?
```

---

### 5.3. 데이터 분포 확인

학습 전에 라벨 분포를 확인한다.

확인 예시:

```text
pore_label 분포:
0: n개
1: n개
2: n개
3: n개
4: n개
5: n개

pigmentation_label 분포:
0: n개
1: n개
2: n개
3: n개
4: n개
5: n개
```

주의:

```text
특정 등급에 데이터가 너무 몰려 있으면 accuracy만으로 성능을 판단하면 안 된다.
본 학습에서는 macro F1-score를 함께 확인한다.
```

---

## 6. 3단계: Dataset 테스트

### 6.1. 목적

CSV를 읽어 PyTorch Dataset이 정상적으로 이미지와 라벨을 반환하는지 확인한다.

Dataset의 `__getitem__`은 다음 값을 반환하는 구조를 권장한다.

```python
image, target = dataset[index]
```

또는 모공/색소침착을 동시에 사용할 경우:

```python
image, targets = dataset[index]

# targets 예시
{
    "pore": pore_label,
    "pigmentation": pigmentation_label
}
```

---

### 6.2. 확인 항목

```text
[ ] image_path에 해당하는 파일이 실제 존재하는가?
[ ] 이미지를 RGB로 변환하는가?
[ ] resize가 정상 적용되는가?
[ ] image tensor shape이 [3, 224, 224]인가?
[ ] label이 int64 또는 long 타입인가?
[ ] label 값이 0~5 범위인가?
```

---

## 7. 4단계: DataLoader 테스트

### 7.1. 목적

DataLoader가 batch 단위로 정상 동작하는지 확인한다.

권장 테스트 설정:

```yaml
image_size: 224
batch_size: 8
num_workers: 0
shuffle: true
```

초기 테스트에서는 Windows 환경 오류를 줄이기 위해 `num_workers=0`을 권장한다.

---

### 7.2. 확인할 shape

단일 타깃 모델 기준:

```text
images.shape = [batch_size, 3, 224, 224]
labels.shape = [batch_size]
```

예시:

```text
images.shape = torch.Size([8, 3, 224, 224])
labels.shape = torch.Size([8])
```

---

## 8. 5단계: ResNet-50 Forward 테스트

### 8.1. 목적

ResNet-50 모델이 batch 이미지를 입력받아 6개 클래스 출력으로 변환되는지 확인한다.

모공 모델 기준 출력:

```text
input:  [batch_size, 3, 224, 224]
output: [batch_size, 6]
```

색소침착 모델도 동일하게 6-class 출력이다.

---

### 8.2. 확인 항목

```text
[ ] torchvision.models.resnet50 가 정상 로드되는가?
[ ] 마지막 fc layer가 num_classes=6으로 교체되었는가?
[ ] forward 결과 shape이 [batch_size, 6]인가?
[ ] CrossEntropyLoss 계산이 정상 동작하는가?
[ ] loss.backward()가 오류 없이 실행되는가?
```

---

## 9. 6단계: 미니 학습 테스트

### 9.1. 목적

전체 학습 전에 소량 데이터로 1 epoch만 학습하여 학습 루프가 정상 동작하는지 확인한다.

권장 설정:

```yaml
backbone: resnet50
pretrained: true
image_size: 224
batch_size: 8
epochs: 1
learning_rate: 0.0001
optimizer: Adam
loss: CrossEntropyLoss
num_classes: 6
```

---

### 9.2. 확인 항목

```text
[ ] train loss가 출력되는가?
[ ] validation loss가 출력되는가?
[ ] accuracy가 계산되는가?
[ ] macro F1-score가 계산되는가?
[ ] checkpoint 저장 코드가 정상 동작하는가?
[ ] GPU 사용 시 CUDA 오류가 없는가?
```

---

## 10. 모델별 테스트 기준

1차 실험에서는 ResNet-50만 사용한다.

```text
1차 테스트 모델: ResNet-50
2차 확장 후보: DINOv3 ViT-L/16
```

DINOv3 ViT-L/16은 초기에 사용하지 않는다.

이유:

```text
- 모델 구조가 ResNet보다 복잡하다.
- 사전학습 가중치 파일 관리가 필요하다.
- 학습 코드 작성 난이도가 높다.
- 먼저 데이터 파이프라인 검증이 필요하다.
```

따라서 테스트 문서와 초기 코드 생성 기준은 반드시 ResNet-50으로 통일한다.

---

## 11. 테스트 통과 기준

아래 항목을 모두 만족하면 전체 학습으로 넘어갈 수 있다.

```text
[ ] crop 이미지가 실제 볼 부위로 잘렸다.
[ ] metadata_test.csv가 정상 생성되었다.
[ ] image_path가 모두 실제 파일을 가리킨다.
[ ] pore_label 값이 0~5 범위이다.
[ ] pigmentation_label 값이 0~5 범위이다.
[ ] Dataset이 image와 label을 정상 반환한다.
[ ] DataLoader batch shape이 정상이다.
[ ] ResNet-50 forward 결과 shape이 [batch_size, 6]이다.
[ ] loss 계산과 backward가 정상 동작한다.
[ ] 1 epoch 미니 학습이 오류 없이 완료된다.
[ ] validation loss, accuracy, macro F1-score가 출력된다.
```

---

## 12. 테스트 실패 시 확인 순서

### 12.1. 이미지 파일을 찾지 못하는 경우

```text
1. info.filename 값 확인
2. 원본 이미지 폴더 위치 확인
3. JSON 폴더와 이미지 폴더 구조 확인
4. TS / VS 하위 전체 검색 로직 확인
```

---

### 12.2. Crop 결과가 이상한 경우

```text
1. bbox 형식이 [x1, y1, x2, y2]인지 확인
2. bbox clipping 적용 여부 확인
3. 원본 이미지 width/height와 bbox 좌표 비교
4. crop 샘플 이미지를 results/crop_test_samples에 저장해 육안 확인
```

---

### 12.3. Loss 계산 오류가 나는 경우

```text
1. 모델 output shape 확인: [batch_size, 6]
2. label shape 확인: [batch_size]
3. label dtype 확인: torch.long
4. label 값 범위 확인: 0~5
5. CrossEntropyLoss에 one-hot label을 넣고 있지 않은지 확인
```

---

### 12.4. DataLoader 오류가 나는 경우

```text
1. image_path 파일 존재 여부 확인
2. PIL 이미지 로딩 가능 여부 확인
3. transform 적용 순서 확인
4. Windows 환경에서는 num_workers=0으로 변경
```

---

## 13. 권장 테스트 실행 순서

```text
1. crop 테스트 스크립트 실행
2. crop 샘플 이미지 육안 확인
3. metadata_test.csv 컬럼 및 라벨 범위 확인
4. Dataset 단일 샘플 로딩 확인
5. DataLoader batch shape 확인
6. ResNet-50 forward 테스트
7. loss 계산 테스트
8. 1 epoch 미니 학습 테스트
9. validation 지표 출력 확인
10. 전체 학습용 crop 및 train 실행
```

---

## 14. 최종 정리

본 프로젝트에서는 먼저 ResNet-50 기반으로 전체 학습 파이프라인을 검증한다.

```text
테스트 단계에서는 성능보다 정상 동작 여부가 중요하다.
```

따라서 초기 테스트에서는 높은 accuracy를 목표로 하지 않고, 데이터 로딩부터 모델 학습까지 오류 없이 연결되는지 확인한다.

테스트가 통과되면 전체 데이터 기준으로 ResNet-50 학습을 진행하고, 이후 성능 개선 단계에서 DINOv3 ViT-L/16을 적용한다.

# 현재 구현 업데이트

`notebooks/jh` 하위의 현재 검증 흐름이 실행 중인 코드와 일치하도록 업데이트되었습니다.

주요 사항:

- 크롭 검증은 이제 `A` 베이스라인 각도 세트를 가정합니다:
  - 왼쪽 볼: `F / Ft / Fb / L15`
  - 오른쪽 볼: `F / Ft / Fb / R15`
- 이미지 파이프라인은 종횡비를 유지하는 리사이즈와 정사각형 패딩을 사용합니다.
- 사전 학습된 ResNet-50 가중치는 다음에서 로드됩니다:
  - `checkpoints/pretrained/resnet50-0676ba61.pth`
- 테스트 체크포인트는 다음 아래에 기록됩니다:
  - `checkpoints/trained/`

현재 스모크 테스트 진입점:

```text
python notebooks/jh/test/test_cheek_crop.py
python notebooks/jh/test/test_cheek_pipeline.py --target pore
python notebooks/jh/test/test_cheek_pipeline.py --target pigmentation
```

최신 운영 요약은 다음을 참조하십시오:

- [cheek_current_training_setup.md](cheek_current_training_setup.md)

# 부록: 현재 코드 우선 적용 사항

`notebooks/jh` 하위의 현재 검증 흐름이 실행 중인 코드와 일치하도록 업데이트되었습니다.

Key points:

- 크롭 검증은 이제 `A` 베이스라인 각도 세트를 가정합니다:
  - 왼쪽 볼: `F / Ft / Fb / L15`
  - 오른쪽 볼: `F / Ft / Fb / R15`
- 이미지 파이프라인은 종횡비를 유지하는 리사이즈와 정사각형 패딩을 사용합니다.
- 사전 학습된 ResNet-50 가중치는 다음에서 로드됩니다:
  - `checkpoints/pretrained/resnet50-0676ba61.pth`
- 테스트 체크포인트는 다음 아래에 기록됩니다:
  - `checkpoints/trained/`

Current smoke-test entrypoints:

```text
python notebooks/jh/test/test_cheek_crop.py
python notebooks/jh/test/test_cheek_pipeline.py --target pore
python notebooks/jh/test/test_cheek_pipeline.py --target pigmentation
```

Current smoke-test outputs:

```text
data/cropped/test/train/l_cheek/*.jpg
data/cropped/test/train/r_cheek/*.jpg
data/cropped/test/val/l_cheek/*.jpg
data/cropped/test/val/r_cheek/*.jpg
data/processed/test/cheek_train_metadata_test.csv
data/processed/test/cheek_val_metadata_test.csv
results/test/crop_samples/
results/test/crop_error_log.csv
```

For the latest consolidated summary, see:

- [cheek_current_training_setup.md](cheek_current_training_setup.md)
