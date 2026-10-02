"""Server-to-server client for the FastAPI fraud engine. The only place the service key is used."""

import httpx
from django.conf import settings


class BankAPIError(Exception):
    def __init__(self, status: int, detail):
        super().__init__(detail)
        self.status = status
        self.detail = detail


_client = None


def _http() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(base_url=settings.FASTAPI_BASE_URL, timeout=10.0,
                               headers={"X-Service-Key": settings.SERVICE_API_KEY})
    return _client


def call(method: str, path: str, **kwargs):
    """call("GET", "/users/usr_1001") -> parsed JSON, or raises BankAPIError."""
    try:
        r = _http().request(method, "/api/v1" + path, **kwargs)
    except httpx.HTTPError as exc:
        raise BankAPIError(503, "The fraud engine is unreachable. Is it running on port 8001?") from exc
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        raise BankAPIError(r.status_code, detail)
    return r.json()
