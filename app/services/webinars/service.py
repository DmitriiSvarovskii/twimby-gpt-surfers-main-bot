from __future__ import annotations

import json
from datetime import datetime, timezone

from aiogram import types
from aiogram.utils.text_decorations import html_decoration
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.model.webinar import Webinar
from app.services.webinars.cache import KEY_WEBINARS_ALL
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.webinar import Webinar
from app.schema.webinar import WebinarDTO, WebinarListItemDTO
# from app.services.webinars.cache import (
#     cache_get_active, cache_set_active,
#     cache_get_webinar, cache_set_webinar,
# )


# async def get_active_webinars(session: AsyncSession, redis) -> list[WebinarListItemDTO]:
#     cached = await cache_get_active(redis)
#     if cached is not None:
#         return cached

#     # Например: только активные и будущие
#     now = datetime.utcnow()
#     q = (
#         select(Webinar)
#         .where(Webinar.is_active.is_(True))
#         .where(Webinar.date_stream >= now - timedelta(hours=1))
#         .order_by(Webinar.date_stream.asc())
#         .limit(50)
#     )
#     res = await session.execute(q)
#     rows = res.scalars().all()

#     items = [
#         WebinarListItemDTO(
#             id=w.id,
#             title=w.title,
#             description_small=w.description_small,
#             date_stream=w.date_stream,
#             is_free=w.is_free,
#             price=w.price,
#         )
#         for w in rows
#     ]

#     await cache_set_active(redis, items)
#     return items


# async def get_webinar_by_id(session: AsyncSession, redis, webinar_id: int) -> WebinarDTO | None:
#     cached = await cache_get_webinar(redis, webinar_id)
#     if cached is not None:
#         return cached

#     res = await session.execute(select(Webinar).where(Webinar.id == webinar_id))
#     w = res.scalar_one_or_none()
#     if w is None:
#         return None

#     dto = WebinarDTO(
#         id=w.id,
#         title=w.title,
#         description_small=w.description_small,
#         description_full=w.description_full,
#         date_stream=w.date_stream,
#         is_active=w.is_active,
#         is_free=w.is_free,
#         price=w.price,
#     )
#     await cache_set_webinar(redis, dto)
#     return dto


def text_with_entities_to_html(text: str, entities: list[types.MessageEntity] | None) -> str:
    return html_decoration.unparse(text or "", entities or [])


async def get_webinar_by_id(session: AsyncSession, wid: int) -> Webinar | None:
    res = await session.execute(select(Webinar).where(Webinar.id == wid))
    return res.scalar_one_or_none()


def render_webinar_full(w: Webinar) -> str:
    dt = w.date_stream
    # показываем дату красиво; если tz нет — считаем UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    dt_str = dt.astimezone(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")

    status = "🟢 Активен" if w.is_active else "🔴 В архиве"
    return (
        f"<b>{w.title}</b>\n"
        f"{status}\n"
        f"🗓 <b>{dt_str}</b>\n\n"
        f"<b>Короткое описание:</b>\n{w.description_small}\n\n"
        f"<b>Полное описание:</b>\n{w.description_full}"
    )


async def refresh_webinars_cache(session: AsyncSession, redis: Redis) -> None:
    res = await session.execute(
        select(Webinar).where(Webinar.is_active.is_(True)).order_by(Webinar.date_stream)
    )
    rows = res.scalars().all()

    payload = []
    for w in rows:
        dt = w.date_stream
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        payload.append({
            "id": w.id,
            "title": w.title,
            "description_small": w.description_small,
            "description_full": w.description_full,
            "date_stream": dt.isoformat(),
        })

    await redis.set(KEY_WEBINARS_ALL, json.dumps(payload, ensure_ascii=False))
