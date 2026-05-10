from services import api_client


def get_recommendations(token: str, session_id: int) -> dict:
    return api_client.get(f"/recommendations/sessions/{session_id}", token=token)
