# AI Inference Server Guide (DINOv3 Multi-task)

본 문서는 `backend/scripts` 디렉토리에 위치한 AI 추론 서버의 구조와 사용 방법을 설명합니다.

## 1. 개요

현재 두 종류의 추론 서버가 공존합니다.

| 서버 파일 | 설명 | 추론 범위 |
|---|---|---|
| `multivalue_ai_server.py` | DINOv3 + MultiTaskSkinModel(face_multivalue_inf)로 **전체 부위 등급·측정값**을 동시에 추론하는 신규 서버 | 9개 facepart(0..8) 전부 |
| `dummy_ai_server.py` | (구) 5-Fold ViT 앙상블 기반. 눈가(Part 3)만 실모델, 나머지는 Mock | 눈가만 실모델, 그 외 Mock |

신규 작업은 `multivalue_ai_server.py`를 기준으로 합니다. `dummy_ai_server.py`는 하위 호환용으로 그대로 두었습니다.

## 2. 주요 구성 요소

### 2.1 `face_multivalue_inf/` (멀티태스크 추론 모듈)
*   **역할**: DINOv3 백본 + MultiTaskSkinModel head를 묶어 이미지 한 장과 facepart bbox 딕셔너리만 받으면 전체 라벨을 한 번에 예측.
*   **핵심 파일**:
    *   `infer_image.py` – `EndToEndInferencer` (백본 빌드, TTA, crop, 통합 predict)
    *   `infer.py` – `SkinInferencer` (캐시 특징/멀티태스크 head 추론)
    *   `skin_model.py` – `MultiTaskSkinModel`, `LABEL_REGISTRY`, `FACEPART_TO_TRUNK`
    *   `skin_heads.py` – `MLPTrunk`, `CORNHead`(ordinal), `PoissonHead`(count), `GaussianRegHead`(reg)
*   **출력 라벨**: ordinal(등급, int), count(λ, int 반올림), reg(원 스케일 float). 부위별 키 매핑은 §5 참고.

### 2.2 `inference_engine.py` (구 추론 엔진, dummy 서버 전용)
*   **역할**: dummy_ai_server.py에서 사용. DINOv3 backbone + 5-Fold ensemble head로 눈가(Part 3) 단일 부위 추론.
*   **주요 기능**: 모델 로드, TTA, bbox crop.

### 2.3 `face_detector.py` (얼굴 파트 검출기)
*   **역할**: YOLO 모델로 입력 이미지에서 8개 얼굴 파트 bbox 검출. 두 서버 모두 공유.
*   **주요 기능**:
    *   `FaceDetector.load()`: YOLO 모델(`backend/model/yolo_facecrop_best.pt`) 1회 로드.
    *   `FaceDetector.detect(image)`: 전체 검출 결과 리스트 반환.
    *   `FaceDetector.detect_best_per_part(image)`: 파트별 최고 confidence 박스 dict.
    *   YOLO 클래스명을 서버 표준명으로 매핑 (`l_eye → left_eye` 등).
*   **검출 파트**: `forehead`, `glabella`, `left_eye`, `right_eye`, `left_cheek`, `right_cheek`, `lips`, `chin` (총 8개).

### 2.4 `multivalue_ai_server.py` (신규 FastAPI 서버)
*   **역할**: HTTP 요청 수신 → YOLO bbox 검출 → MultiTaskSkinModel 한 번에 추론 → example_labeling_data JSON 형식으로 part별 응답 빌드.
*   **작동 방식**:
    *   `lifespan`에서 `EndToEndInferencer`(head ckpt + DINOv3 ckpt)와 `FaceDetector`를 1회 로드.
    *   `/inference/skin`:
        1. YOLO로 8개 파트 best bbox(xyxy) 검출.
        2. xyxy → (x, y, w, h) 변환 후 facepart id(1..8)로 키잉.
        3. `EndToEndInferencer.predict(image, bboxes_xywh)` 한 번 호출 → `{label_name: float}`.
        4. 결과를 facepart별로 분배해 9개 객체(part 0..8)를 빌드. 각 객체는 `data/raw/example_labeling_data/0004_01_F_0X.json`과 **동일한 키 구조**(`info`/`images`/`annotations`/`equipment`).
        5. 모델 라벨이 없거나 bbox 미검출인 항목은 더미값(`0`/`0.0`/`null`)으로 폴백.

## 3. 설치 및 준비 사항

### 3.1 필요 파일
| 경로 | 용도 |
|---|---|
| `backend/scripts/dinov3/` | DINOv3 소스 디렉토리 (`~/.cache/torch/hub/facebookresearch_dinov3_main` 도 자동 탐색) |
| `backend/scripts/dinov3_vits16plus_pretrain_lvd1689m-4057cbaa.pth` | DINOv3 backbone 체크포인트 |
| `backend/model/face_multivalue_inf_best.pt` | MultiTaskSkinModel head 체크포인트 (멀티태스크 서버) |
| `backend/ckpt_kfold_vits_part3/` | 5-Fold ensemble head 체크포인트 (dummy 서버 전용) |
| `backend/model/yolo_facecrop_best.pt` | YOLO 얼굴 파트 검출 모델 |

### 3.2 의존성
`torch`, `torchvision`, `fastapi`, `uvicorn`, `Pillow`, `numpy`, `ultralytics` 등.
`backend/scripts/requirements.txt`에 정의되어 있습니다.

## 4. 사용 방법

### 4.1 서버 실행

```bash
# 신규: MultiTask 멀티값 서버
cd backend
python -m uvicorn scripts.multivalue_ai_server:app --reload --port 9001

# 구: 5-Fold 더미 서버 (눈가만 실모델)
python -m uvicorn scripts.dummy_ai_server:app --reload --port 9000
```

### 4.2 API 요청

```bash
curl -X POST "http://localhost:9001/inference/skin" -F "file=@face.jpg"
```

지원 폼 필드:
*   `file` (필수): 이미지 파일
*   `session_id`, `user_id`, `image_id` (선택): 식별자 패스스루용

multivalue 서버는 호출자가 별도 bbox를 넘기지 않습니다 — YOLO 검출만 사용.

## 5. API 응답 구조 (multivalue_ai_server)

응답은 `data/raw/example_labeling_data/` 의 라벨 JSON 9개 파일과 동일한 키 구조로 구성된 `parts` 리스트입니다 (facepart 0..8 순서 고정).

```json
{
  "model_name": "skin_dinov3_multivalue",
  "model_version": "0.1.0",
  "parts": [
    { "info": { ... }, "images": { "facepart": 0, ... }, "annotations": { "acne": null },
      "equipment": { "pigmentation_count": 146, "acne_count": 0 } },
    { "info": { ... }, "images": { "facepart": 1, "bbox": [434, 677, 1685, 1209] },
      "annotations": { "forehead_pigmentation": 2, "forehead_wrinkle": 3 },
      "equipment": { "forehead_moisture": 59.97, "forehead_elasticity_R0": 0.26, "...": "..." } },
    { "...": "facepart 2..8" }
  ],
  "detected_parts": [
    { "raw_part_name": "left_eye", "class_name": "l_eye",
      "confidence": 0.803, "bbox_xyxy": [196.07, 1420.30, 411.79, 1843.80] }
  ]
}
```

전체 예시 응답: `backend/scripts/face_multivalue_inf/example_response.json` 참고.

### 5.1 part별 키 매핑 (모델 라벨 → JSON 키)

| facepart | annotations (등급 int) | equipment (측정값 float / count int) |
|---|---|---|
| 0 full      | `acne: null` (고정) | `pigmentation_count` (← `pigmentation_count`), `acne_count` (← `acne_count`) |
| 1 forehead  | `forehead_pigmentation`, `forehead_wrinkle` | `forehead_moisture` (← `moisture_forehead`), `forehead_elasticity_R0..R9` (← `R{i}_forehead`), `forehead_elasticity_Q0..Q3` (← `Q{i}_forehead`) |
| 2 glabella  | `glabellus_wrinkle` | `null` |
| 3 left_eye  | `l_perocular_wrinkle` | `l_perocular_wrinkle_{Ra,Rmax,Rt,Rz=Rtm,Rp,Rv,Rq,R3z}` (← `{...}_l_eye`. `Rz=Rtm`은 모델의 `Rz_l_eye`) |
| 4 right_eye | `r_perocular_wrinkle` | 위와 동일, `_r_eye` |
| 5 left_cheek | `l_cheek_pore`, `l_cheek_pigmentation` | `l_cheek_moisture`, `l_cheek_elasticity_R0..R9`/`Q0..Q3`, `l_cheek_pore` (← `pore_count_l_cheek`, 개수) |
| 6 right_cheek | `r_cheek_pore`, `r_cheek_pigmentation` | 위와 동일, `_r_cheek` |
| 7 lips      | `lip_dryness` | `null` |
| 8 chin      | `chin_sagging` | `chin_moisture` (현재 라벨 미학습 → 더미 0.0), `chin_elasticity_R0..R9`/`Q0..Q3` |

값 캐스팅: ordinal → `int(round(v))`, count → `int(round(v))`, reg → `float(v)`. 모델이 해당 라벨을 학습하지 않았거나 bbox 미검출이면 동일 키에 더미값(`0`/`0.0`) 또는 `null`로 폴백합니다.

### 5.2 `/health` 응답
```json
{
  "status": "ok",
  "service": "multivalue-ai-inference",
  "device": "cpu",
  "models_loaded": true,
  "face_detector_loaded": true
}
```

## 6. dummy_ai_server.py 응답 (참고)

구 서버는 평탄한 `parts[]` 구조(`raw_part_name`/`grade_value`/`predicted_value`/`severity`/...)를 반환하며, 눈가만 실모델, 나머지는 mock입니다. `multivalue_ai_server.py`와는 응답 스키마가 다르므로 호출 측에서 분기 필요.

요청 시 `bbox_left_eye` 폼 파라미터로 YOLO 결과를 override할 수 있습니다.

```bash
curl -X POST "http://localhost:9000/inference/skin" \
     -F "file=@face.jpg" \
     -F "bbox_left_eye=[191, 1432, 411, 1817]"
```

## 7. 확장 가이드 (multivalue 서버)

새로운 라벨/측정값을 추가하려면:
1. `face_multivalue_inf/skin_model.py`의 `LABEL_REGISTRY`에 라벨을 등록하고 모델을 재학습 → 새 `face_multivalue_inf_best.pt` 저장.
2. `multivalue_ai_server.py`의 `_build_part*` 함수에서 새 라벨을 해당 part의 `annotations`/`equipment`에 라우팅.
3. 더미값/캐스팅 헬퍼(`_as_grade`/`_as_float`/`_as_count`)를 그대로 사용해 폴백 안전성을 유지.

## 8. 얼굴 파트 검출 단독 사용
서버를 거치지 않고 `FaceDetector`를 직접 호출 가능.

```python
from PIL import Image
from scripts.face_detector import FaceDetector

detector = FaceDetector("backend/model/yolo_facecrop_best.pt")
detector.load()

img = Image.open("face.jpg")
detections = detector.detect(img, conf=0.25, iou=0.5, imgsz=1280)
best = detector.detect_best_per_part(img)
print(best["left_eye"]["bbox_xyxy"])
```
