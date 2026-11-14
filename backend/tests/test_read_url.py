import httpx

import app.tools.read_url as read_url_module
from app.security import url_policy


def _patch_network(monkeypatch, handler):
    real_client = httpx.AsyncClient
    monkeypatch.setattr(read_url_module.httpx, "AsyncClient",
                        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))

    async def fake_check(url: str) -> str:
        host = httpx.URL(url).host
        if host in ("127.0.0.1", "localhost"):
            raise url_policy.UrlPolicyError(f"Host '{host}' resolves to a non-public address.")
        return url

    monkeypatch.setattr(read_url_module, "check_url", fake_check)


async def test_redirect_to_internal_host_is_blocked(monkeypatch):
    requested = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://127.0.0.1:8000/health"})

    _patch_network(monkeypatch, handler)
    result = await read_url_module.read_url.ainvoke({"url": "https://public.example/start"})
    assert result.startswith("[Blocked]")
    assert requested == ["https://public.example/start"], "the internal hop must never be requested"


async def test_public_redirect_is_followed(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/start":
            return httpx.Response(301, headers={"location": "/final"})
        return httpx.Response(200, headers={"content-type": "text/html"},
                              text="<html><body><article><p>Hello from the final page.</p></article></body></html>")

    _patch_network(monkeypatch, handler)
    result = await read_url_module.read_url.ainvoke({"url": "https://public.example/start"})
    assert "Hello from the final page." in result
