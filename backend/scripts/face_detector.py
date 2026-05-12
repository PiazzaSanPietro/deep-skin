# -*- coding: utf-8 -*-
"""
Face part detector using a YOLO model.

Given an image (path, PIL.Image, or numpy array), returns per-part bounding
boxes in xyxy format. Class names follow the trained YOLO model and are
normalized to the names used by the inference server (e.g. ``l_eye`` →
``left_eye``).
"""

import os
from typing import Any, Dict, List, Optional, Union

from PIL import Image

# YOLO class index → raw class name as trained
CLASS_NAMES = [
    "forehead", "glabella", "l_eye", "r_eye",
    "l_cheek", "r_cheek", "lips", "chin",
]

# Map raw YOLO class names → server-side raw_part_name
PART_NAME_MAP = {
    "forehead": "forehead",
    "glabella": "glabella",
    "l_eye": "left_eye",
    "r_eye": "right_eye",
    "l_cheek": "left_cheek",
    "r_cheek": "right_cheek",
    "lips": "lips",
    "chin": "chin",
}

ImageInput = Union[str, "os.PathLike[str]", Image.Image, Any]


class FaceDetector:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None

    def load(self) -> bool:
        try:
            from ultralytics import YOLO
        except ImportError as e:
            print(f"[face-detector] ultralytics not installed: {e}")
            return False

        if not os.path.exists(self.model_path):
            print(f"[face-detector] model file not found: {self.model_path}")
            return False

        try:
            self.model = YOLO(self.model_path)
            return True
        except Exception as e:
            print(f"[face-detector] failed to load YOLO model: {e}")
            return False

    def detect(
        self,
        image: ImageInput,
        conf: float = 0.25,
        iou: float = 0.5,
        imgsz: int = 1280,
    ) -> List[Dict[str, Any]]:
        if self.model is None:
            return []

        r = self.model.predict(
            source=image, imgsz=imgsz, conf=conf, iou=iou, verbose=False
        )[0]

        boxes = r.boxes.xyxy.cpu().numpy()
        cls_ids = r.boxes.cls.cpu().numpy()
        confs = r.boxes.conf.cpu().numpy()

        detections: List[Dict[str, Any]] = []
        for box, cid, cf in zip(boxes, cls_ids, confs):
            cid = int(cid)
            raw = CLASS_NAMES[cid] if 0 <= cid < len(CLASS_NAMES) else str(cid)
            detections.append({
                "class_id": cid,
                "class_name": raw,
                "raw_part_name": PART_NAME_MAP.get(raw, raw),
                "confidence": float(cf),
                "bbox_xyxy": [float(x) for x in box],
            })
        return detections

    def detect_best_per_part(
        self,
        image: ImageInput,
        conf: float = 0.25,
        iou: float = 0.5,
        imgsz: int = 1280,
    ) -> Dict[str, Dict[str, Any]]:
        """Return one detection per part — the highest-confidence box keyed by
        the server-side ``raw_part_name``."""
        best: Dict[str, Dict[str, Any]] = {}
        for d in self.detect(image, conf=conf, iou=iou, imgsz=imgsz):
            name = d["raw_part_name"]
            if name not in best or d["confidence"] > best[name]["confidence"]:
                best[name] = d
        return best
