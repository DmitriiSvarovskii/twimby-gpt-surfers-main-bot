from __future__ import annotations
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.webinar import Webinar  # твоя ORM модель
from app.schema.webinar import WebinarDTO, WebinarListItemDTO
from app.services.webinars.cache import (
    cache_get_active, cache_set_active,
    cache_get_webinar, cache_set_webinar,
)


async def get_active_webinars(session: AsyncSession, redis) -> list[WebinarListItemDTO]:
    cached = await cache_get_active(redis)
    if cached is not None:
        return cached

    # Например: только активные и будущие
    now = datetime.utcnow()
    q = (
        select(Webinar)
        .where(Webinar.is_active.is_(True))
        .where(Webinar.date_stream >= now - timedelta(hours=1))
        .order_by(Webinar.date_stream.asc())
        .limit(50)
    )
    res = await session.execute(q)
    rows = res.scalars().all()

    items = [
        WebinarListItemDTO(
            id=w.id,
            title=w.title,
            description_small=w.description_small,
            date_stream=w.date_stream,
            is_free=w.is_free,
            price=w.price,
        )
        for w in rows
    ]

    await cache_set_active(redis, items)
    return items


async def get_webinar_by_id(session: AsyncSession, redis, webinar_id: int) -> WebinarDTO | None:
    cached = await cache_get_webinar(redis, webinar_id)
    if cached is not None:
        return cached

    res = await session.execute(select(Webinar).where(Webinar.id == webinar_id))
    w = res.scalar_one_or_none()
    if w is None:
        return None

    dto = WebinarDTO(
        id=w.id,
        title=w.title,
        description_small=w.description_small,
        description_full=w.description_full,
        date_stream=w.date_stream,
        is_active=w.is_active,
        is_free=w.is_free,
        price=w.price,
    )
    await cache_set_webinar(redis, dto)
    return dto
