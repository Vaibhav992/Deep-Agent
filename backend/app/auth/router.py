from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.auth.webhook import router as webhook_router

router = APIRouter()
router.include_router(webhook_router)


@router.get("/auth/me", tags=["auth"])
async def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "tier": user.tier,
    }
