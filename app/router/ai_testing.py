from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from app.lexicon import ai_testing as ai_testing_lexicon

router = Router()

AI_TEST_URL = "https://tally.so/r/wo8jo5"


@router.callback_query(F.data == "ai_test")
async def open_ai_test(callback: CallbackQuery, state: FSMContext):
    """
    Экран теста:
    - текст
    - кнопка "Пройти тест" с обычным URL
    - кнопка "Назад"
    """

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Пройти тест",
                    url=AI_TEST_URL,
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data="back",
                )
            ],
        ]
    )

    # обновляем состояние
    data = await state.get_data()
    history = data.get("history", [])
    current = data.get("current_screen")

    if current and current != "ai_test":
        history.append(current)

    await state.update_data(
        history=history,
        current_screen="ai_test",
        screen_message_id=callback.message.message_id,
    )

    await callback.message.edit_text(
        ai_testing_lexicon.TEXTS["ai_test_intro"],
        reply_markup=kb,
    )

    await callback.answer()
