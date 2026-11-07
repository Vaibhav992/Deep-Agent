from fastapi import Request, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.auth.models import User


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency: resolve Clerk JWT → User row.

    If the user doesn't exist in our DB yet (first login),
    we create a minimal record. Clerk webhook (user.created)
    fills in the rest asynchronously.
    """
    clerk_id: str | None = getattr(request.state, "clerk_user_id", None)
    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    result = await db.execute(
        select(User).where(User.clerk_id == clerk_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            id=clerk_id,
            clerk_id=clerk_id,
            email=f"{clerk_id}@pending.clerk",
            display_name="New User",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account deactivated",
        )

    return user
