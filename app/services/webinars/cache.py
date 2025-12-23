from __future__ import annotations
from typing import TypedDict

from app.model.webinar import Webinar
from sqlalchemy import select
from aiogram.utils.text_decorations import html_decoration
from aiogram import types

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

from redis.asyncio import Redis


KEY_WEBINARS_ALL = "webinars:all"
KEY_WEBINARS_ADMIN = "webinars:all_admin"


@dataclass
class CachedWebinar:
    id: int
    title: str
    description_small: str
    description_full: str
    date_stream: datetime

    @staticmethod
    def from_dict(d: dict) -> "CachedWebinar":
        # ожидаем ISO строку с tz
        dt = datetime.fromisoformat(d["date_stream"])
        return CachedWebinar(
            id=int(d["id"]),
            title=str(d["title"]),
            description_small=str(d.get("description_small") or ""),
            description_full=str(d.get("description_full") or ""),
            date_stream=dt,
        )


async def get_upcoming_webinars(redis: Redis) -> List[CachedWebinar]:
    raw = await redis.get(KEY_WEBINARS_ALL)
    if not raw:
        return []

    try:
        items = json.loads(raw)
        if not isinstance(items, list):
            return []
    except Exception:
        return []

    webinars = []
    for it in items:
        if isinstance(it, dict) and it.get("id") and it.get("date_stream"):
            webinars.append(CachedWebinar.from_dict(it))

    now = datetime.now(timezone.utc)
    webinars = [w for w in webinars if w.date_stream > now]
    webinars.sort(key=lambda w: w.date_stream)
    raw = await redis.get(KEY_WEBINARS_ALL)
    # print("REDIS IN HANDLER:", (raw or "")[:200])
    return webinars


def text_with_entities_to_html(text: str, entities: list[types.MessageEntity] | None) -> str:
    # вернёт HTML-строку: <b>, <i>, <a href="...">...</a> и т.п.
    return html_decoration.unparse(text, entities or [])


async def refresh_webinars_cache(session, redis: Redis) -> None:
    res = await session.execute(
        select(Webinar)
        .where(Webinar.is_active.is_(True))
        .order_by(Webinar.date_stream)
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


async def refresh_webinars_cache_admin(session, redis) -> None:
    res = await session.execute(
        select(Webinar).order_by(Webinar.date_stream.desc(), Webinar.id.desc())
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
            "is_active": bool(w.is_active),
        })

    await redis.set(KEY_WEBINARS_ADMIN, json.dumps(payload, ensure_ascii=False))


class AdminWebinarItem(TypedDict):
    id: int
    date_stream: datetime
    title: str
    is_active: bool


async def get_all_webinars_admin(redis) -> list[AdminWebinarItem]:
    raw = await redis.get(KEY_WEBINARS_ADMIN)
    if not raw:
        return []

    try:
        items = json.loads(raw)
        if not isinstance(items, list):
            return []
    except Exception:
        return []

    webinars: list[AdminWebinarItem] = []
    for it in items:
        if not (isinstance(it, dict) and it.get("id") and it.get("date_stream")):
            continue

        w = CachedWebinar.from_dict(it)

        webinars.append({
            "id": w.id,
            "date_stream": w.date_stream,
            "title": w.title,
            "is_active": bool(it.get("is_active", True)),
        })

    webinars.sort(key=lambda x: x["date_stream"], reverse=True)
    return webinars

# async def get_all_webinars_admin(redis) -> list[CachedWebinar]:
#     raw = await redis.get(KEY_WEBINARS_ADMIN)
#     if not raw:
#         return []

#     try:
#         items = json.loads(raw)
#         if not isinstance(items, list):
#             return []
#     except Exception:
#         return []

#     webinars = []
#     for it in items:
#         if isinstance(it, dict) and it.get("id") and it.get("date_stream"):
#             w = CachedWebinar.from_dict(it)
#             # добавим флаг активности (можешь расширить CachedWebinar, либо держать в dict)
#             w.is_active = bool(it.get("is_active", True))  # quick hack
#             webinars.append(w)

#     webinars.sort(key=lambda x: x.date_stream, reverse=True)
#     return webinars
