from aiogram.client.default import DefaultBotProperties
import asyncio
import logging
import sys
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage, Redis

from app.config import settings
from app.router import router as main_router
from app.utils import set_menu


sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../app")))


logger = logging.getLogger(__name__)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(filename)s:%(lineno)d #%(levelname)-8s '
        '[%(asctime)s] - %(name)s - %(message)s'
    )

    logger.info('Starting bot')
    bot: Bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    redis = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
    storage = RedisStorage(redis=redis)
    dp: Dispatcher = Dispatcher(storage=storage)
    dp.include_router(main_router)

    await set_menu.create_set_main_menu(bot)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
