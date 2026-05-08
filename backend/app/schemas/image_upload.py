from typing import Optional

from pydantic import BaseModel


class PartResult(BaseModel):
    raw_part_name: str
    display_part_name: str
    metric_name: str
    metric_display_name: str
    issue_type: str
    grade_value: int
    severity: str
    confidence_score: float


class InferenceResult(BaseModel):
    model_name: str
    model_version: str
    parts: list[PartResult]


class ImageUploadResponse(BaseModel):
    image_id: int
    session_id: int
    original_filename: str
    stored_filename: str
    file_path: str
    width: Optional[int]
    height: Optional[int]
    upload_status: str
    session_status: str
    inference_result: InferenceResult
