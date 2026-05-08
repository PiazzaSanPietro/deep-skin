# AGENTS.md

## 프로젝트 역할

이 백엔드는 FastAPI + MySQL 기반 피부 분석 서비스 API 서버이다.

사용자가 얼굴 사진을 업로드하면 모델 추론 결과를 저장하고,  
부위별 피부 리포트와 부위별 화장품 추천 결과를 제공한다.

## 기술 스택

- FastAPI
- MySQL
- SQLAlchemy
- Alembic
- JWT Bearer Token
- Pydantic
- Pytest

## 핵심 설계 기준

- 실제 서비스 입력은 사용자 얼굴 이미지 업로드이다.
- AI-Hub JSON 업로드는 개발/테스트용 선택 기능이다.
- DB에는 세부 분석 결과를 저장한다.
- API는 사용자 화면용 부위별 리포트 형태로 반환한다.
- 추천은 부위별 문제 지표 기반으로 생성한다.
- 인증은 JWT Bearer Token 방식을 사용한다.
- DBMS는 MySQL을 사용한다.

## 작업 범위

에이전트는 다음 작업을 담당한다.

- FastAPI 프로젝트 구조 생성
- MySQL 연결 설정
- SQLAlchemy 모델 작성
- Alembic 마이그레이션 작성
- JWT 인증 구현
- 회원가입 / 로그인 API 구현
- 사용자 개인정보 API 구현
- 이미지 업로드 API 구현
- 분석 세션 생성
- 모델 추론 결과 저장
- 부위별 리포트 생성
- 부위별 추천 결과 생성
- 예외처리
- 입력값 검증
- 테스트 코드 작성

## 담당하지 않는 작업

- 모델 학습
- 이미지 크롭 학습 코드 작성
- EfficientNet / ViT 모델 튜닝
- 학습 성능 개선


## 반드시 참고할 세부 지침서

작업 전 아래 문서를 확인한다.

- `docs/agent_backend_overview.md`
- `docs/agent_db_design_fixed.md`
- `docs/agent_api_design_fixed.md`
- `docs/agent_auth_jwt.md`
- `docs/agent_image_upload.md`
- `docs/agent_recommendation_seed_fixed.md`

## 완료 조건

- MySQL 연결이 동작한다.
- 회원가입 / 로그인 API가 동작한다.
- JWT 인증이 동작한다.
- 이미지 업로드가 동작한다.
- 모델 mock 추론 결과가 저장된다.
- 부위별 리포트 API가 동작한다.
- 부위별 추천 API가 동작한다.
- 주요 예외처리가 적용된다.
- 테스트 코드가 통과한다.
