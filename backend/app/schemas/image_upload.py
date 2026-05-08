from typing import Optional

from pydantic import BaseModel, ConfigDict


class PartResult(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "raw_part_name": "left_cheek",
                "display_part_name": "볼",
                "metric_name": "pore",
                "metric_display_name": "모공",
                "issue_type": "pore",
                "grade_value": 2,
                "severity": "moderate",
                "confidence_score": 0.82,
            }
        }
    )

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
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "image_id": 1,
                "session_id": 1,
                "original_filename": "face.jpg",
                "stored_filename": "550e8400-e29b-41d4-a716-446655440000.jpg",
                "file_path": "uploads/1/1/550e8400-e29b-41d4-a716-446655440000.jpg",
                "width": 1920,
                "height": 1080,
                "upload_status": "processed",
                "session_status": "completed",
                "inference_result": {
                    "model_name": "mock_skin_model",
                    "model_version": "0.0.1",
                    "parts": [
                        {
                            "raw_part_name": "left_cheek",
                            "display_part_name": "볼",
                            "metric_name": "pore",
                            "metric_display_name": "모공",
                            "issue_type": "pore",
                            "grade_value": 2,
                            "severity": "moderate",
                            "confidence_score": 0.82,
                        },
                        {
                            "raw_part_name": "left_eye",
                            "display_part_name": "눈가",
                            "metric_name": "wrinkle",
                            "metric_display_name": "주름",
                            "issue_type": "wrinkle",
                            "grade_value": 3,
                            "severity": "severe",
                            "confidence_score": 0.88,
                        },
                    ],
                },
            }
        }
    )

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
