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

### 2.2 `dummy_ai_server.py` (FastAPI 서버)
*   **역할**: HTTP 요청을 수신하고 추론 엔진을 호출하는 인터페이스 역할을 합니다.
*   **작동 방식**:
    *   서버 시작 시(`lifespan`) 모델을 메모리에 로드하여 추론 속도를 최적화합니다.
    *   `/inference/skin` 엔드포인트를 통해 이미지를 수신하고 결과를 JSON으로 반환합니다.

## 3. 설치 및 준비 사항

### 3.1 필요 파일
서버 실행을 위해 아래 파일들이 `backend/scripts` 경로에 존재해야 합니다:
*   `dinov3/`: DINOv3 모델 정의가 포함된 소스 디렉토리.
*   `dinov3_vits16plus_pretrain_lvd1689m-4057cbaa.pth`: Backbone 체크포인트.
*   `../ckpt_kfold_vits_part3/`: 5개의 Head 체크포인트 파일들이 포함된 디렉토리.

### 3.2 의존성
`torch`, `torchvision`, `fastapi`, `uvicorn`, `Pillow`, `numpy` 등이 필요합니다.

## 4. 사용 방법

### 4.1 서버 실행
```bash
cd backend
python -m uvicorn scripts.dummy_ai_server:app --reload --port 9000
```

### 4.2 API 요청 (눈가 분석 예시)
`bbox_left_eye` 파라미터는 선택 사항이며, 없을 경우 전체 이미지를 기준으로 분석합니다.

```bash
curl -X POST "http://localhost:9000/inference/skin" \
     -F "file=@face.jpg" \
     -F "bbox_left_eye=[191, 1432, 411, 1817]"
```

## 5. API 응답 구조
프로젝트의 `InferenceResult` 스키마를 준수합니다.

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
      "confidence_score": 0.8452
    },
    ... (기타 부위는 Mock 데이터)
  ]
}
```

## 6. 확장 가이드
다른 부위(볼, 이마 등)의 실제 추론을 추가하려면:
1. `inference_engine.py`에 해당 부위의 모델 로드 로직을 추가합니다.
2. `dummy_ai_server.py`의 `_MOCK_PARTS_TEMPLATE`에서 해당 부위의 데이터를 엔진 호출 결과로 교체합니다.
