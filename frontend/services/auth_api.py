from services import api_client


def signup(email: str, password: str, name: str) -> dict:
    return api_client.post("/auth/signup", json={
        "email": email,
        "password": password,
        "name": name,
    })


def login(email: str, password: str) -> dict:
    return api_client.post("/auth/login", json={
        "email": email,
        "password": password,
    })


def logout(token: str) -> dict:
    return api_client.post("/auth/logout", token=token)


def refresh(refresh_token: str) -> dict:
    return api_client.post("/auth/refresh", json={"refresh_token": refresh_token})
