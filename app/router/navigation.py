# app/router/navigation.py

from aiogram import Router, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram import F

from app.navigation import show_screen

router = Router()


@router.callback_query(F.data == "back")
async def go_back(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    history = data.get("history", [])

    if not history:
        # если истории нет — идём в start без пуша в историю
        await show_screen(callback, state, bot, "start", push_history=False)
        await callback.answer()
        return

    prev_screen = history.pop()
    await state.update_data(history=history)

    await show_screen(callback, state, bot, prev_screen, push_history=False)
    await callback.answer()
