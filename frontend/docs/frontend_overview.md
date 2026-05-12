
# 2. `frontend/docs/frontend_overview.md`


# Deep Skin Frontend Overview

## 목적

Deep Skin 프론트엔드는 사용자가 얼굴 이미지를 업로드하거나 촬영하고, AI 피부 분석 결과와 맞춤형 스킨케어 추천을 확인할 수 있는 Streamlit 기반 웹 화면이다.

## 전체 사용자 흐름

```text
회원가입
→ 로그인
→ 프로필 입력
→ 사진 촬영 또는 이미지 업로드
→ 분석 요청
→ 추천 결과 확인
→ 분석 리포트 확인
```

## 프론트엔드 역할

프론트엔드는 다음 역할을 담당한다.

- 사용자 입력 화면 제공
- FastAPI 백엔드 API 호출
- JWT access token 관리
- 이미지 파일 업로드
- 분석 결과 시각화
- 추천 성분/제외 성분/관리 팁 표시
- 백엔드에서 내려주는 `predicted_value` / `measured_value`를 활용해 더 세밀한 피부 분석 수치 표시 가능
- 단, 현재 추천 로직과 상태 표시는 `severity` 기준을 유지한다

## 백엔드와의 관계

프론트엔드는 AI 모델을 직접 호출하지 않는다.

```text
Streamlit Frontend
→ FastAPI Backend
→ AI Inference Server
→ FastAPI Backend
→ Streamlit Frontend
```

프론트엔드는 백엔드 API만 호출한다.

## 주요 기능

### 1. 인증
- 회원가입
- 로그인
- 로그아웃
- access_token 저장
- 인증 실패 시 로그인 화면 이동

### 2. 프로필 관리
- 나이
- 출생연도
- 성별
- 피부 타입
- 민감성 여부
- 주요 고민
- 알레르기 성분
- 선호 제품 타입

### 3. 이미지 분석
- st.camera_input을 통한 촬영
- st.file_uploader를 통한 이미지 업로드
- 백엔드 이미지 업로드 API 호출
- 분석 완료 후 리포트 화면 이동

### 4. 리포트 표시
- 전체 분석 상태
- 주요 관리 필요 지표
- 부위별 분석 결과
- 예측 수치 (`predicted_value` 기반 — 이미지 업로드 경로)
- 측정 수치 (`measured_value` 기반 — dev JSON / AI-Hub JSON 경로)
- 추천 카테고리
- 추천 성분
- 제외 성분
- 관리 팁

## 최종 사용자 화면 기준

사용자는 다음 흐름만 인식한다.

```text
사진 업로드
→ 분석 시작
→ 결과 확인
```

다음 내부 값은 사용자에게 직접 노출하지 않는다.

- session_id
- image_id
- raw_part_name
- model_name
- model_version
- angle
- facepart

## 개발/디버깅 기준

디버깅이 필요한 경우에만 st.expander("개발용 응답 확인") 안에서 원본 API 응답을 확인할 수 있다.