from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.lexicon import webinar as webinar_lexicon

router = Router()

WEBINAR_PAYMENT_URL = "https://tally.so/r/wo8jo5"   # поставь свою ссылку, это пример


def kb_webinar_announce():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Зарегистрироваться", callback_data="webinar_register")],
            [InlineKeyboardButton(text="Назад", callback_data="back")],
        ]
    )


def kb_webinar_register():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Оплатить вебинар",
                    url=WEBINAR_PAYMENT_URL,
                )
            ],
            [InlineKeyboardButton(text="Назад", callback_data="back")],
        ]
    )


@router.callback_query(F.data == "webinar_announce")
async def open_webinar_announce(callback: types.CallbackQuery, state: FSMContext):
    """
    Страница "Анонс вебинара"
    """
    data = await state.get_data()
    history = data.get("history", [])
    current = data.get("current_screen")

    if current and current != "webinar_announce":
        history.append(current)

    await state.update_data(
        history=history,
        current_screen="webinar_announce",
        screen_message_id=callback.message.message_id,
    )

    await callback.message.edit_text(
        webinar_lexicon.TEXTS["webinar_announce"],
        reply_markup=kb_webinar_announce(),
    )

    await callback.answer()


@router.callback_query(F.data == "webinar_register")
async def open_webinar_register(callback: types.CallbackQuery, state: FSMContext):
    """
    Страница "Регистрация на вебинар"
    (форма + кнопка оплаты через URL)
    """
    data = await state.get_data()
    history = data.get("history", [])
    current = data.get("current_screen")

    if current and current != "webinar_register":
        history.append(current)

    await state.update_data(
        history=history,
        current_screen="webinar_register",
        screen_message_id=callback.message.message_id,
    )

    await callback.message.edit_text(
        webinar_lexicon.TEXTS["webinar_register_info"],
        reply_markup=kb_webinar_register(),
    )

    await callback.answer()


@router.callback_query(F.data == "webinar_pay")
async def webinar_pay(callback: types.CallbackQuery):
    """
    Если захочешь — сюда можно подвязать прямую оплату Telegram Stars.
    Пока оставляем сообщение-заглушку.
    """
    await callback.answer("Оплата вебинара будет добавлена позже 💳", show_alert=True)
