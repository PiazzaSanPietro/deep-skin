# JWT Auth Guide

현재 인증 구현은 `app/core/security.py`, `app/core/dependencies.py`, `app/services/auth_service.py` 기준입니다.

## 방식

- 인증 헤더: `Authorization: Bearer <access_token>`
- FastAPI dependency: `Depends(get_current_user)`
- 토큰 라이브러리: `python-jose`
- 비밀번호 해시: `bcrypt`
- refresh token DB 저장: 원문 저장이 아니라 SHA-256 hash 저장

## JWT payload

Access token과 refresh token 모두 아래 최소 payload를 사용합니다.

```json
{
  "sub": "1",
  "type": "access",
  "exp": 1715150000
}
```

| Field | 설명 |
|---|---|
| `sub` | 사용자 ID 문자열 |
| `type` | `access` 또는 `refresh` |
| `exp` | 만료 시각 |

개인정보, 프로필 정보, 피부 정보는 JWT에 넣지 않고 DB의 `user_profiles`에서 관리합니다.

## Access token 검증

`get_current_user()` 흐름:

1. `HTTPBearer(auto_error=False)`로 Bearer token 추출
2. `decode_token()` 호출
3. `payload.type == "access"` 확인
4. `payload.sub`를 사용자 ID로 변환
5. `users`에서 사용자 조회
6. 사용자가 없거나 비활성 상태면 에러

## Refresh token 흐름

로그인 시:

1. access token 발급
2. refresh token 발급
3. refresh token 원문을 SHA-256으로 hash
4. `refresh_tokens.token_hash`에 저장
5. `expires_at`은 `REFRESH_TOKEN_EXPIRE_DAYS` 기준

재발급 시 `POST /auth/refresh`:

1. refresh token decode
2. `payload.type == "refresh"` 확인
3. token hash로 DB row 조회
4. `revoked_at`과 `expires_at` 확인
5. 새 access token만 반환

현재 구현은 refresh token rotation을 하지 않습니다. refresh 호출 시 새 refresh token은 발급하지 않습니다.

## Logout

`POST /auth/logout`은 인증 필요 API입니다. 현재 사용자 ID의 아직 revoke되지 않은 refresh token 전체에 `revoked_at`을 기록합니다.

프론트엔드는 로그아웃 성공 후 로컬에 저장한 access/refresh token도 제거해야 합니다.

## 관련 환경 변수

```env
JWT_SECRET_KEY=change-me-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=14
```

운영 환경에서는 `JWT_SECRET_KEY`를 반드시 안전한 값으로 변경해야 합니다.