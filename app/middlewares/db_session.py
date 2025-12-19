from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker


class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, session_maker: sessionmaker):
        super().__init__()
        self._session_maker = session_maker

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with self._session_maker() as session:
            data["session"] = session
            return await handler(event, data)
