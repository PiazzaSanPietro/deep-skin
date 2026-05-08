**역할:** 이미지 업로드 구현 지침서

사용자가 핸드폰으로 촬영하거나 갤러리에서 선택한 얼굴 이미지를 업로드할 수 있도록 한다.

---

# Agent Image Upload Guide

## 목적

사용자가 얼굴 이미지를 업로드하면 백엔드는 이미지를 검증하고 저장한 뒤,  
모델 추론 서비스에 전달하여 피부 분석 결과를 생성한다.

분석 결과는 `skin_part_results` 테이블에 저장하고,  
이후 부위별 리포트와 추천 결과 생성에 사용한다.

---

## 업로드 방식

```http
POST /analysis/sessions/{session_id}/images
Content-Type: multipart/form-data
Authorization: Bearer <access_token>
```

---

## 요청 필드

| 필드 | 타입 | 필수 여부 | 설명 |
|---|---|---|---|
| `file` | File | 필수 | 업로드할 얼굴 이미지 |
| `angle` | int | 선택 | 촬영 각도 |
| `facepart` | int | 선택 | 얼굴 부위 코드 |

---

## 요청 예시

```text
file: face.jpg
angle: 0
facepart: 0
```

---

## 검증 항목

이미지 업로드 시 다음 항목을 검증한다.

- 파일 존재 여부
- 확장자 `jpg`, `jpeg`, `png` 여부
- MIME type `image/jpeg` 또는 `image/png` 여부
- 파일 크기 10MB 이하 여부
- 손상된 이미지 여부
- 이미지 `width`, `height` 확인
- 분석 세션 소유자 확인

---

## 처리 흐름

```text
1. JWT 인증 확인
2. 분석 세션 소유자 확인
3. 이미지 파일 존재 여부 확인
4. 이미지 확장자 검증
5. MIME type 검증
6. 이미지 용량 검증
7. 손상된 이미지 여부 확인
8. 이미지 width/height 확인
9. UUID 기반 저장 파일명 생성
10. 이미지 파일 저장
11. uploaded_images 테이블 저장
12. analysis_sessions.status = processing 변경
13. inference_service.py 호출
14. 모델 추론 결과 검증
15. skin_part_results 테이블 저장
16. 부위별 추천 결과 생성
17. uploaded_images.upload_status = processed 변경
18. analysis_sessions.status = completed 변경
```
---

## 저장 기준

원본 이미지는 파일 시스템에 저장한다.

DB에는 이미지 파일 자체를 저장하지 않고,  
이미지에 대한 메타데이터와 저장 경로만 저장한다.

---

## DB 저장 항목

`uploaded_images` 테이블에는 다음 정보를 저장한다.

| 컬럼 | 설명 |
|---|---|
| `original_filename` | 사용자가 업로드한 원본 파일명 |
| `stored_filename` | 서버에 저장된 파일명 |
| `file_path` | 서버 저장 경로 |
| `content_type` | MIME type |
| `file_size` | 파일 크기 |
| `width` | 이미지 너비 |
| `height` | 이미지 높이 |
| `angle` | 촬영 각도 |
| `facepart` | 얼굴 부위 코드 |
| `upload_status` | 업로드 처리 상태 |

---

## 예외 처리

| 상황 | status code | error_code |
|---|---:|---|
| 파일 없음 | 400 | IMAGE_FILE_REQUIRED |
| 확장자 오류 | 400 | INVALID_IMAGE_EXTENSION |
| MIME type 오류 | 400 | INVALID_IMAGE_TYPE |
| 파일 용량 초과 | 400 | IMAGE_TOO_LARGE |
| 손상된 이미지 | 400 | INVALID_IMAGE_FILE |
| 세션 없음 | 404 | SESSION_NOT_FOUND |
| 다른 사용자 세션 접근 | 403 | SESSION_ACCESS_DENIED |
| 모델 추론 실패 | 500 | INFERENCE_FAILED |

---

## 예외 응답 형식

```json
{
  "success": false,
  "error_code": "IMAGE_TOO_LARGE",
  "message": "이미지 파일 크기는 10MB 이하만 업로드할 수 있습니다."
}
```

---

## 구현 위치

```text
routers/images.py
services/image_service.py
services/inference_service.py
models/uploaded_image.py
models/skin_part_result.py
schemas/image_upload.py
schemas/prediction_result.py
```

## 파일 저장 경로 규칙

이미지는 다음 경로 규칙으로 저장한다.

```text
uploads/skin_images/{user_id}/{session_id}/{uuid_filename}.jpg
```

원본 파일명은 그대로 저장 파일명으로 사용하지 않는다.

파일명 충돌과 보안 문제를 막기 위해 UUID 기반 파일명을 사용한다.

예시:

```text
uploads/skin_images/1/10/550e8400-e29b-41d4-a716-446655440000.jpg
```

---

## 파일명 저장 기준

DB에는 원본 파일명과 서버 저장 파일명을 모두 저장한다.

| 컬럼 | 설명 |
|---|---|
| `original_filename` | 사용자가 업로드한 원본 파일명 |
| `stored_filename` | UUID 기반으로 생성한 서버 저장 파일명 |
| `file_path` | 서버 내부 저장 경로 |

예시:

```text
original_filename = "face.jpg"
stored_filename = "550e8400-e29b-41d4-a716-446655440000.jpg"
file_path = "uploads/skin_images/1/10/550e8400-e29b-41d4-a716-446655440000.jpg"
```

---

## 이미지 삭제 정책

DB에서 이미지 레코드가 삭제되더라도 파일 시스템의 실제 이미지는 자동으로 삭제되지 않는다.

따라서 다음 경우에는 파일 삭제 로직을 별도로 구현한다.

- 분석 세션 삭제
- 사용자 탈퇴
- 이미지 업로드 실패 후 rollback
- 이미지 저장 후 DB 저장 실패
- 모델 추론 실패로 분석 세션을 폐기하는 경우

---

## 이미지 업로드 실패 처리 기준

이미지 업로드 과정에서 실패가 발생하면 실패 위치에 따라 상태값을 다르게 저장한다.

### 이미지 파일 검증 실패

이미지 확장자, MIME type, 용량, 손상 여부 검증에서 실패한 경우에는 DB에 저장하지 않는다.

```text
uploaded_images row 생성 안 함
analysis_sessions.status 유지 또는 failed 처리
```

권장 기준:

```text
파일 검증 실패 → HTTP 400 반환
DB 저장 전 실패 → uploaded_images 생성하지 않음
```

---

### 이미지 저장 후 모델 추론 실패

이미지는 정상 저장되었지만 모델 추론에서 실패한 경우에는 이미지 업로드 기록은 남긴다.

```text
uploaded_images.upload_status = failed
analysis_sessions.status = failed
analysis_sessions.error_message = 실패 사유
```

예시:

```text
uploaded_images.upload_status = "failed"
analysis_sessions.status = "failed"
analysis_sessions.error_message = "모델 추론 중 오류가 발생했습니다."
```

---

### 이미지 저장 후 DB 저장 실패

파일 시스템에는 이미지가 저장되었지만 DB 저장이 실패한 경우에는 파일을 삭제해야 한다.

처리 기준:

```text
1. 이미지 파일 저장
2. DB 저장 시도
3. DB 저장 실패
4. 저장된 이미지 파일 삭제
5. HTTP 500 반환
```

---

## 상태값 기준

### `uploaded_images.upload_status`

```text
uploaded    : 이미지 저장 완료
processing  : 모델 추론 진행 중
processed   : 모델 추론 및 결과 저장 완료
failed      : 이미지 처리 또는 모델 추론 실패
```

### `analysis_sessions.status`

```text
pending     : 분석 세션 생성 직후
processing  : 이미지 업로드 후 분석 진행 중
completed   : 분석 및 추천 생성 완료
failed      : 분석 실패
```

---


---

## 주의 사항

- 이미지 파일은 DB에 직접 저장하지 않는다.
- DB에는 이미지 저장 경로와 메타데이터만 저장한다.
- 업로드된 이미지는 반드시 로그인 사용자와 연결한다.
- 분석 세션 소유자와 현재 로그인 사용자가 같은지 검증한다.
- 모델 추론 코드는 `inference_service.py`에 분리한다.
- 이미지 업로드 API 안에 추천 로직을 직접 작성하지 않는다.
- 추천 생성은 `recommendation_service.py`에서 처리한다.

