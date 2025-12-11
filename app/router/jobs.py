
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.navigation import show_screen

router = Router()


@router.callback_query(F.data == "jobs")
async def open_jobs(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Экран "Вакансии":
    - рендерим через общий навигатор show_screen
    - он сам подставит фото + текст + кнопки
    """
    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id="jobs",
    )
    await callback.answer()
