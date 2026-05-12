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
7. GET /analysis/reports/latest
   - 현재 로그인 사용자 기준 최신 completed 리포트 반환
   - 재로그인 후 프론트의 current_session_id가 비어 있을 때 리포트 복구에 사용
8. GET /recommendations/sessions/{session_id}
   - 저장된 추천 결과 반환
```

개발용 JSON 흐름은 5번 대신 `POST /dev/analysis/sessions/{session_id}/json`을 사용합니다.

## 최신 리포트 복구 흐름

로그아웃 시 프론트의 `current_session_id`와 `last_report`는 초기화됩니다. 재로그인 후에는 이전 `session_id`를 클라이언트 저장소에서 복구하지 않고, 백엔드가 현재 로그인한 사용자의 최신 완료 세션을 조회합니다.

```text
GET /analysis/reports/latest
  -> access token에서 current_user 확인
  -> analysis_sessions에서 user_id=current_user.id, status='completed' 조건 조회
  -> analyzed_at DESC, updated_at DESC, created_at DESC 순서로 최신 세션 선택
  -> report_service.get_report(session_id, user_id)와 동일한 ReportResponse 반환
```

이 방식은 로그아웃 후 다른 계정으로 로그인했을 때 localStorage에 남은 `session_id`가 섞이는 문제를 피하기 위한 현재 기준입니다.

## AI 추론 모드

`AI_INFERENCE_MODE` 값에 따라 동작합니다.

- `mock`: `inference_service._run_mock()`이 고정된 부위별 결과를 반환합니다.
- `remote`: `AI_INFERENCE_URL`로 저장된 이미지 파일을 multipart/form-data로 전송하고 응답을 검증합니다.

## 현재 미사용 또는 제한 사항

- `products` 모델과 테이블은 존재하지만 현재 추천/리포트 API에서 직접 조회하지 않습니다.
- `UserProfile.skin_type`, `main_concerns`, `preferred_product_types`는 저장되지만 현재 추천 필터링에는 직접 사용되지 않습니다.
- 현재 추천 필터링에 직접 사용되는 프로필 값은 `sensitive`, `allergy_ingredients`입니다.
- `AnalysisSession.analyzed_at`, `overall_status`, `summary_message` 필드는 모델에 있지만 현재 서비스 흐름에서 적극적으로 갱신하지 않습니다. TODO: 필요 여부 확인.
