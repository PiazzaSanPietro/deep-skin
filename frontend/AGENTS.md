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
GET  /analysis/sessions/{session_id}/metrics   ← Phase 2-2 추가
GET  /analysis/metrics/trends                  ← Phase 2-4 추가
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

## Phase 2-4 완료 (2026-05-12) — 추이 그래프

- `services/analysis_api.py` — `get_metric_trends()` 추가
- `services/api_client.py` — `get()` 함수에 `params` 키워드 인수 추가
- `views/report.py` — "피부 측정 추이" 섹션 + `_render_trends_section()` / `_fetch_all_trends()` / `_render_trend_chart()` 추가
- `_TREND_METRICS`: 기본 8개 지표 (이마 수분, 볼 모공, 눈가 Ra, 탄력 R2)
- "추이 그래프 보기" 토글: on-demand 로드, `st.session_state` 캐시
- 그래프: `st.line_chart(x=날짜, y=값)` / 1개: 현재 값 / 0개: 안내 문구 / API 실패: soft fail

## Phase 3-E 완료 (2026-05-12) — 실제 얼굴 이미지 YOLO bbox E2E 검증

- 940×1410 정면 얼굴 이미지 (session_id=104) 기준 전체 흐름 검증
- YOLO 3개 검출 (forehead/lips/chin), 5개 full_image_fallback — 혼합 저장 정상
- 실제 추론값: `forehead_moisture=50.64`, grade 최대 4(severe) 포함
- report `overall_status=집중 관리 필요`, trends API 2개 세션 추이 정상 반영
- API (report/metrics/trends/latest), DB (80 metric values), bbox 저장 모두 정상

## Phase 3-D 완료 (2026-05-12) — 실환경 E2E 테스트

- 백엔드 `AI_INFERENCE_MODE=multivalue` + multivalue AI 서버(port 9001) 연결 상태에서 전체 흐름 검증
- 프론트 이미지 업로드 → multivalue 추론 → DB 저장 → report/metrics/trends/recommendations API 모두 정상 응답 확인
- trends 전문가 모드 selectbox API 파라미터: `metric_name`은 DB `skin_metric_values.metric_name` 기준
  (예: forehead moisture → `metric_name=moisture`, NOT `forehead_moisture`)
- `_TREND_METRIC_OPTIONS`의 metric_name 키가 DB 값과 일치하는지 확인 완료

## Phase 3-B 완료 (2026-05-12) — 전문가 모드 추이 지표 선택 UI

- `views/report.py` — `_render_expert_trend_selector()` 추가
  - 부위 → 지표 그룹 → 세부 지표 캐스케이딩 selectbox
  - 부위 변경 시 하위 selectbox session_state 키 초기화 (index 0 자동 복귀)
  - "추이 조회" 버튼 → `analysis_api.get_metric_trends()` 호출 → `_render_trend_chart()` 재사용
  - 결과 `st.session_state[f"expert_trend_chart_{session_id}"]` 캐시
- `views/report.py` — `_metric_name_display(group, name)` 헬퍼 추가
- `views/report.py` — `_PART_DISPLAY` / `_GROUP_DISPLAY` / `_TREND_METRIC_OPTIONS` 상수 추가
  - `_TREND_METRIC_OPTIONS`: 7개 부위 × 각 부위별 그룹 × metric_name 목록
- `views/report.py` — `_render_trends_section(expert_mode=False)` 시그니처 확장
- `styles/report.css` — `.ds-trends-expert-header` 스타일 추가
- 백엔드 변경 없음 (기존 `GET /analysis/metrics/trends` 재사용)

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

## Phase 3-F 완료 (2026-05-12) — UI Polish

백엔드/API/DB 변경 없음. 화면 스타일 및 UX만 개선.

### 변경 파일

| 파일 | 변경 내용 |
|---|---|
| `styles/report.css` | 섹션 서브타이틀(`.ds-report-section-sub`), 추천 출처 노트(`.ds-rec-source-note`), 전문가 그룹 블록(`.ds-metrics-group-block/label`), 추이 카드 래퍼(`.ds-trend-charts-container`), empty state / single-value 클래스 추가 |
| `styles/sidebar.css` | 신규 파일. `theme.py` 사이드바 CSS 위에 추가 적용. 활성 아이템 gradient+inset shadow, section label, info card 등 polish |
| `components/layout.py` | `render_sidebar()` 진입 시 `load_css("sidebar.css")` 호출 추가 |
| `views/report.py` | 전문가 모드 토글 → 상세 분석 헤더와 같은 줄 배치; 추천 섹션 서브타이틀 추가; 추천 카드 subtitle 텍스트 rule-based 표현으로 정정; 추천 출처 안내 노트 추가; `_render_metrics_section()` — 전문가 모드 metric_group별 그룹 표시; `_render_trends_section()` — `ds-trend-charts-container` 카드 래퍼 + 개선된 empty state; `_render_trend_chart()` — single-value / no-data → CSS 클래스 사용; `_render_expert_trend_selector()` — 3-column selectbox 레이아웃 |

### 주요 UX 변경

- 전문가 모드 토글이 "상세 분석" 헤더 오른쪽에 인라인 배치됨
- 추천 섹션이 "AI가 추천해요"가 아닌 rule-based 언어로 표현됨
- 전문가 모드에서 80+ metric을 group label로 묶어 표시
- 추이 차트가 카드 래퍼 안에 표시됨; 데이터 없을 때 아이콘+텍스트 empty state
- 부위/그룹/세부지표 selectbox가 3-column 한 줄로 배치됨

## 문서 갱신 원칙

코드가 수정되면 관련 문서를 즉시 수정한다.

예시:

- API 호출 방식 수정 → docs/frontend_api_flow.md 수정
- 화면 구조 수정 → docs/frontend_ui_guide.md 수정
- 폴더 구조 수정 → docs/frontend_structure.md 수정
- 인증 흐름 수정 → docs/frontend_state_auth.md 수정
- 리포트 화면 수정 → docs/frontend_report_design.md 수정
- 테스트 방법 수정 → docs/frontend_validation_checklist.md 수정