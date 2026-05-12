# AI Inference Server Guide (DINOv3 Ensemble)

본 문서는 `backend/scripts` 디렉토리에 위치한 AI 추론 서버의 구조와 사용 방법을 설명합니다.

## 1. 개요
이 서버는 실제 AI 모델(DINOv3)을 사용하여 피부 상태를 분석하는 API 서버입니다. 현재 개발 및 테스트 편의를 위해 **눈가(Part 3)** 부위만 실제 모델 추론을 수행하며, 나머지 부위는 Mock 데이터를 반환하는 하이브리드 방식으로 작동합니다.

## 2. 주요 구성 요소

### 2.1 `inference_engine.py` (추론 엔진)
*   **역할**: 모델 로드, 전처리, 추론 로직을 캡슐화한 핵심 모듈입니다.
*   **주요 기능**:
    *   DINOv3 Backbone 및 5-Fold Ensemble Head 로드.
    *   이미지 전처리 (Resize, Normalize) 및 TTA(Test Time Augmentation) 지원.
    *   BBox 기반의 지능적 Crop 지원.

### 2.2 `face_detector.py` (얼굴 파트 검출기)
*   **역할**: YOLO 모델을 사용해 입력 이미지에서 8개 얼굴 파트의 bbox를 검출합니다.
*   **주요 기능**:
    *   `FaceDetector.load()`: YOLO 모델(`backend/model/yolo_facecrop_best.pt`)을 메모리에 한 번만 로드.
    *   `FaceDetector.detect(image)`: 모든 검출 결과를 리스트로 반환 (`class_name`, `raw_part_name`, `confidence`, `bbox_xyxy`).
    *   `FaceDetector.detect_best_per_part(image)`: 파트별 최고 confidence 박스만 dict로 반환 (서버에서 사용).
    *   YOLO 클래스명을 서버 표준명으로 매핑 (`l_eye → left_eye`, `l_cheek → left_cheek`, `r_eye → right_eye`, `r_cheek → right_cheek`).
*   **검출 파트**: `forehead`, `glabella`, `left_eye`, `right_eye`, `left_cheek`, `right_cheek`, `lips`, `chin` (총 8개).

### 2.3 `dummy_ai_server.py` (FastAPI 서버)
*   **역할**: HTTP 요청을 수신하고 얼굴 검출기 + 추론 엔진을 호출하는 인터페이스 역할을 합니다.
*   **작동 방식**:
    *   서버 시작 시(`lifespan`) DINOv3 모델과 YOLO 모델을 메모리에 로드합니다.
    *   `/inference/skin` 엔드포인트를 통해 이미지를 수신하면:
        1. YOLO로 8개 얼굴 파트 bbox 자동 검출.
        2. `bbox_left_eye` 파라미터가 없으면 YOLO가 검출한 `left_eye` bbox를 DINOv3 추론에 자동 사용.
        3. 각 파트 응답에 `bbox_xyxy` / `detection_confidence` 첨부.

## 3. 설치 및 준비 사항

### 3.1 필요 파일
서버 실행을 위해 아래 파일들이 존재해야 합니다:
*   `backend/scripts/dinov3/`: DINOv3 모델 정의가 포함된 소스 디렉토리.
*   `backend/scripts/dinov3_vits16plus_pretrain_lvd1689m-4057cbaa.pth`: Backbone 체크포인트.
*   `backend/ckpt_kfold_vits_part3/`: 5개의 Head 체크포인트 파일들이 포함된 디렉토리.
*   `backend/model/yolo_facecrop_best.pt`: YOLO 얼굴 파트 검출 모델.

### 3.2 의존성
`torch`, `torchvision`, `fastapi`, `uvicorn`, `Pillow`, `numpy`, `ultralytics` 등이 필요합니다.
(`requirements.txt`에 정의되어 있음)

## 4. 사용 방법

### 4.1 서버 실행
```bash
cd backend
python -m uvicorn scripts.dummy_ai_server:app --reload --port 9000
```

### 4.2 API 요청 (눈가 분석 예시)
`bbox_left_eye` 파라미터는 선택 사항입니다. 생략 시 YOLO가 자동으로 검출한 `left_eye` bbox가 DINOv3 추론에 사용됩니다. 파라미터를 직접 넘기면 YOLO 결과보다 우선합니다.

```bash
# YOLO 자동 검출 사용
curl -X POST "http://localhost:9000/inference/skin" -F "file=@face.jpg"

# 수동 bbox override
curl -X POST "http://localhost:9000/inference/skin" \
     -F "file=@face.jpg" \
     -F "bbox_left_eye=[191, 1432, 411, 1817]"
```

## 5. API 응답 구조
프로젝트의 `InferenceResult` 스키마를 준수하며, YOLO 검출 결과가 추가로 첨부됩니다.

*   각 `parts[*]` 항목에 `bbox_xyxy` / `detection_confidence` 필드가 추가됩니다 (검출된 파트에 한함).
*   응답 최상위에 전체 검출 결과 `detected_parts` 배열이 포함됩니다.

```json
{
  "model_name": "skin_dinov3_ensemble_model",
  "model_version": "0.2.0",
  "parts": [
    {
      "raw_part_name": "left_eye",
      "display_part_name": "눈가",
      "metric_name": "wrinkle",
      "grade_value": 2,
      "severity": "moderate",
      "confidence_score": 0.8452,
      "bbox_xyxy": [196.07, 1420.30, 411.79, 1843.80],
      "detection_confidence": 0.803
    }
    // ... (기타 부위는 Mock 값 + YOLO bbox)
  ],
  "detected_parts": [
    {
      "raw_part_name": "left_eye",
      "class_name": "l_eye",
      "confidence": 0.803,
      "bbox_xyxy": [196.07, 1420.30, 411.79, 1843.80]
    }
    // ... 최대 8개
  ]
}
```

### 5.1 `/health` 응답
```json
{
  "status": "ok",
  "service": "ai-inference",
  "device": "cpu",
  "models_loaded": true,
  "face_detector_loaded": true
}
```

## 6. 확장 가이드
다른 부위(볼, 이마 등)의 실제 추론을 추가하려면:
1. `inference_engine.py`에 해당 부위의 모델 로드 로직을 추가합니다.
2. `dummy_ai_server.py`의 `_MOCK_PARTS_TEMPLATE`에서 해당 부위의 데이터를 엔진 호출 결과로 교체합니다.
3. YOLO가 이미 해당 파트의 bbox를 검출하므로 `part_bboxes[raw_part_name]["bbox_xyxy"]`를 그대로 추론 엔진에 전달하면 됩니다.

## 7. 얼굴 파트 검출 단독 사용
서버를 거치지 않고 `FaceDetector`를 직접 사용할 수도 있습니다.

```python
from PIL import Image
from scripts.face_detector import FaceDetector

detector = FaceDetector("backend/model/yolo_facecrop_best.pt")
detector.load()

img = Image.open("face.jpg")

# 모든 검출 결과
detections = detector.detect(img, conf=0.25, iou=0.5, imgsz=1280)

# 파트별 최고 confidence 박스만
best = detector.detect_best_per_part(img)
print(best["left_eye"]["bbox_xyxy"])
```
