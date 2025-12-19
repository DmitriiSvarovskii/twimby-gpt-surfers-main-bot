from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

from redis.asyncio import Redis


KEY_WEBINARS_ALL = "webinars:all"


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
    return webinars
