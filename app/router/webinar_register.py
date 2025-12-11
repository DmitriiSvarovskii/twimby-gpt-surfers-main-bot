from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
)

from app.navigation import show_screen


router = Router()


@router.callback_query(F.data == "webinar_main")
async def open_webinar_main(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id="webinar",
    )
    await callback.answer()


@router.callback_query(F.data == "webinar_18")
async def open_webinar_18(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id="webinar_18",
    )
    await callback.answer()


@router.callback_query(F.data == "webinar_21")
async def open_webinar_21(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id="webinar_21",
    )
    await callback.answer()


@router.callback_query(F.data == "webinar_back")
async def webinar_back(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    # экран, с которого зашли в вебинары
    prev_screen = data.get("webinar_prev_screen")

    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id=prev_screen,
        as_new_message=False,
        push_history=False,
    )

    await callback.answer()
