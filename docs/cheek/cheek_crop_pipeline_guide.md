# 볼 부위 Crop 데이터 생성 가이드

## 1. 문서 목적

본 문서는 AI-Hub 한국인 피부상태 데이터셋에서 **양쪽 볼(facepart 5, 6)** 라벨 JSON을 읽고, 원본 얼굴 이미지에서 bbox 기준으로 볼 영역을 crop하여 학습용 이미지와 메타데이터 CSV를 생성하기 위한 기준을 정리한다.

이 문서는 Claude, Codex, ChatGPT 등 코드 생성 도구가 `src/crop.py` 또는 전처리 스크립트를 작성할 때 참고할 수 있는 개발 명세서 역할을 한다.

---

## 2. 사용 대상 데이터

본 프로젝트에서 사용하는 데이터는 원본 이미지와 JSON 라벨로 구성된다.

```text
원본 이미지  → data/raw/aihub_skin/Training/01. 원천데이터/TS/...
라벨 JSON   → data/raw/aihub_skin/Training/02. 라벨링데이터/TL/...
검증 이미지  → data/raw/aihub_skin/Validation/01. 원천데이터/VS/...
검증 JSON   → data/raw/aihub_skin/Validation/02. 라벨링데이터/VL/...
```

데이터셋의 JSON은 `info`, `images`, `annotations`, `equipment` 영역으로 구성된다.

```json
{
  "info": {},
  "images": {},
  "annotations": {},
  "equipment": {}
}
```

본 crop 과정에서는 `info`, `images`, `annotations`만 사용하고, `equipment`는 회귀용 측정값이므로 1차 분류 학습에서는 제외한다.

또한 현재 단계에서는 화장품 추천 DB가 연결되어 있지 않으므로, crop 결과는 추천용 데이터가 아니라 **피부 상태 분류 모델 학습용 데이터**를 만드는 데 집중한다.

---

## 3. 원본 데이터 저장 기준

AI-Hub에서 받은 원본 데이터는 `data/raw/aihub_skin/` 아래에 원본 구조를 유지하여 저장한다.

```text
face_skin_project/
└── data/
    └── raw/
        └── aihub_skin/
            ├── Other/
            │   ├── measurement_data.csv
            │   └── meta_data.csv
            │
            ├── Training/
            │   ├── 01. 원천데이터/
            │   │   └── TS/
            │   │       ├── 1. 디지털카메라/
            │   │       ├── 2. 스마트패드/
            │   │       └── 3. 스마트폰/
            │   │
            │   └── 02. 라벨링데이터/
            │       └── TL/
            │           ├── 1. 디지털카메라/
            │           ├── 2. 스마트패드/
            │           └── 3. 스마트폰/
            │
            └── Validation/
                ├── 01. 원천데이터/
                │   └── VS/
                │       ├── 1. 디지털카메라/
                │       ├── 2. 스마트패드/
                │       └── 3. 스마트폰/
                │
                └── 02. 라벨링데이터/
                    └── VL/
                        ├── 1. 디지털카메라/
                        ├── 2. 스마트패드/
                        └── 3. 스마트폰/
```

---

## 4. Crop 대상 기준

본 담당 범위는 양쪽 볼이다.

| JSON 값 | 부위 | 사용할 라벨 |
|---:|---|---|
| `facepart = 5` | 왼쪽 볼 | `l_cheek_pore`, `l_cheek_pigmentation` |
| `facepart = 6` | 오른쪽 볼 | `r_cheek_pore`, `r_cheek_pigmentation` |

주의할 점:

```text
파일명 끝의 _05, _06만 기준으로 판단하지 말고,
반드시 JSON 내부 images.facepart 값을 함께 확인한다.
```

예시:

```text
0002_01_F_05.json → images.facepart == 5 → 왼쪽 볼
0002_01_F_06.json → images.facepart == 6 → 오른쪽 볼
```

---

## 5. JSON에서 사용할 필드

### 5.1. info

| 필드 | 사용 목적 |
|---|---|
| `info.filename` | 원본 이미지 파일명 |
| `info.id` | 사용자 ID |
| `info.gender` | 분석/필터링용 메타정보 |
| `info.age` | 분석/필터링용 메타정보 |
| `info.skin_type` | 피부 타입 메타정보 |
| `info.sensitive` | 민감 여부 메타정보 |

### 5.2. images

| 필드 | 사용 목적 |
|---|---|
| `images.device` | 촬영 장비 구분 |
| `images.width` | 원본 이미지 너비 |
| `images.height` | 원본 이미지 높이 |
| `images.angle` | 촬영 각도 구분 |
| `images.facepart` | 볼 부위 필터링 기준 |
| `images.bbox` | crop 좌표 |

### 5.3. annotations

| facepart | 사용할 annotation |
|---:|---|
| 5 | `l_cheek_pore`, `l_cheek_pigmentation` |
| 6 | `r_cheek_pore`, `r_cheek_pigmentation` |

### 5.4. equipment

`equipment`는 장비 측정값이며 회귀 학습용이다.

```text
1차 분류 학습에서는 사용하지 않는다.
단, 원본 JSON에는 유지되어 있으므로 삭제하지 않는다.
```

---

## 6. bbox 해석 기준

JSON의 `images.bbox`는 다음 형식으로 사용한다.

```text
bbox = [x1, y1, x2, y2]
```

즉, 좌상단 좌표와 우하단 좌표 기준으로 해석한다.

```text
x1 = bbox[0]
y1 = bbox[1]
x2 = bbox[2]
y2 = bbox[3]
```

Crop 시에는 다음 방식으로 자른다.

```python
crop_img = img.crop((x1, y1, x2, y2))
```

주의:

```text
일부 문서에서는 bbox를 [x, y, w, h]로 설명할 수 있으나,
제공된 실제 JSON 예시에서는 [x1, y1, x2, y2] 형태로 사용하는 것이 자연스럽다.
따라서 crop 코드 작성 시 실제 crop 결과를 샘플 이미지로 반드시 확인한다.
```

---

## 7. 이미지 경로 매칭 규칙

JSON에는 원본 이미지 파일명이 들어 있다.

```json
"info": {
  "filename": "0002_01_F.jpg"
}
```

라벨 JSON 파일명은 부위 코드가 붙는다.

```text
0002_01_F_05.json
0002_01_F_06.json
```

원본 이미지는 부위 코드가 붙지 않는다.

```text
0002_01_F.jpg
```

따라서 이미지 경로를 찾을 때는 다음 순서로 처리한다.

```text
1. JSON 파일 읽기
2. info.filename 값 추출
3. JSON 파일이 위치한 사용자 폴더 또는 같은 장비 폴더 기준으로 원본 이미지 검색
4. 찾지 못하면 TS 또는 VS 하위 전체에서 filename 검색
5. 이미지가 없으면 오류 로그에 기록하고 skip
```

---

## 8. Crop 결과 저장 위치

Crop한 이미지는 `data/cropped/`에 저장한다.

```text
data/cropped/
├── train/
│   ├── l_cheek/
│   └── r_cheek/
└── val/
    ├── l_cheek/
    └── r_cheek/
```

저장 파일명은 원본 이미지명과 facepart를 함께 사용한다.

```text
0002_01_F_05.jpg  # 왼쪽 볼
0002_01_F_06.jpg  # 오른쪽 볼
```

동일 파일명이 중복될 가능성을 줄이기 위해 사용자 ID를 포함해도 된다.

```text
0002_0002_01_F_05.jpg
0002_0002_01_F_06.jpg
```

권장 파일명:

```text
{id}_{original_stem}_{facepart:02d}.jpg
```

예시:

```text
0002_0002_01_F_05.jpg
0002_0002_01_F_06.jpg
```

---

## 9. Crop 후 생성할 CSV

Crop 과정이 끝나면 `data/processed/cheek_train_metadata.csv`, `data/processed/cheek_val_metadata.csv`를 생성한다.

### 9.1. CSV 컬럼

| 컬럼명 | 설명 |
|---|---|
| `image_path` | crop 이미지 저장 경로 |
| `original_image_path` | 원본 이미지 경로 |
| `original_filename` | 원본 이미지 파일명 |
| `json_path` | 사용한 JSON 라벨 경로 |
| `id` | 사용자 ID |
| `gender` | 성별 |
| `age` | 나이 |
| `skin_type` | 피부 타입 코드 |
| `sensitive` | 민감 여부 코드 |
| `device` | 촬영 장비 코드 |
| `angle` | 촬영 각도 코드 |
| `facepart` | 5 또는 6 |
| `side` | `left` 또는 `right` |
| `bbox` | crop 좌표 |
| `pore_label` | 모공 등급 |
| `pigmentation_label` | 색소침착 등급 |
| `split` | train 또는 val |

### 9.2. CSV 예시

```csv
image_path,original_image_path,original_filename,json_path,id,gender,age,skin_type,sensitive,device,angle,facepart,side,bbox,pore_label,pigmentation_label,split
data/cropped/train/l_cheek/0002_0002_01_F_05.jpg,data/raw/aihub_skin/Training/01. 원천데이터/TS/1. 디지털카메라/0002/0002_01_F.jpg,0002_01_F.jpg,data/raw/aihub_skin/Training/02. 라벨링데이터/TL/1. 디지털카메라/0002/0002_01_F_05.json,0002,F,50,0,0,0,0,5,left,"[347,1717,865,2390]",2,3,train
data/cropped/train/r_cheek/0002_0002_01_F_06.jpg,data/raw/aihub_skin/Training/01. 원천데이터/TS/1. 디지털카메라/0002/0002_01_F.jpg,0002_01_F.jpg,data/raw/aihub_skin/Training/02. 라벨링데이터/TL/1. 디지털카메라/0002/0002_01_F_06.json,0002,F,50,0,0,0,0,6,right,"[1379,1710,1853,2377]",2,3,train
```

---

## 10. Crop 스크립트 요구사항

`src/crop.py` 또는 별도 실행 스크립트는 다음 기능을 가져야 한다.

```text
1. raw 데이터 루트 경로를 입력받는다.
2. Training/TL, Validation/VL 하위의 모든 JSON을 탐색한다.
3. images.facepart가 5 또는 6인 JSON만 필터링한다.
4. info.filename으로 원본 이미지를 찾는다.
5. images.bbox를 기준으로 볼 영역을 crop한다.
6. facepart에 따라 l_cheek 또는 r_cheek 폴더에 저장한다.
7. annotations에서 pore/pigmentation 라벨을 추출한다.
8. crop 결과와 메타정보를 CSV로 저장한다.
9. 실패한 파일은 error log로 저장한다.
```

---

## 11. 예외 처리 기준

다음 경우는 학습 데이터에서 제외하고 로그에 기록한다.

| 상황 | 처리 |
|---|---|
| 원본 이미지 파일 없음 | skip 후 로그 저장 |
| JSON 파싱 실패 | skip 후 로그 저장 |
| `facepart`가 5, 6이 아님 | skip |
| `bbox`가 없음 | skip 후 로그 저장 |
| bbox 좌표가 이미지 범위를 벗어남 | 이미지 크기 내로 clipping 후 로그 기록 |
| annotations에 라벨이 없음 | skip 후 로그 저장 |
| crop 결과 크기가 너무 작음 | skip 또는 로그 기록 |

bbox clipping 기준:

```text
x1 = max(0, x1)
y1 = max(0, y1)
x2 = min(image_width, x2)
y2 = min(image_height, y2)
```

---

## 12. 검증용 샘플 확인

Crop 스크립트 작성 후 반드시 샘플 이미지를 저장해 눈으로 확인한다.

확인할 항목:

```text
- facepart 5가 실제 왼쪽 볼 영역인지
- facepart 6이 실제 오른쪽 볼 영역인지
- bbox가 너무 크게 또는 작게 잘리지 않았는지
- 이미지가 회전되거나 깨지지 않았는지
- train/val 저장 경로가 올바른지
- CSV의 label 값이 JSON annotations와 일치하는지
```

샘플 확인용 결과는 다음 경로에 저장할 수 있다.

```text
results/crop_samples/
```

---

## 13. 최종 산출물

Crop 과정이 끝나면 다음 파일이 생성되어야 한다.

이 단계의 산출물은 모델 학습용 crop 이미지와 metadata CSV이며, 화장품 추천 결과는 포함하지 않는다.

```text
data/cropped/train/l_cheek/*.jpg
data/cropped/train/r_cheek/*.jpg
data/cropped/val/l_cheek/*.jpg
data/cropped/val/r_cheek/*.jpg

data/processed/cheek_train_metadata.csv
data/processed/cheek_val_metadata.csv

results/crop_error_log.csv
results/crop_samples/*.jpg
```

단, `data/`와 `results/`는 기본적으로 GitHub에 업로드하지 않는다.

---

## 14. 구현 위치

권장 구현 위치:

```text
src/crop.py
```

또는 실행 스크립트를 별도로 분리할 경우:

```text
scripts/build_cheek_crop_dataset.py
```

현재 프로젝트 구조가 단순한 경우에는 `src/crop.py`에 crop 관련 함수를 작성하고, 노트북 또는 임시 실행 파일에서 호출해도 된다.

---

## 15. 최종 처리 흐름

```text
1. JSON 라벨 파일 전체 탐색
2. facepart 5, 6만 필터링
3. info.filename 기준 원본 이미지 찾기
4. bbox 좌표 보정
5. 볼 영역 crop
6. data/cropped에 이미지 저장
7. annotations에서 모공/색소침착 등급 추출
8. data/processed에 metadata CSV 저장
9. crop 샘플 육안 검증
10. 학습 코드에서 CSV를 읽어 Dataset 구성
```
