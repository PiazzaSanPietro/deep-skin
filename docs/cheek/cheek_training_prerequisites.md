# 볼 부위 모델 학습 전 사전 이해 문서

## 1. 문서 목적

본 문서는 양쪽 볼(facepart 5, 6) 부위의 **모공 및 색소침착 등급 분류 모델**을 학습하기 전에 개발자가 반드시 이해해야 하는 기준을 정리한다.

이 문서는 Claude, Codex, ChatGPT 등 코드 생성 도구가 `dataset.py`, `model.py`, `train.py`, `predict.py`를 작성하기 전에 참고하는 사전 명세서 역할을 한다.

---

## 2. 프로젝트 1차 목표

본 프로젝트의 1차 목표는 **화장품 추천 DB 연동이 아니라 피부 상태 분류 모델 학습**이다.

현재는 화장품 제품 DB, 성분 DB, 사용자 구매 이력 DB가 구축되어 있지 않으므로 특정 제품 추천은 구현 범위에서 제외한다.

```text
볼 crop 이미지
→ 모공 등급 분류
→ 색소침착 등급 분류
→ 예측 결과 JSON 생성
→ 추후 추천 DB 또는 rule-based 추천 모듈과 연결
```

즉, 1차 모델은 화장품을 직접 추천하는 모델이 아니라 **피부 상태를 정량화하는 분류 모델**이다.
화장품 추천 기능은 모델 예측 결과를 활용하는 서비스 확장 단계로 분리한다.

---

## 3. 학습 대상

담당 부위는 양쪽 볼이다.

| facepart | 부위 | 분류 라벨 |
|---:|---|---|
| 5 | 왼쪽 볼 | `l_cheek_pore`, `l_cheek_pigmentation` |
| 6 | 오른쪽 볼 | `r_cheek_pore`, `r_cheek_pigmentation` |

본 프로젝트에서는 `labeling_codes_guide.md` 기준으로 다음과 같이 통일한다.

```text
facepart 5 → 왼쪽 볼
facepart 6 → 오른쪽 볼
```

---

## 4. Classification과 Regression 구분

JSON에는 분류용 라벨과 회귀용 라벨이 같이 들어 있다.

| JSON 영역 | 의미 | 학습 유형 | 1차 사용 여부 |
|---|---|---|---|
| `annotations` | 전문가 진단 등급 | Classification | 사용 |
| `equipment` | 장비 측정 수치 | Regression | 제외 |

1차 구현에서는 `annotations`만 사용한다.

```text
사용:
- l_cheek_pore
- l_cheek_pigmentation
- r_cheek_pore
- r_cheek_pigmentation

제외:
- l_cheek_moisture
- r_cheek_moisture
- l_cheek_elasticity_*
- r_cheek_elasticity_*
- l_cheek_pore 장비 측정값
- r_cheek_pore 장비 측정값
```

주의:

```text
annotations의 l_cheek_pore는 등급 분류 라벨이고,
equipment의 l_cheek_pore는 장비 측정 수치이다.
이름이 비슷하지만 학습 유형이 다르므로 혼동하면 안 된다.
```

---

## 5. 라벨 범위

볼 부위 라벨은 모두 0~5 정수 등급이다.

| 라벨 | 범위 | 클래스 수 |
|---|---:|---:|
| `l_cheek_pore` | 0~5 | 6 |
| `r_cheek_pore` | 0~5 | 6 |
| `l_cheek_pigmentation` | 0~5 | 6 |
| `r_cheek_pigmentation` | 0~5 | 6 |

등급 해석:

| 값 | 의미 |
|---:|---|
| 0 | 없음 / 정상 |
| 1 | 경미 |
| 2 | 보통 |
| 3 | 심함 |
| 4 | 매우 심함 |
| 5 | 극심함 |

---

## 6. 학습 데이터 입력 형태

학습 코드는 원본 JSON을 직접 반복해서 읽기보다는, crop 과정에서 생성한 CSV를 읽는 구조를 권장한다.

권장 입력 파일:

```text
data/processed/cheek_train_metadata.csv
data/processed/cheek_val_metadata.csv
```

CSV에는 crop 이미지 경로와 정답 라벨이 들어 있어야 한다.

필수 컬럼:

| 컬럼명 | 설명 |
|---|---|
| `image_path` | crop 이미지 경로 |
| `facepart` | 5 또는 6 |
| `side` | left 또는 right |
| `pore_label` | 모공 등급 |
| `pigmentation_label` | 색소침착 등급 |
| `split` | train 또는 val |

권장 추가 컬럼:

| 컬럼명 | 사용 목적 |
|---|---|
| `id` | 사용자 단위 데이터 누수 확인 |
| `gender` | 성능 분석용 |
| `age` | 성능 분석용 |
| `skin_type` | 성능 분석용 |
| `sensitive` | 성능 분석용 |
| `device` | 장비별 성능 분석용 |
| `angle` | 각도별 성능 분석용 |
| `bbox` | crop 검증용 |
| `original_image_path` | 원본 추적용 |
| `json_path` | 라벨 추적용 |

---

## 7. 모델 입력 이미지 기준

모델 입력 이미지는 crop된 볼 이미지이다.

권장 전처리:

```text
1. RGB 변환
2. resize: 224x224 또는 256x256
3. tensor 변환
4. ImageNet mean/std 기준 normalize
```

ResNet 계열을 사용할 경우 일반적으로 224x224를 사용한다.
DINOv3 ViT-L/16 백본을 사용할 경우 224 또는 256 등 실험 설정을 명확히 고정한다.

---

## 8. 모델 출력 설계

볼 부위는 예측 대상이 2개이다.

```text
1. pore
2. pigmentation
```

### 방식 A. 모델 2개 사용

```text
cheek_pore_model: 6 classes
cheek_pigmentation_model: 6 classes
```

장점:

```text
- 구현이 가장 단순하다.
- 각 라벨별 성능 확인이 쉽다.
- 오류 발생 시 디버깅이 쉽다.
```

단점:

```text
- 모델 파일이 2개가 된다.
- 추론 시 모델을 2번 호출할 수 있다.
```

### 방식 B. 멀티헤드 모델 1개 사용

```text
shared backbone
├── pore_head: 6 classes
└── pigmentation_head: 6 classes
```

장점:

```text
- 하나의 모델로 두 라벨을 동시에 예측한다.
- 서비스 연결 시 모델 관리가 편하다.
```

단점:

```text
- 학습 코드가 조금 더 복잡하다.
- loss를 두 개 계산해서 합산해야 한다.
```

1차 구현에서는 방식 A를 추천한다.
팀에서 모델 관리까지 고려한다면 방식 B로 확장할 수 있다.

---

## 9. Loss와 평가 지표

분류 문제이므로 기본 손실 함수는 CrossEntropyLoss를 사용한다.

```text
loss = CrossEntropyLoss(pred, label)
```

멀티헤드 모델을 사용할 경우:

```text
loss = pore_loss + pigmentation_loss
```

평가 지표:

| 지표 | 사용 목적 |
|---|---|
| Accuracy | 전체 정답률 확인 |
| Macro F1-score | 클래스 불균형 대응 |
| Confusion Matrix | 어떤 등급을 헷갈리는지 확인 |
| Class Distribution | 등급별 데이터 개수 확인 |

피부 등급 데이터는 특정 등급에 몰릴 가능성이 있으므로 Accuracy만 보지 않고 F1-score와 confusion matrix를 함께 확인한다.

---

## 10. 데이터 누수 주의

동일한 사용자 ID가 train과 validation에 동시에 들어가면 데이터 누수가 발생할 수 있다.

예를 들어 같은 사람의 왼쪽 볼은 train에 있고 오른쪽 볼은 validation에 있으면, 검증 성능이 실제보다 높게 나올 수 있다.

권장 기준:

```text
가능하면 id 기준으로 train/val을 분리한다.
```

AI-Hub에서 이미 Training/Validation으로 분리되어 있다면 우선 해당 분리를 따른다.
단, 내부적으로 추가 split을 만들 경우에는 반드시 id 단위로 분리한다.

---

## 11. 좌우 볼 처리 기준

좌우 볼을 하나의 데이터셋으로 합쳐 학습할 수 있다.

```text
l_cheek_pore → pore_label
r_cheek_pore → pore_label
l_cheek_pigmentation → pigmentation_label
r_cheek_pigmentation → pigmentation_label
```

즉, 학습 CSV에서는 왼쪽/오른쪽 라벨명을 공통 타깃명으로 정규화할 수 있다.

예시:

```csv
image_path,side,pore_label,pigmentation_label
data/cropped/train/l_cheek/0002_0002_01_F_05.jpg,left,2,3
data/cropped/train/r_cheek/0002_0002_01_F_06.jpg,right,2,3
```

모델이 좌우 정보를 알 필요가 있다면 `side`를 메타데이터로 유지한다.
이미지만으로 학습하는 1차 모델에서는 `side`를 입력 피처로 사용하지 않는다.

---

## 12. 사전학습 백본 사용 기준

현재 사용할 수 있는 백본 예시:

```text
ResNet 계열
DINOv3 ViT-L/16 사전학습 가중치
```

DINOv3 사전학습 가중치 파일은 다음 위치에 저장한다.

```text
checkpoints/pretrained/dinov3_vitl16_pretrain_lvd1689m-8aa4cbdd.pth
```

이 파일은 용량이 크므로 GitHub에 업로드하지 않는다.

팀원이 동일하게 실행할 수 있도록 README에 다운로드 경로와 저장 위치를 명시한다.

---

## 13. 학습 코드 구성 기준

권장 파일 역할:

```text
src/dataset.py
→ cheek_train_metadata.csv를 읽어 PyTorch Dataset 구성

src/model.py
→ ResNet 또는 DINOv3 기반 분류 모델 정의

src/train.py
→ 학습 루프, validation, checkpoint 저장

src/predict.py
→ 저장된 모델을 불러와 단일 이미지 예측 및 예측 JSON 생성

src/utils/config.py
→ batch_size, image_size, learning_rate 등 설정값 관리

src/utils/paths.py
→ data, checkpoints, results 경로 관리

src/utils/seed.py
→ random seed 고정
```

---

## 14. 학습 설정 초안

1차 실험 기준 설정:

```yaml
image_size: 224
batch_size: 32
epochs: 10
learning_rate: 0.0001
optimizer: Adam
loss: CrossEntropyLoss
num_classes: 6
backbone: resnet50
```

DINOv3를 사용할 경우:

```yaml
backbone: dinov3_vitl16
pretrained_path: checkpoints/pretrained/dinov3_vitl16_pretrain_lvd1689m-8aa4cbdd.pth
num_classes: 6
```

---

## 15. Checkpoint 저장 기준

학습된 모델은 `checkpoints/trained/`에 저장한다.

```text
checkpoints/trained/cheek_pore_best.pt
checkpoints/trained/cheek_pigmentation_best.pt
```

멀티헤드 모델일 경우:

```text
checkpoints/trained/cheek_multitask_best.pt
```

저장 기준:

```text
validation loss가 가장 낮은 모델
또는 validation macro F1-score가 가장 높은 모델
```

---

## 16. 추론 결과 JSON 기준

모델 예측 결과는 추후 추천 시스템과 연결할 수 있도록 JSON 형태로 반환한다.

현재 단계에서는 화장품 추천 DB가 없으므로 JSON에는 **예측 결과까지만 포함**한다.
특정 제품명, 브랜드명, 구매 링크는 포함하지 않는다.

예시:

```json
{
  "facepart": "cheek",
  "input": {
    "image_path": "data/cropped/val/l_cheek/0002_0002_01_F_05.jpg",
    "side": "left"
  },
  "predictions": {
    "pore": {
      "level": 2,
      "label": "보통",
      "probability": 0.81
    },
    "pigmentation": {
      "level": 3,
      "label": "심함",
      "probability": 0.76
    }
  }
}
```

추후 추천 기능을 붙일 경우에는 아래처럼 별도 모듈에서 확장한다.

```text
predict.py
→ 피부 상태 예측 JSON 생성

recommend.py
→ 예측 등급 + 화장품 DB 또는 rule-based 기준으로 추천 결과 생성
```

---

## 17. 화장품 추천 기능 처리 기준

현재 단계에서는 화장품 추천 기능을 1차 구현 범위에 포함하지 않는다.

제외 이유:

```text
- 화장품 제품 DB가 아직 구축되어 있지 않다.
- 성분/카테고리 매칭 기준이 아직 확정되지 않았다.
- 추천 품질을 검증할 평가 데이터가 없다.
- 모델 학습 전에는 추천보다 피부 상태 예측 성능 검증이 우선이다.
```

따라서 1차 산출물은 다음으로 제한한다.

```text
- 모공 등급 예측 결과
- 색소침착 등급 예측 결과
- 예측 확률
- 예측 결과 JSON
- validation 성능 지표
```

추천 기능은 2차 확장 단계에서 아래 방식 중 하나로 구현한다.

| 방식 | 설명 | 적용 시점 |
|---|---|---|
| Rule-based 추천 | 등급 조건에 따라 카테고리/성분 추천 | DB가 없을 때 임시 구현 |
| DB 기반 추천 | 제품 DB, 성분 DB, 피부 고민 태그를 매칭 | 서비스화 단계 |
| 개인화 추천 | 피부 타입, 민감 여부, 사용자 선호 반영 | 고도화 단계 |

주의:

```text
추천 결과를 제공할 경우 의학적 진단이 아니라 뷰티 케어 참고 정보로 표현한다.
```

---

## 18. 학습 전 체크리스트

학습 코드를 실행하기 전에 다음을 확인한다.

```text
[ ] data/raw/aihub_skin 원본 데이터가 존재한다.
[ ] facepart 5, 6 JSON만 crop에 사용했다.
[ ] data/cropped/train, data/cropped/val 이미지가 생성되었다.
[ ] cheek_train_metadata.csv가 생성되었다.
[ ] cheek_val_metadata.csv가 생성되었다.
[ ] pore_label, pigmentation_label 값이 0~5 범위이다.
[ ] train/val에 같은 ID가 섞이지 않았는지 확인했다.
[ ] 클래스별 데이터 분포를 확인했다.
[ ] 샘플 crop 이미지를 육안 검증했다.
[ ] checkpoints/pretrained 또는 torchvision pretrained 설정을 확인했다.
```

---

## 19. 1차 구현 범위

1차 구현에서는 다음까지만 완료한다.

```text
1. crop 이미지 생성
2. train/val metadata CSV 생성
3. ResNet 기반 분류 모델 학습
4. 모공 등급 예측
5. 색소침착 등급 예측
6. validation 성능 지표 확인
7. best checkpoint 저장
8. 예측 결과 JSON 생성
```

1차 구현에서 제외하는 항목:

```text
- 화장품 제품 DB 구축
- 특정 화장품 제품 추천
- 구매 링크 연결
- 사용자 구매 이력 기반 개인화 추천
- 추천 결과 정량 평가
```

2차 확장 후보:

```text
- DINOv3 백본 적용
- 멀티헤드 모델 적용
- equipment 기반 회귀 모델 추가
- 피부 타입/민감 여부를 분석 결과에 반영
- rule-based 화장품 카테고리/성분 추천 모듈 추가
- 화장품 제품 DB 연결
- Gradio 또는 Streamlit 앱 연결
```

---

## 20. 최종 흐름

```text
1. data/raw에 원본 데이터 저장
2. JSON에서 facepart 5, 6 필터링
3. bbox로 양쪽 볼 crop
4. data/cropped에 crop 이미지 저장
5. data/processed에 metadata CSV 저장
6. Dataset이 CSV를 읽어 이미지와 라벨 반환
7. 모델이 pore/pigmentation 등급 분류
8. validation 지표 확인
9. best checkpoint 저장
10. predict.py에서 예측 결과 JSON 반환
11. 추후 recommend.py 또는 DB 기반 추천 모듈과 연결
```
