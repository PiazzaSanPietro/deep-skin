
# 5. `frontend/docs/frontend_ui_guide.md`


# Frontend UI Guide

## 디자인 목표

Deep Skin 프론트엔드는 AI 피부 분석 서비스처럼 보이도록 구성한다.

핵심 이미지는 다음과 같다.

- 깨끗함
- 신뢰감
- 전문성
- 부드러운 스킨케어 감성
- AI 기반 분석 느낌

## 컬러 팔레트

```text
Primary Navy: #172B4D
Primary Blue: #4F7CFF
Teal: #29C7C7
Lavender: #8B7CF6
Light Blue: #EFF6FF
Light Lavender: #F5F3FF
Background: #F8FBFF
Card White: #FFFFFF
Text Main: #1F2937
Text Sub: #6B7280
Danger: #EF4444
Warning: #F59E0B
Success: #10B981
```

## 공통 UI 스타일

### 카드
- 배경: white
- border-radius: 18px
- border: 1px solid #E5E7EB
- box-shadow: soft shadow
- padding: 24px

### 버튼

Primary 버튼은 blue → teal 또는 blue → lavender 그라데이션을 사용한다.

예시 문구:
```
회원가입
로그인
분석 시작
리포트 확인
새 분석 시작
```

### 칩

추천 성분, 제외 성분, 카테고리는 chip 형태로 표시한다.

예:
```
나이아신아마이드
펩타이드
판테놀
레티놀 제외
BHA 제외
```

## 화면별 UI 기준

### 1. 회원가입 화면

#### 구성
- 왼쪽: 브랜드 설명 영역
- 오른쪽: 회원가입 카드

#### 표시 요소

- Deep Skin 로고
- 서비스 소개 문구
- 이름 입력
- 이메일 입력
- 비밀번호 입력
- 비밀번호 확인 입력
- 회원가입 버튼
- 로그인 이동 링크

#### 문구 예시
```
AI로 더 깊이,
피부를 더 정확하게
맞춤형 피부 분석을 시작해보세요.
```
#### 참고 이미지
`frontend/assets/ui_references/signup_reference.png`

### 2. 로그인 화면

#### 구성
- 왼쪽: 서비스 가치 설명
- 중앙: 로그인 카드
- 오른쪽: 브랜드 일러스트 또는 여백
- 하단: 약관/개인정보/문의 푸터

#### 표시 요소
- 이메일 입력
- 비밀번호 입력
- 로그인 버튼
- 회원가입 이동 링크

로그인 화면은 스크롤 없이 첫 화면 안에 3열 콘텐츠와 하단 푸터가 함께 보여야 한다.

#### 참고 이미지
`frontend/assets/ui_references/login_reference.png`

### 3. 분석 시작 화면
#### 구성
- 사이드바
- 분석 단계 표시
- 사진 촬영 영역
- 이미지 업로드 영역
- 촬영 가이드 카드
- 분석 시작 버튼

#### 단계 표시
```
1 사진 업로드
2 AI 분석
3 리포트 확인
```

#### 이미지 입력

Streamlit 기능:
```
st.camera_input("사진 촬영")
st.file_uploader("이미지 업로드", type=["jpg", "jpeg", "png"])
```

### 사용자 안내 문구
정면 얼굴 사진을 업로드하세요.
밝은 조명에서 촬영하세요.
메이크업이 옅은 상태를 권장합니다.

#### 참고 이미지
`frontend/assets/ui_references/analysis_reference.png`

### 4. 리포트 화면
#### 구성
- 전체 분석 결과 카드
- 부위별 분석 결과 카드
- 추천 카테고리
- 추천 성분
- 제외 성분
- 관리 팁
- 전체 상태 표시
- 양호
- 주의
- 집중 관리 필요

### 부위별 카드

부위 예시:
```
볼
눈가
이마
입술
턱
전체 얼굴
```

#### severity 배지
```
normal   → 양호
mild     → 약한 관리 필요
moderate → 관리 필요
severe   → 집중 관리 필요
```
#### 참고 이미지
`frontend/assets/ui_references/report_reference.png`

### 사이드바

로그인 후 화면에서 표시한다.
Streamlit 네이티브 `st.sidebar` 접힘 상태에 의존하지 않고, 앱 본문을 좌측 내비게이션 컬럼과 우측 콘텐츠 컬럼으로 나누어 구성한다.
상단 메뉴 아이콘으로 좌측 메뉴를 접고, 접힌 상태의 아이콘 레일에서 다시 펼칠 수 있어야 한다.
사이드바는 expanded / collapsed 전용 컨테이너와 CSS를 분리해 새로고침 직후에도 동일한 스타일로 렌더링한다.

메뉴:
```
분석 시작
리포트
프로필
로그아웃
```

### 5. 프로필 조회 화면

#### 구성
- 사이드바
- 프로필 요약 카드
- 기본 정보 카드
- 피부 정보 카드
- 주요 고민 카드
- 알레르기 성분 카드
- 선호 제품 타입 카드
- 최근 분석 요약 카드
- 프로필 수정 버튼

#### 표시 요소
- 이름
- 이메일
- 나이
- 출생연도
- 성별
- 피부 타입
- 민감성 여부
- 주요 고민
- 알레르기 성분
- 선호 제품 타입
- 최근 분석 요약

#### 참고 이미지
`frontend/assets/ui_references/profile_reference.png`

### 6. 프로필 수정 화면

#### 구성
- 사이드바
- 프로필 수정 폼
- 맞춤 추천 반영 항목 카드
- 저장하기 버튼
- 취소 버튼

#### 입력 요소
- 이름
- 이메일
- 나이
- 출생연도
- 성별
- 피부 타입
- 민감성 여부
- 주요 고민
- 알레르기 성분
- 선호 제품 타입

#### 참고 이미지
`frontend/assets/ui_references/profile_edit_reference.png`

## 사용자에게 숨길 값

아래 값은 기본 화면에 노출하지 않는다.
```
session_id
image_id
raw_part_name
model_name
model_version
json_record_id
```
필요하면 개발용 expander 안에만 표시한다.

## 문서 갱신 규칙

화면 구조, 디자인 톤, 표시 문구, 사용자 흐름이 변경되면 이 문서를 즉시 수정한다.
