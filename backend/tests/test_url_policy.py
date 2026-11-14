import pytest

from app.security.url_policy import UrlPolicyError, check_url


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8000/health",
    "http://localhost:3000",
    "http://app.localhost/",
    "http://169.254.169.254/latest/meta-data",
    "http://10.0.0.5/",
    "http://192.168.1.1/admin",
    "http://[::1]/",
    "http://metadata.google.internal/",
    "file:///etc/passwd",
    "view-source:https://example.com",
    "javascript:alert(1)",
    "chrome://settings",
    "https:///no-host",
])
async def test_blocks_non_public_and_non_http(url):
    with pytest.raises(UrlPolicyError):
        await check_url(url)


async def test_allows_public_https():
    assert await check_url("https://example.com/path?q=1") == "https://example.com/path?q=1"


def _fake_resolver(monkeypatch, addresses):
    import app.security.url_policy as policy

    class FakeLoop:
        async def getaddrinfo(self, host, port, type=None):
            return [(None, None, None, None, (a, 0)) for a in addresses]

    monkeypatch.setattr(policy.asyncio, "get_running_loop", lambda: FakeLoop())


async def test_allows_public_site_behind_nat64(monkeypatch):
    # Regression: DNS64 networks return 64:ff9b::/96 wrappers for public IPv4 (www.bbc.com was blocked).
    _fake_resolver(monkeypatch, ["199.232.104.81", "64:ff9b::c7e8:6851"])
    assert await check_url("https://www.bbc.com/news") == "https://www.bbc.com/news"


@pytest.mark.parametrize("wrapped", ["64:ff9b::a00:5", "64:ff9b::7f00:1", "::ffff:127.0.0.1", "::ffff:169.254.169.254"])
async def test_blocks_private_ipv4_hidden_in_ipv6_wrappers(monkeypatch, wrapped):
    _fake_resolver(monkeypatch, [wrapped])
    with pytest.raises(UrlPolicyError, match="non-public"):
        await check_url("https://sneaky.example/")


async def test_rejects_dns_name_resolving_to_loopback(monkeypatch):
    import app.security.url_policy as policy

    class FakeLoop:
        async def getaddrinfo(self, host, port, type=None):
            return [(None, None, None, None, ("127.0.0.1", 0))]

    monkeypatch.setattr(policy.asyncio, "get_running_loop", lambda: FakeLoop())
    with pytest.raises(UrlPolicyError, match="non-public"):
        await check_url("https://rebind.example/")
