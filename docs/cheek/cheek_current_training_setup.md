# 볼 부위 현재 학습 설정

## 목적

이 문서는 최신 A-baseline 업데이트 기준으로 `notebooks/jh` 아래에 구현된 현재 학습 설정을 요약한다. 기존 계획 문서와 검증 문서에 더해, 현재 실제로 실행 중인 코드를 기준으로 내용을 보완한다.

## 현재 Baseline

현재 baseline은 `A` 설정이다.

- 왼쪽 볼은 `F / Ft / Fb / L15`를 사용한다.
- 오른쪽 볼은 `F / Ft / Fb / R15`를 사용한다.
- `L30 / R30`은 기본 crop 데이터셋에서 제외한다.

이 규칙은 다음 파일에서 적용된다.

- [crop.py](C:/PROJECT/Deep_skin/notebooks/jh/crop.py)

## 현재 파일 역할 (Current File Roles)

### 학습 코드 (Training code)

- `notebooks/jh/crop.py`
  - 볼 crop 이미지와 메타데이터 CSV를 구축한다.
  - A-baseline 각도 필터링을 적용한다.
  - 볼 crop 마진(margin)을 적용한다.
  - 얇은 측면 뷰 crop에 대한 기본적인 품질 필터링을 적용한다.

- `notebooks/jh/dataset.py`
  - CSV에서 crop 이미지를 로드한다.
  - 종횡비를 유지하는 리사이즈 + 정사각형 패딩을 사용한다.

- `notebooks/jh/model.py`
  - ResNet-50 볼 분류기를 정의한다.
  - `checkpoints/pretrained`에서 로컬 사전 학습 가중치를 로드한다.
  - 백본(backbone) 동결 / 해제를 지원한다.

- `notebooks/jh/train.py`
  - 전체 학습 진입점(entrypoint)이다.
  - 최신(latest) / 최적(best) 체크포인트 저장을 지원한다.
  - 학습 재개(resume training)를 지원한다.
  - 선택적 백본 동결을 지원한다.

### 테스트 코드 (Test code)

- `notebooks/jh/test/test_cheek_crop.py`
  - crop + 메타데이터 스모크 테스트(smoke test)이다.

- `notebooks/jh/test/test_cheek_pipeline.py`
  - 데이터셋 / 데이터로더 / 순전파(forward) / 1-에포크 미니 학습 스모크 테스트이다.

## 체크포인트 레이아웃 (Checkpoint Layout)

### 사전 학습됨 (Pretrained)

외부 사전 학습된 백본 가중치는 다음 위치에 있다.

```text
checkpoints/pretrained/
```

현재 사용 중인 파일:

```text
checkpoints/pretrained/resnet50-0676ba61.pth
```

이 파일은 독창적인 외부 ImageNet 사전 학습된 ResNet-50 가중치이다. 학습 중에 덮어쓰여지지 않는다.

### Trained

학습 출력물은 다음 위치에 있다.:

```text
checkpoints/trained/
```

실제 학습 진입점의 경우, 예상되는 파일은 다음과 같다.:

```text
checkpoints/trained/<target>_latest.pth
checkpoints/trained/<target>_best.pth
```

Examples:

```text
checkpoints/trained/pore_latest.pth
checkpoints/trained/pore_best.pth
checkpoints/trained/pigmentation_latest.pth
checkpoints/trained/pigmentation_best.pth
```

## 각 체크포인트가 저장하는 것

`train.py` saves:

- `epoch`
- `model_state_dict`
- `optimizer_state_dict`
- `best_macro_f1`
- `metrics`
- `config`

이는 체크포인트가 다음과 같은 용도로 사용될 수 있음을 의미한다.:

- continuing training
- keeping the best validation model
- inspecting the run configuration later

## Freeze / Resume Support

### Backbone freeze

`model.py` supports:

- `freeze_backbone=True`
- `freeze_backbone=False`

동결된 경우, 최종 분류기 헤드(head)만 학습 가능하다..

### Resume

`train.py` supports:

- `--resume latest`
- `--resume best`
- `--resume <path-to-checkpoint>`

재개는 다음을 복원한다:

- 모델 가중치
- 호환 가능한 경우의 옵티마이저 상태
- 시작 에포크
- 최적 매크로 F1

## 현재 전처리 규칙

### Crop margin

측면 뷰 crop은 정면 crop보다 더 넓은 마진을 사용한다.

현재 마진 정책은 다음에서 구현된다.:

- [crop.py](C:/PROJECT/Deep_skin/notebooks/jh/crop.py)

### Resize and padding

이미지 파이프라인은 더 이상 직접적인 Resize((224, 224))를 사용하지 않는다.

대신 다음을 사용한다:

1. 종횡비 유지
2. 긴 쪽을 기준으로 리사이즈
3. 정사각형 이미지로 패딩

이는 다음에서 구현된다:

- [dataset.py](C:/PROJECT/Deep_skin/notebooks/jh/dataset.py)

## 현재 학습 명령

### Standard training

```bash
python notebooks/jh/train.py --target pore
python notebooks/jh/train.py --target pigmentation
```

### Freeze backbone

```bash
python notebooks/jh/train.py --target pore --freeze-backbone
```

### Resume training

```bash
python notebooks/jh/train.py --target pore --resume latest
python notebooks/jh/train.py --target pore --resume best
python notebooks/jh/train.py --target pore --resume checkpoints/trained/pore_latest.pth
```

### Mini validation smoke test

```bash
python notebooks/jh/test/test_cheek_crop.py
python notebooks/jh/test/test_cheek_pipeline.py --target pore
python notebooks/jh/test/test_cheek_pipeline.py --target pigmentation
```

## 권장 워크플로우

1. test_cheek_crop.py로 crop 테스트 데이터를 생성 / 갱신한다.
2. test_cheek_pipeline.py로 파이프라인을 검증한다.
3. train.py로 실제 학습을 실행한다.
4. checkpoints/trained에서 latest 및 best 체크포인트를 모니터링한다.
5. 학습이 중단되면 latest에서 재개한다.
6. 평가 또는 내보내기를 위해 best를 사용한다.


## Notes
- checkpoints/pretrained/resnet50-0676ba61.pth는 외부 사전 학습된 데이터이다.
- checkpoints/trained/*.pth는 학습 출력물이다.
- A-베이스라인은 현재 notebooks/jh에서의 기본 운영 정책이다.
