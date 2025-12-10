from aiogram.fsm.context import FSMContext
from aiogram import Router, types, F, Bot

from app.lexicon import academy as academy_lexicon
from app.button.factory import build_inline_kb
from app.navigation import show_screen

router = Router()


@router.callback_query(F.data == "academy")
async def open_academy(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await show_screen(callback, state, bot, "academy")
    await callback.answer()
