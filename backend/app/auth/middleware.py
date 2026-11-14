import asyncio
import base64

import jwt
from jwt import PyJWKClient
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

settings = get_settings()

_jwks_client: PyJWKClient | None = None


def _resolve_jwks_url() -> str:
    if settings.CLERK_JWKS_URL:
        return settings.CLERK_JWKS_URL
    pk = settings.CLERK_PUBLISHABLE_KEY
    encoded = pk.split("_")[-1]
    domain = base64.b64decode(encoded + "==").decode().rstrip("$")
    return f"https://{domain}/.well-known/jwks.json"


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(_resolve_jwks_url(), cache_keys=True)
    return _jwks_client


def verify_clerk_token(token: str) -> dict:
    """Verify a Clerk JWT and return its claims.

    Clerk JWTs are signed with RS256. We fetch the public key from
    Clerk's JWKS endpoint (cached after first call).
    """
    client = _get_jwks_client()
    signing_key = client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        options={"verify_aud": False},
    )


class ClerkAuthMiddleware(BaseHTTPMiddleware):
    """Middleware that verifies Clerk JWTs on protected routes.

    Public routes (health, webhooks, docs) skip auth.
    """
    PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/models"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        # Exceptions raised here bypass FastAPI's handlers (they'd surface as 500), so respond directly.
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse({"detail": "Missing or invalid Authorization header"},
                                status_code=status.HTTP_401_UNAUTHORIZED)

        token = auth_header.removeprefix("Bearer ").strip()
        try:
            # JWKS lookup can hit the network on a cache miss; keep it off the event loop.
            claims = await asyncio.to_thread(verify_clerk_token, token)
        except jwt.exceptions.PyJWKClientConnectionError:
            return JSONResponse({"detail": "Authentication service unavailable"},
                                status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        except jwt.InvalidTokenError:
            return JSONResponse({"detail": "Invalid or expired token"}, status_code=status.HTTP_401_UNAUTHORIZED)

        request.state.clerk_user_id = claims.get("sub")
        request.state.clerk_claims = claims
        return await call_next(request)
