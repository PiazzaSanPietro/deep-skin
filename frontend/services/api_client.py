import os

import requests
from dotenv import load_dotenv

load_dotenv()

_BASE_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")


def _headers(token: str | None = None) -> dict:
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _parse_error(response: requests.Response) -> dict:
    try:
        body = response.json()
        detail = body.get("detail") or body.get("message") or body.get("error") or str(body)
    except Exception:
        detail = response.text or "알 수 없는 오류"
    return {"_status": response.status_code, "_error": detail}


def _connection_error(e: Exception) -> dict:
    if isinstance(e, requests.exceptions.ConnectionError):
        return {"_status": 0, "_error": "백엔드 서버에 연결할 수 없습니다."}
    if isinstance(e, requests.exceptions.Timeout):
        return {"_status": 0, "_error": "서버 응답 시간이 초과되었습니다."}
    return {"_status": -1, "_error": str(e)}


def get(endpoint: str, token: str | None = None) -> dict:
    try:
        r = requests.get(f"{_BASE_URL}{endpoint}", headers=_headers(token), timeout=30)
        if not r.ok:
            return _parse_error(r)
        return r.json()
    except Exception as e:
        return _connection_error(e)


def post(endpoint: str, json: dict | None = None, token: str | None = None) -> dict:
    try:
        r = requests.post(f"{_BASE_URL}{endpoint}", json=json, headers=_headers(token), timeout=30)
        if not r.ok:
            return _parse_error(r)
        return r.json()
    except Exception as e:
        return _connection_error(e)


def put(endpoint: str, json: dict | None = None, token: str | None = None) -> dict:
    try:
        r = requests.put(f"{_BASE_URL}{endpoint}", json=json, headers=_headers(token), timeout=30)
        if not r.ok:
            return _parse_error(r)
        return r.json()
    except Exception as e:
        return _connection_error(e)


def post_file(
    endpoint: str,
    files: dict,
    data: dict | None = None,
    token: str | None = None,
) -> dict:
    h = {}
    if token:
        h["Authorization"] = f"Bearer {token}"
    try:
        r = requests.post(
            f"{_BASE_URL}{endpoint}",
            files=files,
            data=data or {},
            headers=h,
            timeout=60,
        )
        if not r.ok:
            return _parse_error(r)
        return r.json()
    except Exception as e:
        return _connection_error(e)


def is_error(res: dict) -> bool:
    return "_error" in res


def get_error_message(res: dict) -> str:
    status = res.get("_status", -1)
    msg = res.get("_error", "알 수 없는 오류")
    if status == 401:
        return "로그인이 만료되었습니다. 다시 로그인해주세요."
    if status == 0:
        return "백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요."
    return str(msg)
