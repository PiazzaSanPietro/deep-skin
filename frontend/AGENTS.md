# Deep Skin Frontend AGENTS.md

## 역할

Streamlit 프론트엔드 에이전트는 Deep Skin 피부 분석 서비스의 사용자 화면을 구현한다.

이 프론트엔드는 FastAPI 백엔드 API를 호출하여 다음 흐름을 제공한다.

사용자 회원가입/로그인  
→ 프로필 입력  
→ 얼굴 이미지 촬영 또는 업로드  
→ 백엔드 분석 요청  
→ 추천 결과 및 피부 분석 리포트 표시

## 최상위 지침

- 프론트엔드는 `frontend/` 폴더 안에서만 작업한다.
- `backend/` 코드는 수정하지 않는다.
- 백엔드 API 호출은 `frontend/services/`에 분리한다.
- 화면 UI 코드는 `frontend/views/`와 `frontend/components/`에 분리한다.
- Streamlit 기본 `pages/` 폴더 기능은 사용하지 않는다. 라우팅은 `app.py`에서 직접 관리한다.
- 공통 스타일은 `frontend/styles/`에 분리한다.
- `app.py`는 라우팅과 세션 상태 관리 중심으로 작성한다.
- Streamlit 기본 UI를 사용하되, CSS를 활용해 서비스 화면처럼 보이도록 구성한다.

## 사용 기술

- Streamlit
- requests
- python-dotenv
- Pillow
- FastAPI 백엔드 API 연동

## 주요 화면

1. 회원가입 화면
2. 로그인 화면
3. 프로필 조회 화면
4. 프로필 수정 화면
5. 사진 촬영 및 이미지 업로드 화면
6. 분석 진행 화면
7. 분석 리포트 화면

## API 연동 기준

사용할 백엔드 API는 다음과 같다.

```text
POST /auth/signup
POST /auth/login
POST /auth/refresh
POST /auth/logout

GET  /users/me/profile
PUT  /users/me/profile

POST /analysis/sessions
POST /analysis/sessions/{session_id}/images

GET  /recommendations/sessions/{session_id}
GET  /analysis/sessions/{session_id}/report
```

## 인증 기준

로그인 성공 시 access_token, refresh_token을 st.session_state에 저장한다.
인증이 필요한 API 요청에는 항상 다음 헤더를 포함한다.

```http
Authorization: Bearer <access_token>
```

401 응답이 발생하면 로그인 화면으로 이동한다.
로그아웃 시 백엔드 /auth/logout 호출 후 st.session_state를 초기화한다.

## 사용자 화면 기준

사용자는 다음 값만 직접 다룬다.

- 회원가입 정보
- 로그인 정보
- 프로필 정보
- 얼굴 이미지 파일 또는 촬영 이미지

사용자 화면에는 다음 값을 노출하지 않는다.

- angle
- facepart
- model_name
- model_version
- raw_part_name
- image_id
- json_record_id

단, 개발 디버깅용 expander 안에서는 선택적으로 표시할 수 있다.

## 디자인 기준

- 서비스명: Deep Skin
- 톤: 깨끗함, 신뢰감, AI 피부 분석, 스킨케어
- 컬러: white, soft blue, teal, lavender, navy
- UI: 둥근 카드, 부드러운 그라데이션 버튼, 칩 형태 성분 표시, 사이드바 내비게이션
- 회원가입/로그인 화면은 넓은 여백과 브랜드 이미지를 활용한다.
- 분석 화면은 사진 촬영/업로드가 명확해야 한다.
- 리포트 화면은 전체 요약과 부위별 분석 결과가 한눈에 보여야 한다.

## 작업 규칙
- 기능 구현 전 관련 문서를 먼저 읽는다.
- 기존 API 응답 구조를 변경하지 않는다.
- 백엔드 API와 맞지 않는 임의 필드명을 만들지 않는다.
- 코드 수정 시 관련 문서도 즉시 수정한다.
- UI 문구, API 흐름, 테스트 방법이 바뀌면 frontend/docs/ 문서를 함께 갱신한다.
- Streamlit 화면에서 오류가 발생하면 사용자 친화적인 메시지를 표시한다.
- 디버깅용 원본 JSON은 기본 화면에 노출하지 않고 st.expander 안에 숨긴다.

## 완료 조건

작업 완료 시 다음을 만족해야 한다.

- 회원가입 가능
- 로그인 가능
- access_token 저장 가능
- 프로필 저장 가능
- 이미지 촬영과 업로드 가능
- 분석 세션 생성 가능
- 이미지 업로드 API 호출 가능
- 추천 결과 조회 가능
- 분석 리포트 조회 가능
- 로그아웃 가능
- Streamlit 실행 가능
- 코드 수정 내용에 맞게 문서가 갱신되어 있음

## 검증 명령

```bash
cd frontend
streamlit run app.py
```

백엔드 서버는 별도 터미널에서 실행한다.

```bash
cd backend
python -m uvicorn app.main:app --reload
```

## 문서 갱신 원칙

코드가 수정되면 관련 문서를 즉시 수정한다.

예시:

- API 호출 방식 수정 → docs/frontend_api_flow.md 수정
- 화면 구조 수정 → docs/frontend_ui_guide.md 수정
- 폴더 구조 수정 → docs/frontend_structure.md 수정
- 인증 흐름 수정 → docs/frontend_state_auth.md 수정
- 리포트 화면 수정 → docs/frontend_report_design.md 수정
- 테스트 방법 수정 → docs/frontend_validation_checklist.md 수정