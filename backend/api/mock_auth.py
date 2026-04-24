from datetime import datetime, timedelta, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_db
from models.user import User
from models.refresh_token import RefreshToken
from core.security import create_access_token, create_refresh_token
from core.config import settings

router = APIRouter()

@router.post("/login")
async def mock_login(db: AsyncSession = Depends(get_db)):
    """
    Temporary bypass endpoint for testing.
    Creates or fetches a mock 'Pro' user and issues an RS256 token pair.
    """
    if not settings.DEBUG:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    email = "test@example.com"
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        # Create a new tenant and user
        tenant_id = uuid.uuid4()
        user = User(
            email=email,
            display_name="Test User",
            tenant_id=tenant_id,
            role="owner",
            tier="pro",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Issue tokens
    access_token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role
    )
    raw_rt, hashed_rt = create_refresh_token()

    rt_record = RefreshToken(
        user_id=user.id,
        token_hash=hashed_rt,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(rt_record)
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": raw_rt,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role,
            "tier": user.tier,
            "tenant_id": str(user.tenant_id)
        }
    }
