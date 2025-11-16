# app/navigation.py

from dataclasses import dataclass
from typing import Dict, Any, Union

from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram import Bot

from app.lexicon import start as lex_start
from app.lexicon import academy as lex_academy
from app.lexicon import ai_testing as lex_ai_testing
from app.lexicon import pricing as lex_pricing
from app.lexicon import webinar as lex_webinar
from app.lexicon import ask_question as lex_ask_question
from app.lexicon import corporate as lex_corporate
from app.lexicon import program_view as lex_program
from app.lexicon import experts as lex_experts
from app.lexicon import ai_photoshoot as lex_photoshoot

from app.button.factory import build_inline_kb


@dataclass
class ScreenConfig:
    text_module: Any
    text_key: str
    buttons_key: str


SCREENS: Dict[str, ScreenConfig] = {
    "start": ScreenConfig(lex_start, "start", "start"),
    "academy": ScreenConfig(lex_academy, "academy_about", "academy_about"),
    "ai_test": ScreenConfig(lex_ai_testing, "ai_test_intro", "ai_test"),
    "pricing": ScreenConfig(lex_pricing, "pricing_intro", "pricing"),
    "webinar_announce": ScreenConfig(lex_webinar, "webinar_announce", "webinar_announce"),
    "webinar_register": ScreenConfig(lex_webinar, "webinar_register_info", "webinar_register"),
    "ask_question": ScreenConfig(lex_ask_question, "ask_question_intro", "ask_question"),
    "corporate": ScreenConfig(lex_corporate, "corporate_main", "corporate"),
    "program": ScreenConfig(lex_program, "program_intro", "program_navigation"),
    "experts": ScreenConfig(lex_experts, "experts_intro", "experts_navigation"),
    "ai_photoshoot": ScreenConfig(lex_photoshoot, "ai_photoshoot_intro", "ai_photoshoot"),
}


# async def show_screen(
#     target: Union[Message, CallbackQuery],
#     state: FSMContext,
#     bot: Bot,
#     screen_id: str,
#     *,
#     as_new_message: bool = False,
#     push_history: bool = True,
# ):
#     """
#     Универсальный рендер экрана.
#     - Всегда стараемся редактировать одно и то же сообщение (screen_message_id).
#     - Если id нет или as_new_message=True — отправляем новое сообщение и сохраняем id.
#     """

#     cfg = SCREENS[screen_id]

#     data = await state.get_data()
#     history = data.get("history", [])
#     current = data.get("current_screen")
#     screen_message_id = data.get("screen_message_id")

#     if push_history and current and current != screen_id:
#         history.append(current)

#     text = cfg.text_module.TEXTS[cfg.text_key]
#     kb = build_inline_kb(cfg.buttons_key)

#     # Определяем chat_id
#     if isinstance(target, CallbackQuery):
#         chat_id = target.message.chat.id
#     else:
#         chat_id = target.chat.id

#     # Если явно сказали отправить новое сообщение
#     if as_new_message or screen_message_id is None:
#         if isinstance(target, CallbackQuery):
#             msg = await target.message.answer(text, reply_markup=kb)
#         else:
#             msg = await target.answer(text, reply_markup=kb)

#         screen_message_id = msg.message_id

#     else:
#         # редактируем ранее запомненное сообщение
#         await bot.edit_message_text(
#             chat_id=chat_id,
#             message_id=screen_message_id,
#             text=text,
#             reply_markup=kb,
#         )

#     await state.update_data(
#         history=history,
#         current_screen=screen_id,
#         screen_message_id=screen_message_id,
#     )
async def show_screen(
    target: Union[Message, CallbackQuery],
    state: FSMContext,
    bot: Bot,
    screen_id: str,
    *,
    as_new_message: bool = False,
    push_history: bool = True,
):
    """
    Универсальный рендер текстового экрана:
    - один message_id на все экраны
    - редактирование текста и клавиатуры
    - история экранов
    """

    cfg = SCREENS[screen_id]

    data = await state.get_data()
    history = data.get("history", [])
    current = data.get("current_screen")
    screen_message_id = data.get("screen_message_id")

    # История
    if push_history and current and current != screen_id:
        history.append(current)

    # Текст и клавиатура
    text = cfg.text_module.TEXTS[cfg.text_key]
    kb = build_inline_kb(cfg.buttons_key)

    # Определяем chat_id
    if isinstance(target, CallbackQuery):
        chat_id = target.message.chat.id
    else:
        chat_id = target.chat.id

    # Если нужен новый экран
    if as_new_message or screen_message_id is None:
        if isinstance(target, CallbackQuery):
            msg = await target.message.answer(text, reply_markup=kb)
        else:
            msg = await target.answer(text, reply_markup=kb)

        screen_message_id = msg.message_id

    else:
        # редактирование существующего экрана
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=screen_message_id,
            text=text,
            reply_markup=kb,
        )

    await state.update_data(
        history=history,
        current_screen=screen_id,
        screen_message_id=screen_message_id,
    )
