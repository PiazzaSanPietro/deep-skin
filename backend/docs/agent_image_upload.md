# Image Upload and Analysis Flow

현재 이미지 업로드 구현은 `app/routers/images.py`와 `app/services/image_service.py` 기준입니다.

## Endpoint

```http
POST /analysis/sessions/{session_id}/images
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

## Request fields

| Field | Required | 설명 |
|---|---:|---|
| `file` | Yes | 분석할 얼굴 이미지 |
| `angle` | No | 개발/테스트용 촬영 각도 메타데이터 |
| `facepart` | No | 개발/테스트용 얼굴 부위 메타데이터 |

현재 실제 서비스 흐름에서는 `file`만 필수입니다. `angle`, `facepart`는 저장은 되지만 모델 판단을 대체하지 않습니다.

## 지원 파일

- 확장자: `.jpg`, `.jpeg`, `.png`
- MIME type: `image/jpeg`, `image/png`
- 최대 크기: `MAX_IMAGE_SIZE_MB` 환경 변수 기준, 기본 10MB
- Pillow로 이미지 정상 여부와 width/height 확인

## 저장 위치

```text
{UPLOAD_DIR}/{user_id}/{session_id}/{uuid}.jpg
```

기본값:

```text
uploads/skin_images/{user_id}/{session_id}/{uuid}.jpg
```

주의: 현재 저장 파일명은 원본 확장자와 관계없이 `uuid.jpg` 형식입니다. 파일 내용은 업로드된 원본 bytes를 그대로 저장합니다.

## 처리 순서

```text
1. 인증 사용자 확인
2. analysis_sessions 존재 여부 확인
3. 세션 소유자 확인
4. 파일명/확장자 검증
5. 파일 bytes 읽기
6. MIME type 검증
7. 파일 크기 검증
8. Pillow로 이미지 검증 및 width/height 추출
9. 로컬 파일 저장
10. uploaded_images row 생성
11. analysis_sessions.status = processing
12. inference_service.run_inference 호출
13. 기존 이미지 기반 skin_part_results 삭제
14. inference parts를 skin_part_results에 저장
15. uploaded_images.upload_status = processed
16. analysis_sessions.status = completed
17. recommendation_service.generate_and_save 호출
18. ImageUploadResponse 반환
```

추론 또는 저장 중 실패하면:

- `uploaded_images.upload_status = failed`
- `uploaded_images.failure_reason` 기록
- `analysis_sessions.status = failed`
- `analysis_sessions.error_message` 기록
- API는 `INFERENCE_FAILED` 에러를 반환

## Response

```json
{
  "image_id": 1,
  "session_id": 1,
  "original_filename": "face.jpg",
  "stored_filename": "<uuid>.jpg",
  "file_path": "uploads/skin_images/1/1/<uuid>.jpg",
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
        "confidence_score": 0.82
      }
    ]
  }
}
```

## 주요 에러 코드

`app/core/exceptions.py` 기준:

| error_code | 조건 |
|---|---|
| `SESSION_NOT_FOUND` | 세션 없음 |
| `SESSION_ACCESS_DENIED` | 다른 사용자의 세션 |
| `IMAGE_FILE_REQUIRED` | 파일 없음 |
| `INVALID_IMAGE_EXTENSION` | 확장자 미지원 |
| `INVALID_IMAGE_TYPE` | MIME type 미지원 |
| `IMAGE_TOO_LARGE` | 용량 초과 |
| `INVALID_IMAGE_FILE` | Pillow 검증 실패 |
| `INFERENCE_FAILED` | 추론/결과 저장 실패 |