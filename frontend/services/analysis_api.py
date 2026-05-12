from services import api_client


def create_session(token: str, session_name: str) -> dict:
    return api_client.post("/analysis/sessions", json={"session_name": session_name}, token=token)


def upload_image(
    token: str,
    session_id: int,
    file_bytes: bytes,
    filename: str,
) -> dict:
    files = {"file": (filename, file_bytes, "image/jpeg")}
    return api_client.post_file(
        f"/analysis/sessions/{session_id}/images",
        files=files,
        token=token,
    )


def get_report(token: str, session_id: int) -> dict:
    return api_client.get(f"/analysis/sessions/{session_id}/report", token=token)


def get_latest_report(token: str) -> dict:
    return api_client.get("/analysis/reports/latest", token=token)
