from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model import User  # <-- поправь импорт под свой проект
from app.schema.user import UserCreate, UserRead


async def get_or_create_user(session: AsyncSession, payload: UserCreate) -> UserRead:
    """
    Создаёт пользователя, если его ещё нет (по tg_id).
    Если есть — обновляет username/first_name/last_name (актуализируем данные).
    """
    res = await session.execute(select(User).where(User.tg_id == payload.tg_id))
    user: User | None = res.scalar_one_or_none()

    if user is None:
        user = User(
            tg_id=payload.tg_id,
            username=payload.username,
            first_name=payload.first_name,
            last_name=payload.last_name,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return UserRead.model_validate(user)

    # обновим данные, если поменялись
    updated = False
    if user.username != payload.username:
        user.username = payload.username
        updated = True
    if user.first_name != payload.first_name:
        user.first_name = payload.first_name
        updated = True
    if user.last_name != payload.last_name:
        user.last_name = payload.last_name
        updated = True

    if updated:
        await session.commit()
        await session.refresh(user)

    return UserRead.model_validate(user)
