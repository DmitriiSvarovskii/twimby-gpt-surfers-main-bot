from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.user import User


async def get_user_by_tg_id(session: AsyncSession, tg_id: int) -> User | None:
    res = await session.execute(select(User).where(User.tg_id == tg_id))
    return res.scalar_one_or_none()
