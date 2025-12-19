# app/utils/telegram/subscription.py

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from app.config import settings


SUBSCRIPTION_CHANNEL_ID = settings.TELEGRAM_CHANEL


async def is_user_subscribed(
    bot: Bot,
    user_id: int,
    channel_id: int = SUBSCRIPTION_CHANNEL_ID,
) -> bool:
    """
    Проверяет, подписан ли пользователь на Telegram-канал.

    Возвращает:
    - True  — если подписан (member / admin / creator / restricted)
    - False — если не подписан или произошла ошибка
    """
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
    except TelegramBadRequest:
        return False
    except Exception:
        return False

    return member.status in ("member", "administrator", "creator", "restricted")
