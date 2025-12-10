# app/router/ai_testing.py

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    FSInputFile,
    InputMediaPhoto,
)
from aiogram.exceptions import TelegramBadRequest

from app.lexicon import ai_testing as ai_testing_lexicon

router = Router()

AI_TEST_URL = "https://tally.so/r/wo8jo5"
AI_TEST_PHOTO_PATH = "app/static/start/surfers_main.jpg"


def build_ai_test_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура:
    [Пройти тест]
    [Назад]
    """
    return InlineKeyboardMarkup(
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


@router.callback_query(F.data == "ai_test")
async def open_ai_test(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Экран теста:
    - пытаемся ОТРЕДАКТИРОВАТЬ текущее сообщение в фото + caption
      (edit_media + reply_markup)
    - если не получается (сообщение без медиа и т.п.) — удаляем и шлём новое фото
    - обновляем history / current_screen / screen_message_id
    """
    data = await state.get_data()
    history = data.get("history", [])
    current = data.get("current_screen")
    screen_message_id = data.get("screen_message_id")
    chat_id = callback.message.chat.id

    # добавляем предыдущий экран в history, если приходим не из ai_test
    if current and current != "ai_test":
        history.append(current)

    text = ai_testing_lexicon.TEXTS["ai_test_intro"]
    kb = build_ai_test_keyboard()

    # медиа для редактирования
    media = InputMediaPhoto(
        media=FSInputFile(AI_TEST_PHOTO_PATH),
        caption=text,
    )

    edited = False

    # пробуем редактировать существующее сообщение (если оно есть и не просили new)
    if screen_message_id is not None:
        try:
            await callback.message.edit_media(
                media=media,
                reply_markup=kb,
            )
            edited = True
        except TelegramBadRequest:
            edited = False
        except Exception:
            edited = False

    if not edited:
        # если не смогли отредактировать — удаляем старый экран (если был)
        if screen_message_id is not None:
            try:
                await bot.delete_message(chat_id, screen_message_id)
            except Exception:
                pass

        # отправляем новое сообщение с фото
        msg = await callback.message.answer_photo(
            photo=FSInputFile(AI_TEST_PHOTO_PATH),
            caption=text,
            reply_markup=kb,
        )
        screen_message_id = msg.message_id
    else:
        # при успешном edit_media id сообщения не меняется
        screen_message_id = callback.message.message_id

    # сохраняем состояние экрана
    await state.update_data(
        history=history,
        current_screen="ai_test",
        screen_message_id=screen_message_id,
    )

    await callback.answer()
