
# 3. `frontend/docs/frontend_structure.md`


# Streamlit Frontend Structure Guide

## 권장 폴더 구조

```text
frontend/
├── app.py
├── requirements.txt
├── .env
│
├── assets/
│   ├── logo/
│   │   └── deep_skin_logo.png
│   │
│   ├── illustrations/
│   │   ├── face_guide.png
│   │   └── empty_state.png
│   │
│   └── ui_references/
│       ├── signup_reference.png
│       ├── login_reference.png
│       ├── analysis_reference.png
│       ├── report_reference.png
│       ├── profile_reference.png
│       └── profile_edit_reference.png
│
├── components/
│   ├── layout.py
│   ├── auth_forms.py
│   ├── upload_panel.py
│   ├── profile_cards.py
│   ├── report_cards.py
│   └── common.py
│
├── views/
│   ├── login.py
│   ├── signup.py
│   ├── profile.py
│   ├── profile_edit.py
│   ├── analysis.py
│   └── report.py
│
├── services/
│   ├── api_client.py
│   ├── auth_api.py
│   ├── user_api.py
│   ├── analysis_api.py
│   └── recommendation_api.py
│
├── styles/
│   └── theme.py
│
└── docs/
    ├── frontend_overview.md
    ├── frontend_structure.md
    ├── frontend_api_flow.md
    ├── frontend_ui_guide.md
    ├── frontend_state_auth.md
    ├── frontend_report_design.md
    └── frontend_validation_checklist.md
```

## 파일별 역할

```app.py```
Streamlit 앱 진입점이다.

역할:
- 페이지 라우팅
- 로그인 상태 확인
- 세션 상태 초기화
- 로그인 후 화면을 접힘/펼침 가능한 좌측 내비게이션 컬럼과 본문 컬럼으로 구성

> Streamlit 기본 `pages/` 폴더 기능은 사용하지 않는다.
> 화면은 `views/` 폴더에 두고, 라우팅은 `app.py`에서 직접 관리한다.

```assets``` 
assets/logo/

실제 앱 화면에서 사용할 로고 이미지를 보관한다.

예:
```
frontend/assets/logo/deep_skin_logo.png
```

사용 위치:
- 로그인 화면
- 회원가입 화면
- 사이드바
- 프로필 화면
- 리포트 화면

```assets/illustrations/```

실제 화면에 사용할 일러스트 이미지를 보관한다.

예:

frontend/assets/illustrations/face_guide.png

사용 위치:

- 사진 촬영 가이드
- 이미지 업로드 안내
- 빈 상태 화면

```assets/ui_references/```

프론트엔드 구현 시 참고할 디자인 시안 이미지를 보관한다.

이 이미지는 실제 앱에 그대로 노출하기 위한 파일이 아니라,
Codex/Claude가 UI 분위기와 레이아웃을 참고하기 위한 디자인 가이드다.
```
frontend/assets/ui_references/
├── signup_reference.png
├── login_reference.png
├── analysis_reference.png
├── report_reference.png
├── profile_reference.png
└── profile_edit_reference.png
```

참고 기준:

- signup_reference.png → 회원가입 화면
- login_reference.png → 로그인 화면
- analysis_reference.png → 사진 촬영 및 이미지 업로드 화면
- report_reference.png → 분석 리포트 화면
- profile_reference.png → 프로필 조회 화면
- profile_edit_reference.png → 프로필 수정 화면

구현 시 참고 이미지와 1:1로 완전히 동일하게 만들 필요는 없다.
다만 아래 요소는 최대한 유지한다.

- Deep Skin 로고와 브랜드 톤
- white / soft blue / teal / lavender / navy 색상
- 둥근 카드 UI
- 부드러운 그림자
- 그라데이션 버튼
- 좌측 앱 내 내비게이션
- 칩 형태의 성분/고민 표시
- 넓은 여백과 깔끔한 배치

```services/api_client.py```

백엔드 API 요청 공통 함수 파일이다.

역할:
- base URL 관리
- Authorization 헤더 생성
- 공통 GET/POST/PUT 요청 처리
- 에러 응답 처리

```services/auth_api.py```
인증 API 호출 함수 파일이다.

연결 API:
- POST /auth/signup
- POST /auth/login
- POST /auth/refresh
- POST /auth/logout

```services/user_api.py```
사용자 프로필 API 호출 함수 파일이다.

연결 API:
- GET /users/me/profile
- PUT /users/me/profile

```services/analysis_api.py```
분석 관련 API 호출 함수 파일이다.

연결 API:
- POST /analysis/sessions
- POST /analysis/sessions/{session_id}/images
- GET /analysis/sessions/{session_id}/report

```services/recommendation_api.py```
추천 결과 API 호출 함수 파일이다.

연결 API:
- GET /recommendations/sessions/{session_id}

```views/login.py```
로그인 화면을 담당한다.

```views/signup.py```
회원가입 화면을 담당한다.

```views/profile.py```
프로필 조회 화면을 담당한다.

```views/profile_edit.py```
프로필 수정 화면을 담당한다.

```views/analysis.py```
사진 촬영 및 이미지 업로드 화면을 담당한다.

```views/report.py```
분석 리포트 화면을 담당한다.

```components/layout.py```
공통 레이아웃을 담당한다.

- 로그인 후 화면의 접힘/펼침 가능한 좌측 내비게이션
- expanded / collapsed 사이드바 렌더링 분리
- 헤더
- 로그아웃 버튼
- 페이지 타이틀

```components/report_cards.py```
리포트 카드 UI를 담당한다.

- 전체 요약 카드
- 부위별 카드
- 추천 성분 칩
- 제외 성분 칩
- 관리 팁 리스트

```styles/theme.py```
CSS와 디자인 토큰을 관리한다.

- 컬러
- 카드 스타일
- 버튼 스타일
- 배지 스타일
- 칩 스타일

## 작업 규칙
- API 호출 코드는 views/ 안에 직접 작성하지 않는다.
- API 호출은 반드시 services/를 통해 수행한다.
- 반복되는 UI는 components/로 분리한다.
- 색상과 CSS는 styles/theme.py에 모은다.
- 코드 구조가 변경되면 이 문서를 즉시 수정한다.
