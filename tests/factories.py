from httpx import AsyncClient


async def register_and_login(client: AsyncClient) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "StrongPass123!"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "StrongPass123!"},
    )
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def valid_book_payload(**overrides) -> dict:
    base = {
        "title": "The Pragmatic Programmer",
        "author": "David Thomas",
        "genre": "science",
        "year": 2019,
    }
    return {**base, **overrides}