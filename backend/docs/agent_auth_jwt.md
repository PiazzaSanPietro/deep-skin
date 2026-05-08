**역할:** 인증 구현 지침서

JWT 인증 방식, 토큰 구조, 인증 API 처리 기준을 정리한다.

---

# Agent JWT Auth Guide

## 인증 방식

FastAPI에서는 JWT Bearer Token 방식을 사용한다.

프론트엔드는 로그인 후 받은 `access_token`을 요청 헤더에 담아 보낸다.

```http
Authorization: Bearer <access_token>
```

---

## FastAPI 구현 기준

- `OAuth2PasswordBearer` 사용
- `Depends(get_current_user)` 사용
- `python-jose` 또는 `PyJWT` 사용
- 비밀번호는 `bcrypt` 해시로 저장
- 개인정보는 JWT payload에 넣지 않음
- 인증이 필요한 API는 반드시 현재 로그인 사용자를 확인함

---

## JWT Payload 권장 구조

JWT에는 최소한의 사용자 식별 정보만 넣는다.

```json
{
  "sub": "1",
  "type": "access",
  "exp": 1715150000
}
```

### 필드 설명

| 필드 | 설명 |
|---|---|
| `sub` | 사용자 ID |
| `type` | 토큰 유형 |
| `exp` | 토큰 만료 시간 |

---

## JWT Payload에 넣지 말 것

나이, 성별, 피부 타입 같은 개인정보는 JWT에 넣지 않는다.

```json
{
  "age": 28,
  "gender": "F",
  "skin_type": 3
}
```

위 정보는 DB의 `user_profiles` 테이블에서 관리한다.

---

## 인증 필요한 API 처리

모든 인증 필요 API는 다음 의존성을 사용한다.

```python
current_user = Depends(get_current_user)
```

예시:

```python
@router.get("/users/me")
def read_my_profile(current_user: User = Depends(get_current_user)):
    return current_user
```

---

## 권한 검증

분석 세션 조회, 이미지 업로드, 추천 조회 시에는 반드시 세션 소유자를 확인한다.

```python
if session.user_id != current_user.id:
    raise HTTPException(
        status_code=403,
        detail={
            "error_code": "SESSION_ACCESS_DENIED",
            "message": "본인의 분석 세션만 접근할 수 있습니다."
        }
    )
```

검증 기준:

```text
session.user_id == current_user.id
```

## Refresh Token 관리

로그인 응답에 `refresh_token`을 포함할 경우 DB에 해시값으로 저장한다.

원문 refresh token은 DB에 저장하지 않는다.

```text
refresh_tokens.token_hash
```

---

## Refresh Token 저장 기준

로그인 성공 시 다음 정보를 저장한다.

| 컬럼 | 설명 |
|---|---|
| `user_id` | 토큰을 발급받은 사용자 ID |
| `token_hash` | refresh token 원문을 해시 처리한 값 |
| `expires_at` | refresh token 만료 시간 |
| `revoked_at` | 로그아웃 또는 폐기 시간 |
| `created_at` | 발급 시간 |

---

## Refresh Token 사용 흐름

```text
1. 사용자가 로그인한다.
2. 서버가 access_token과 refresh_token을 발급한다.
3. access_token은 짧은 만료 시간을 가진다.
4. refresh_token은 더 긴 만료 시간을 가진다.
5. refresh_token 원문은 클라이언트에만 전달한다.
6. 서버 DB에는 refresh_token 해시값만 저장한다.
7. access_token이 만료되면 refresh_token으로 재발급을 요청한다.
8. 서버는 refresh_token 해시값과 만료 여부를 검증한다.
9. 검증 성공 시 새로운 access_token을 발급한다.
```

---

## 로그아웃 처리

로그아웃 시에는 해당 refresh token을 폐기 처리한다.

```text
revoked_at = 현재 시간
```

로그아웃 이후 같은 refresh token으로 access token을 재발급할 수 없어야 한다.

---

## Refresh Token 검증 기준

Refresh Token 재발급 요청 시 다음 항목을 검증한다.

- DB에 token_hash가 존재하는지
- 만료 시간이 지나지 않았는지
- revoked_at이 NULL인지
- 해당 사용자가 활성 상태인지

---

## Refresh Token 관련 예외

| 상황 | status code | error_code |
|---|---:|---|
| refresh token 없음 | 401 | REFRESH_TOKEN_REQUIRED |
| 유효하지 않은 refresh token | 401 | INVALID_REFRESH_TOKEN |
| 만료된 refresh token | 401 | REFRESH_TOKEN_EXPIRED |
| 폐기된 refresh token | 401 | REFRESH_TOKEN_REVOKED |

---

## Access Token과 Refresh Token 만료 기준

초기 개발 기준은 다음처럼 설정한다.

```text
Access Token 만료 시간: 60분
Refresh Token 만료 시간: 14일
```

`.env` 예시:

```env
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=14
```

