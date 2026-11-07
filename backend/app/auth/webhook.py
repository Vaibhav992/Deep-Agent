import hashlib
import hmac
import json

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.database import get_db
from app.auth.models import User

router = APIRouter(tags=["webhooks"])
settings = get_settings()


def _verify_svix_signature(payload: bytes, headers: dict[str, str]) -> bool:
    """Verify Clerk webhook signature (Svix).

    Clerk uses Svix for webhook delivery. We verify the signature
    to ensure the payload came from Clerk, not an attacker.
    """
    secret = settings.CLERK_WEBHOOK_SECRET
    if not secret:
        return False

    svix_id = headers.get("svix-id", "")
    svix_timestamp = headers.get("svix-timestamp", "")
    svix_signature = headers.get("svix-signature", "")

    if not all([svix_id, svix_timestamp, svix_signature]):
        return False

    # Svix signs: "{msg_id}.{timestamp}.{body}"
    to_sign = f"{svix_id}.{svix_timestamp}.{payload.decode()}"

    # Secret is base64-encoded with "whsec_" prefix
    import base64
    secret_bytes = base64.b64decode(secret.removeprefix("whsec_"))
    expected = hmac.new(secret_bytes, to_sign.encode(), hashlib.sha256).digest()
    expected_b64 = base64.b64encode(expected).decode()

    # svix-signature can have multiple sigs separated by space
    for sig in svix_signature.split(" "):
        sig_value = sig.removeprefix("v1,")
        if hmac.compare_digest(sig_value, expected_b64):
            return True
    return False


@router.post("/webhooks/clerk")
async def clerk_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Clerk webhook events (user.created, user.updated, user.deleted)."""
    payload = await request.body()
    headers = dict(request.headers)

    if not _verify_svix_signature(payload, headers):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event = json.loads(payload)
    event_type = event.get("type", "")
    data = event.get("data", {})

    if event_type == "user.created":
        await _handle_user_created(db, data)
    elif event_type == "user.updated":
        await _handle_user_updated(db, data)
    elif event_type == "user.deleted":
        await _handle_user_deleted(db, data)

    return {"status": "ok"}


async def _handle_user_created(db: AsyncSession, data: dict):
    clerk_id = data["id"]
    email = _extract_primary_email(data)

    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    existing = result.scalar_one_or_none()

    if existing:
        existing.email = email
        existing.display_name = _build_display_name(data)
        existing.avatar_url = data.get("image_url")
    else:
        user = User(
            id=clerk_id,
            clerk_id=clerk_id,
            email=email,
            display_name=_build_display_name(data),
            avatar_url=data.get("image_url"),
        )
        db.add(user)

    await db.commit()


async def _handle_user_updated(db: AsyncSession, data: dict):
    clerk_id = data["id"]
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    if not user:
        return

    user.email = _extract_primary_email(data)
    user.display_name = _build_display_name(data)
    user.avatar_url = data.get("image_url")
    await db.commit()


async def _handle_user_deleted(db: AsyncSession, data: dict):
    clerk_id = data.get("id")
    if not clerk_id:
        return
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    if user:
        user.is_active = False
        await db.commit()


def _extract_primary_email(data: dict) -> str:
    for addr in data.get("email_addresses", []):
        if addr.get("id") == data.get("primary_email_address_id"):
            return addr["email_address"]
    return f"{data['id']}@clerk.user"


def _build_display_name(data: dict) -> str:
    first = data.get("first_name", "")
    last = data.get("last_name", "")
    name = f"{first} {last}".strip()
    return name or data.get("username", "User")
