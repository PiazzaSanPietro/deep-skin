"""
Multi-value AI inference server.

DINOv3 백본 + MultiTaskSkinModel(face_multivalue_inf) head로 9개 facepart(0..8)
전체에 대한 등급/측정값을 추론한다. YOLO 얼굴 파트 검출기로 facepart bbox를
얻은 뒤, 한 번의 EndToEndInferencer.predict 호출로 모든 라벨을 얻고
data/raw/example_labeling_data/ 의 JSON 형식과 동일한 키 구조로 part별 응답을
구성한다.

실행:
    cd backend
    python -m uvicorn scripts.multivalue_ai_server:app --reload --port 9001
"""

from __future__ import annotations

import io
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)

# face_multivalue_inf는 sibling-relative import(`from infer import ...`)를 사용하므로
# 패키지 디렉토리를 sys.path에 추가해 모듈을 그대로 로드한다.
_MV_DIR = os.path.join(SCRIPT_DIR, "face_multivalue_inf")
if _MV_DIR not in sys.path:
    sys.path.insert(0, _MV_DIR)

# infer_image.py가 `from dinov3.models...`로 임포트하므로 dinov3 패키지 루트를 추가한다.
_DINOV3_DIR = os.path.join(SCRIPT_DIR, "dinov3")
if _DINOV3_DIR not in sys.path:
    sys.path.insert(0, _DINOV3_DIR)

try:
    from scripts.face_detector import PART_NAME_MAP, FaceDetector
except ImportError:
    from face_detector import PART_NAME_MAP, FaceDetector

from infer_image import EndToEndInferencer  # noqa: E402

# ===================================================================
# Paths
# ===================================================================
DINOV3_CKPT = os.path.join(SCRIPT_DIR, "dinov3_vits16plus_pretrain_lvd1689m-4057cbaa.pth")
HEAD_CKPT = os.path.join(BASE_DIR, "model", "face_multivalue_inf_best_v2.pt")
YOLO_CKPT = os.path.join(BASE_DIR, "model", "yolo_facecrop_best.pt")

# raw_part_name(서버측) → facepart id
PART_NAME_TO_FACEPART = {
    "forehead": 1,
    "glabella": 2,
    "left_eye": 3,
    "right_eye": 4,
    "left_cheek": 5,
    "right_cheek": 6,
    "lips": 7,
    "chin": 8,
}

# ===================================================================
# 더미값 (모델 출력이 없거나 부위 미검출일 때 채울 값)
# ===================================================================
_DUMMY_INFO = {
    "filename": "uploaded.jpg",
    "id": "0000",
    "gender": "U",
    "age": 30,
    "date": "2024-01-01",
    "skin_type": 0,
    "sensitive": 0,
}

_DUMMY_GRADE = 0
_DUMMY_FLOAT = 0.0
_DUMMY_COUNT = 0


# ===================================================================
# Engines
# ===================================================================
engine: Optional[EndToEndInferencer] = None
face_detector = FaceDetector(model_path=YOLO_CKPT)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    try:
        engine = EndToEndInferencer(
            head_checkpoint=HEAD_CKPT,
            dinov3_checkpoint=DINOV3_CKPT,
            model_key="vits",
            device="cuda",
            use_tta=True,
        )
        print(f"[multivalue] EndToEndInferencer loaded on {engine.device}")
    except Exception as e:
        print(f"[multivalue] Failed to load EndToEndInferencer: {e}")
        engine = None

    if not face_detector.load():
        print("[multivalue] Warning: failed to load YOLO face detector.")
    yield


app = FastAPI(title="Multi-value AI Inference Server", version="0.1.0", lifespan=lifespan)


# ===================================================================
# Builders — example_labeling_data JSON 구조에 맞춰 part별 객체 생성
# ===================================================================

def _as_grade(results: Dict[str, float], key: str) -> int:
    v = results.get(key)
    if v is None:
        return _DUMMY_GRADE
    try:
        return int(round(float(v)))
    except Exception:
        return _DUMMY_GRADE


def _as_float(results: Dict[str, float], key: str) -> float:
    v = results.get(key)
    if v is None:
        return _DUMMY_FLOAT
    try:
        return float(v)
    except Exception:
        return _DUMMY_FLOAT


def _as_count(results: Dict[str, float], key: str) -> int:
    v = results.get(key)
    if v is None:
        return _DUMMY_COUNT
    try:
        return int(round(float(v)))
    except Exception:
        return _DUMMY_COUNT


def _info(filename: str) -> Dict[str, Any]:
    info = dict(_DUMMY_INFO)
    info["filename"] = filename
    return info


def _images(facepart: int, W: int, H: int, bbox_xyxy: Optional[List[float]]) -> Dict[str, Any]:
    if bbox_xyxy is None:
        bbox = [0, 0, W, H]
    else:
        bbox = [int(round(x)) for x in bbox_xyxy]
    return {
        "device": 0,
        "width": W,
        "height": H,
        "angle": 0,
        "facepart": facepart,
        "bbox": bbox,
    }


def _build_part0(filename: str, W: int, H: int, results: Dict[str, float]) -> Dict[str, Any]:
    return {
        "info": _info(filename),
        "images": _images(0, W, H, [0, 0, W, H]),
        "annotations": {"acne": None},
        "equipment": {
            "pigmentation_count": _as_count(results, "pigmentation_count"),
            "acne_count": _as_count(results, "acne_count"),
        },
    }


def _build_part1(filename, W, H, bbox, results) -> Dict[str, Any]:
    equipment = {"forehead_moisture": _as_float(results, "moisture_forehead")}
    for i in range(10):
        equipment[f"forehead_elasticity_R{i}"] = _as_float(results, f"R{i}_forehead")
    for i in range(4):
        equipment[f"forehead_elasticity_Q{i}"] = _as_float(results, f"Q{i}_forehead")
    return {
        "info": _info(filename),
        "images": _images(1, W, H, bbox),
        "annotations": {
            "forehead_pigmentation": _as_grade(results, "forehead_pigmentation"),
            "forehead_wrinkle": _as_grade(results, "forehead_wrinkle"),
        },
        "equipment": equipment,
    }


def _build_part2(filename, W, H, bbox, results) -> Dict[str, Any]:
    return {
        "info": _info(filename),
        "images": _images(2, W, H, bbox),
        "annotations": {"glabellus_wrinkle": _as_grade(results, "glabellus_wrinkle")},
        "equipment": None,
    }


def _build_eye(filename, W, H, bbox, results, side: str, facepart: int) -> Dict[str, Any]:
    # side: "l" or "r"
    prefix = f"{side}_perocular_wrinkle"
    measures = ("Ra", "Rmax", "Rt", "Rz", "Rp", "Rv", "Rq", "R3z")
    # JSON 키 중 Rz는 `Rz=Rtm` 으로 들어가는 점에 유의
    out_keys = {
        "Ra": "Ra", "Rmax": "Rmax", "Rt": "Rt",
        "Rz": "Rz=Rtm", "Rp": "Rp", "Rv": "Rv",
        "Rq": "Rq", "R3z": "R3z",
    }
    equipment: Dict[str, Any] = {}
    for m in measures:
        equipment[f"{prefix}_{out_keys[m]}"] = _as_float(results, f"{m}_{side}_eye")
    return {
        "info": _info(filename),
        "images": _images(facepart, W, H, bbox),
        "annotations": {prefix: _as_grade(results, prefix)},
        "equipment": equipment,
    }


def _build_cheek(filename, W, H, bbox, results, side: str, facepart: int) -> Dict[str, Any]:
    cheek_key = f"{side}_cheek"
    equipment: Dict[str, Any] = {f"{cheek_key}_moisture": _as_float(results, f"moisture_{cheek_key}")}
    for i in range(10):
        equipment[f"{cheek_key}_elasticity_R{i}"] = _as_float(results, f"R{i}_{cheek_key}")
    for i in range(4):
        equipment[f"{cheek_key}_elasticity_Q{i}"] = _as_float(results, f"Q{i}_{cheek_key}")
    equipment[f"{cheek_key}_pore"] = float(_as_count(results, f"pore_count_{cheek_key}"))
    return {
        "info": _info(filename),
        "images": _images(facepart, W, H, bbox),
        "annotations": {
            f"{cheek_key}_pore": _as_grade(results, f"{cheek_key}_pore"),
            f"{cheek_key}_pigmentation": _as_grade(results, f"{cheek_key}_pigmentation"),
        },
        "equipment": equipment,
    }


def _build_part7(filename, W, H, bbox, results) -> Dict[str, Any]:
    return {
        "info": _info(filename),
        "images": _images(7, W, H, bbox),
        "annotations": {"lip_dryness": _as_grade(results, "lip_dryness")},
        "equipment": None,
    }


def _build_part8(filename, W, H, bbox, results) -> Dict[str, Any]:
    equipment: Dict[str, Any] = {}
    for i in range(10):
        equipment[f"chin_elasticity_R{i}"] = _as_float(results, f"R{i}_chin")
    for i in range(4):
        equipment[f"chin_elasticity_Q{i}"] = _as_float(results, f"Q{i}_chin")
    return {
        "info": _info(filename),
        "images": _images(8, W, H, bbox),
        "annotations": {"chin_sagging": _as_grade(results, "chin_sagging")},
        "equipment": equipment,
    }


def _build_response_parts(
    filename: str,
    W: int,
    H: int,
    part_bboxes_xyxy: Dict[str, List[float]],
    results: Dict[str, float],
) -> List[Dict[str, Any]]:
    def b(name: str) -> Optional[List[float]]:
        d = part_bboxes_xyxy.get(name)
        return d["bbox_xyxy"] if d else None

    return [
        _build_part0(filename, W, H, results),
        _build_part1(filename, W, H, b("forehead"), results),
        _build_part2(filename, W, H, b("glabella"), results),
        _build_eye(filename, W, H, b("left_eye"), results, "l", 3),
        _build_eye(filename, W, H, b("right_eye"), results, "r", 4),
        _build_cheek(filename, W, H, b("left_cheek"), results, "l", 5),
        _build_cheek(filename, W, H, b("right_cheek"), results, "r", 6),
        _build_part7(filename, W, H, b("lips"), results),
        _build_part8(filename, W, H, b("chin"), results),
    ]


# ===================================================================
# Endpoint
# ===================================================================

def _xyxy_to_xywh(xyxy: List[float]) -> Tuple[int, int, int, int]:
    x1, y1, x2, y2 = xyxy
    return (int(round(x1)), int(round(y1)), int(round(x2 - x1)), int(round(y2 - y1)))


@app.post("/inference/skin")
async def inference_skin(
    file: UploadFile = File(..., description="분석할 얼굴 이미지 파일"),
    session_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    image_id: Optional[str] = Form(None),
):
    try:
        content = await file.read()
        image = Image.open(io.BytesIO(content)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {e}")

    W, H = image.size
    print(f"[multivalue] 수신 | filename={file.filename} size={len(content)}bytes ({W}x{H})")

    # 1) YOLO 얼굴 파트 검출
    part_bboxes: Dict[str, Dict[str, Any]] = {}
    if face_detector.model is not None:
        try:
            part_bboxes = face_detector.detect_best_per_part(image)
        except Exception as e:
            print(f"[multivalue] face detection failed: {e}")

    # 2) bbox 딕셔너리 (facepart id → (x, y, w, h))
    # 검출된 부위는 해당 bbox 사용, 미검출 부위는 전체 이미지를 fallback으로 사용
    # → 모든 facepart가 추론되어 더미 0 값이 남지 않도록 보장
    bboxes_xywh: Dict[int, Tuple[int, int, int, int]] = {}
    for raw_name, det in part_bboxes.items():
        fp = PART_NAME_TO_FACEPART.get(raw_name)
        if fp is None:
            continue
        bboxes_xywh[fp] = _xyxy_to_xywh(det["bbox_xyxy"])

    # 미검출 facepart에 전체 이미지 bbox 할당 (fallback)
    full_bbox = (0, 0, W, H)
    for fp in PART_NAME_TO_FACEPART.values():
        if fp not in bboxes_xywh:
            bboxes_xywh[fp] = full_bbox

    # 3) MultiTask 추론 (모든 facepart 한 번에)
    results: Dict[str, float] = {}
    if engine is not None:
        try:
            results = engine.predict(image, bboxes_xywh)
        except Exception as e:
            print(f"[multivalue] inference failed: {e}")

    # 4) part별 응답 빌드 (example_labeling_data 형식)
    parts = _build_response_parts(file.filename or "uploaded.jpg", W, H, part_bboxes, results)

    return {
        "model_name": "skin_dinov3_multivalue",
        "model_version": "0.1.0",
        "parts": parts,
        "detected_parts": [
            {
                "raw_part_name": name,
                "class_name": d["class_name"],
                "confidence": d["confidence"],
                "bbox_xyxy": d["bbox_xyxy"],
            }
            for name, d in part_bboxes.items()
        ],
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "multivalue-ai-inference",
        "device": str(engine.device) if engine is not None else "n/a",
        "models_loaded": engine is not None,
        "face_detector_loaded": face_detector.model is not None,
    }
