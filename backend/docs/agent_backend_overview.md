# Backend Overview

현재 백엔드는 FastAPI API 서버입니다. 인증, 프로필, 분석 세션, 이미지 업로드, AI 추론, 추천 생성, 리포트 조회를 담당합니다.

## 현재 폴더 구조

```text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   └── security.py
│   ├── db/
│   │   ├── database.py
│   │   └── session.py
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   └── utils/json_parser.py
├── alembic/
├── docs/
├── scripts/
└── uploads/
```

## 전체 처리 흐름

```text
1. POST /auth/signup
2. POST /auth/login
   - access_token, refresh_token 발급
3. PUT /users/me/profile
   - 피부 타입, 민감 여부, 알러지 성분 등 저장
4. POST /analysis/sessions
   - 분석 세션 생성
5. POST /analysis/sessions/{session_id}/images
   - 이미지 검증 및 저장
   - inference_service.run_inference 호출
   - skin_part_results 저장
   - recommendation_service.generate_and_save 호출
   - part_recommendations 저장
6. GET /analysis/sessions/{session_id}/report
   - 전체 요약 + 부위별 리포트 반환
7. GET /recommendations/sessions/{session_id}
   - 저장된 추천 결과 반환
```

개발용 JSON 흐름은 5번 대신 `POST /dev/analysis/sessions/{session_id}/json`을 사용합니다.

## AI 추론 모드

`AI_INFERENCE_MODE` 값에 따라 동작합니다.

- `mock`: `inference_service._run_mock()`이 고정된 부위별 결과를 반환합니다.
- `remote`: `AI_INFERENCE_URL`로 저장된 이미지 파일을 multipart/form-data로 전송하고 응답을 검증합니다.

## 현재 미사용 또는 제한 사항

- `products` 모델과 테이블은 존재하지만 현재 추천/리포트 API에서 직접 조회하지 않습니다.
- `UserProfile.skin_type`, `main_concerns`, `preferred_product_types`는 저장되지만 현재 추천 필터링에는 직접 사용되지 않습니다.
- 현재 추천 필터링에 직접 사용되는 프로필 값은 `sensitive`, `allergy_ingredients`입니다.
- `AnalysisSession.analyzed_at`, `overall_status`, `summary_message` 필드는 모델에 있지만 현재 서비스 흐름에서 적극적으로 갱신하지 않습니다. TODO: 필요 여부 확인.