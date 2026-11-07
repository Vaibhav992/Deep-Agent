import httpx
import jwt
from jwt import PyJWKClient
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

settings = get_settings()

_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(settings.CLERK_JWKS_URL, cache_keys=True)
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
    PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/webhooks/clerk"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid Authorization header",
            )

        token = auth_header.removeprefix("Bearer ").strip()
        try:
            claims = verify_clerk_token(token)
            request.state.clerk_user_id = claims.get("sub")
            request.state.clerk_claims = claims
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {e}",
            )

        return await call_next(request)
