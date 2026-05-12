# 8. `frontend/docs/frontend_validation_checklist.md`

# Frontend Validation Checklist

## 실행 전 준비

백엔드 서버 실행:

```bash
cd backend
python -m uvicorn app.main:app --reload
```

프론트 서버 실행:
```bash
cd frontend
streamlit run app.py
```

.env 확인:
```bash
BACKEND_API_URL=http://localhost:8000
```

## 필수 테스트
### 1. 회원가입 테스트

확인 항목:

- 이름 입력 가능
- 이메일 입력 가능
- 비밀번호 입력 가능
- 회원가입 버튼 클릭 가능
- 성공 시 로그인 화면 이동
- 중복 이메일이면 오류 메시지 표시

### 2. 로그인 테스트

확인 항목:

- 이메일/비밀번호 입력 가능
- 로그인 성공 시 access_token 저장
- 로그인 성공 후 GET /users/me/profile 자동 호출
- 프로필 미완성이면 프로필 수정 화면으로 이동
- 프로필 완성이면 분석 화면으로 이동
- 로그인 실패 시 오류 메시지 표시

### 3. 프로필 조회 테스트

확인 항목:

- 기본 정보 카드 표시 (이름, 이메일, 나이, 성별)
- 피부 정보 카드 표시 (피부 타입, 민감성 여부)
- 주요 고민 카드 표시
- 알레르기 성분 카드 표시
- 선호 제품 타입 카드 표시
- 최근 분석 요약 카드 표시
- 프로필 수정 버튼 노출

### 4. 프로필 수정 테스트

확인 항목:

- 나이 입력 가능
- 성별 선택 가능
- 피부 타입 선택 가능
- 민감성 여부 선택 가능
- 주요 고민 복수 선택 가능
- 알레르기 성분 입력 가능
- 선호 제품 타입 입력 가능
- 저장 성공 메시지 표시
- 저장 성공 후 분석 화면으로 이동
- 취소 버튼으로 프로필 조회 화면 복귀

### 5. 이미지 업로드 테스트

확인 항목:

- st.camera_input으로 촬영 가능
- st.file_uploader로 jpg/png 업로드 가능
- 업로드 전 분석 시작 버튼 비활성 또는 안내 표시
- 이미지 업로드 후 세션 생성 API 호출
- 이미지 업로드 API 호출
- 업로드 성공 후 리포트 화면 이동

### 6. 추천 결과 테스트

확인 항목:

- 추천 카테고리 표시
- 추천 성분 표시
- 제외 성분 표시
- 제외 사유 표시
- 관리 팁 표시

### 7. 리포트 화면 테스트

확인 항목:

- overall_summary.status 표시
- overall_summary.main_message 표시
- main_issues 표시
- part_reports 카드 표시
- 볼/눈가/이마/입술/턱 카드 표시
- normal 상태도 표시
- severe 상태가 강조 표시
- `current_session_id`가 있으면 `GET /analysis/sessions/{session_id}/report`로 리포트가 표시되는지
- 로그아웃 후 같은 계정으로 재로그인하고 리포트 메뉴에 들어갔을 때 `GET /analysis/reports/latest`로 최신 완료 리포트가 복구되는지
- 최신 리포트 복구 성공 시 `current_session_id`와 `last_report`가 다시 채워지는지
- 분석 이력이 없는 계정에서는 최신 리포트 API 404 후 "분석 결과 없음" 상태가 표시되는지

#### 회귀값 표시 확인 항목

- `part_reports[].issues[].predicted_value`가 null이 아니면 "예측값: X.XX" 형태로 표시되는지
- `part_reports[].issues[].measured_value`가 null이 아니면 "측정값: X.XX" 형태로 표시되는지
- `predicted_value`와 `measured_value`가 모두 null이면 기존 `grade_value` / `severity` 화면이 깨지지 않는지
- `measured_value`와 `predicted_value`가 동시에 null이 아닌 경우 `measured_value` 우선 표시 여부 확인
- 표시 라벨이 `predicted_value` / `measured_value` 필드명 그대로가 아닌 "예측값" / "측정값"으로 변환되는지

### 8. 로그아웃 테스트

확인 항목:

- 로그아웃 버튼 클릭 가능
- /auth/logout 호출
- session_state 초기화
- 로그인 화면 이동

#### 에러 케이스
백엔드 서버가 꺼져 있을 때

기대 동작:
```
백엔드 서버에 연결할 수 없습니다.
```

#### 토큰 만료 또는 401

기대 동작:
```
로그인이 만료되었습니다. 다시 로그인해주세요.
```

#### 이미지 형식 오류

기대 동작:
```
jpg, jpeg, png 파일만 업로드할 수 있습니다.
```

#### 분석 실패

기대 동작:
```
분석에 실패했습니다. 다시 시도해주세요.
```

## 코드 품질 확인

가능하면 다음 명령을 실행한다.
```bash
python -m compileall frontend
```

선택적으로 ruff를 사용할 경우:
```bash
ruff check frontend
```

## 완료 기준

아래 흐름이 끊기지 않고 동작하면 MVP 완료로 본다.
```
회원가입
→ 로그인
→ 프로필 완성 여부 확인 (GET /users/me/profile)
    ├─ 미완성 → 프로필 수정 → 저장 → 분석 화면
    └─ 완성   → 분석 화면
→ 이미지 업로드
→ 분석 완료
→ 리포트 조회
→ 로그아웃
```

## 문서 갱신 규칙

테스트 방법, 실행 명령, 화면 흐름, API 흐름이 바뀌면 이 문서를 즉시 수정한다.
