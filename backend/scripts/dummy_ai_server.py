"""
Dummy AI inference server — remote 모드 테스트용.

실제 AI 모델 서버가 없을 때 mock inference 응답을 반환한다.
이미지 파일을 multipart/form-data로 수신하고 저장하지 않는다.

실행:
    cd backend
    python -m uvicorn scripts.dummy_ai_server:app --reload --port 9000
"""

from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile

app = FastAPI(title="Dummy AI Inference Server", version="0.0.1")

_MOCK_PARTS = [
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
        "raw_part_name": "right_cheek",
        "display_part_name": "볼",
        "metric_name": "pore",
        "metric_display_name": "모공",
        "issue_type": "pore",
        "grade_value": 1,
        "severity": "mild",
        "confidence_score": 0.79,
    },
    {
        "raw_part_name": "forehead",
        "display_part_name": "이마",
        "metric_name": "wrinkle",
        "metric_display_name": "주름",
        "issue_type": "wrinkle",
        "grade_value": 0,
        "severity": "normal",
        "confidence_score": 0.91,
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
    {
        "raw_part_name": "lips",
        "display_part_name": "입술",
        "metric_name": "dryness",
        "metric_display_name": "건조",
        "issue_type": "dryness",
        "grade_value": 1,
        "severity": "mild",
        "confidence_score": 0.77,
    },
    {
        "raw_part_name": "chin",
        "display_part_name": "턱",
        "metric_name": "sagging",
        "metric_display_name": "처짐",
        "issue_type": "sagging",
        "grade_value": 2,
        "severity": "moderate",
        "confidence_score": 0.74,
    },
]


@app.post("/inference/skin")
async def inference_skin(
    file: UploadFile = File(..., description="분석할 얼굴 이미지 파일"),
    session_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    image_id: Optional[str] = Form(None),
):
    content = await file.read()
    print(
        f"[dummy-ai] 수신 | filename={file.filename} size={len(content)}bytes "
        f"session_id={session_id} user_id={user_id} image_id={image_id}"
    )
    return {
        "model_name": "skin_multitask_model",
        "model_version": "0.1.0",
        "parts": _MOCK_PARTS,
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "dummy-ai-inference"}
