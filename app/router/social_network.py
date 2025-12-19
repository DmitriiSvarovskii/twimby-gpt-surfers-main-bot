from aiogram.fsm.context import FSMContext
from aiogram import Router, types, F, Bot

from app.navigation import show_screen

router = Router()


@router.callback_query(F.data == "social_network")
async def open_social_network(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await show_screen(callback, state, bot, "social_network")
    await callback.answer()
