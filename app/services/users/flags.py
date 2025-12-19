from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.user import User  # поправь импорт под свой проект


async def mark_user_photos_generated(
    session: AsyncSession,
    *,
    tg_id: int,
    generation_kind: str,  # "welcome" | "subscribed"
) -> None:
    """
    Обновляет флаги генераций у пользователя:
    - generation_kind="welcome"    -> welcome_photo_generated = True
    - generation_kind="subscribed" -> subbscribed_photo_generated = True
    """
    if generation_kind not in ("welcome", "subscribed"):
        raise ValueError(f"Unknown generation_kind: {generation_kind}")

    # вариант без загрузки ORM-объекта в память
    values = {"welcome_photo_generated": True} if generation_kind == "welcome" else {"subbscribed_photo_generated": True}

    await session.execute(
        update(User)
        .where(User.tg_id == tg_id)
        .values(**values)
    )
    await session.commit()
