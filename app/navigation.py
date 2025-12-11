from dataclasses import dataclass
from typing import Dict, Any, Union, Optional

from aiogram.fsm.context import FSMContext
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    InputMediaPhoto,
    InputMediaDocument,
    InputMediaVideo,
)
from aiogram.exceptions import TelegramBadRequest
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

    # необязательные поля под медиа
    media_type: Optional[str] = None  # "photo", "document", "video"
    file_id: Optional[str] = None     # уже загруженный в TG file_id
    file_path: Optional[str] = None   # локальный путь к файлу (FSInputFile)


SCREENS: Dict[str, ScreenConfig] = {
    "start": ScreenConfig(lex_start, "start", "start", "photo", file_path="app/static/start/surfers_main.png"),
    "academy": ScreenConfig(lex_academy, "academy_about", "academy_about", "photo", file_path="app/static/academy/academy.png"),
    "ai_test": ScreenConfig(lex_ai_testing, "ai_test_intro", "ai_test"),
    # "pricing": ScreenConfig(lex_pricing, "pricing_intro", "pricing", "photo", file_path="app/static/pricing/pricing.png"),

    # текстовые экраны для вебинаров
    "webinar_announce": ScreenConfig(lex_webinar, "webinar_announce", "webinar_announce"),
    "webinar_register": ScreenConfig(lex_webinar, "webinar_register_info", "webinar_register"),

    # главный экран вебинаров — с фото (пример)
    "webinar": ScreenConfig(
        text_module=lex_webinar,
        text_key="webinar_main",
        buttons_key="webinar",
        media_type="photo",

        file_path="app/static/webinar/efiry.png",
    ),
    "webinar_18": ScreenConfig(lex_webinar, "webinar_18_details", "webinar_18"),
    "webinar_21": ScreenConfig(lex_webinar, "webinar_21_details", "webinar_21"),


    "ask_question": ScreenConfig(lex_ask_question, "ask_question_intro", "ask_question"),
    "corporate": ScreenConfig(
        lex_corporate,
        "corporate_main",
        "corporate",
        media_type="document",
        file_id="BQACAgUAAxkBAAMRaRohHRc5w5zl85tQoLrN9VjAl_cAApsXAAIVstBUp69Lqylg4q82BA",
        file_path="app/static/program/GPT Surfers.pdf"
    ),
    "program": ScreenConfig(lex_program, "program_intro", "program_navigation"),
    "experts": ScreenConfig(lex_experts, "experts_intro", "experts_navigation", "photo"),
    "ai_photoshoot": ScreenConfig(lex_photoshoot, "ai_photoshoot_intro", "ai_photoshoot"),
}


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
    Универсальный рендер экрана:
    - media_type = None  → обычный текст + инлайн-клавиатура
    - media_type задан   → экран с медиа (photo/document/video) + caption + инлайн-клава

    Для экранов с медиа:
      1) если это новый экран (as_new_message или нет screen_message_id) → отправляем новое медиа;
         при ошибке wrong file identifier по file_id — пробуем file_path;
      2) если сообщение уже есть:
         - пробуем edit_message_media(...) с file_id, при ошибке wrong file identifier → пробуем с file_path;
         - если ошибка другого типа → пробуем edit_message_caption(...);
         - если снова ошибка → удаляем сообщение и отправляем обычный текст.
    """

    if screen_id not in SCREENS:
        screen_id = "start"

    cfg = SCREENS[screen_id]

    data = await state.get_data()
    history = data.get("history", [])
    current = data.get("current_screen")
    screen_message_id = data.get("screen_message_id")

    # история экранов
    if push_history and current and current != screen_id:
        history.append(current)

    text = cfg.text_module.TEXTS[cfg.text_key]
    kb = build_inline_kb(cfg.buttons_key)

    # chat_id
    if isinstance(target, CallbackQuery):
        chat_id = target.message.chat.id
    else:
        chat_id = target.chat.id

    media_type = cfg.media_type
    file_id = cfg.file_id
    file_path = cfg.file_path

    # ===== ветка: только текст =====
    if media_type is None:
        if as_new_message or screen_message_id is None:
            if isinstance(target, CallbackQuery):
                msg = await target.message.answer(text, reply_markup=kb)
            else:
                msg = await target.answer(text, reply_markup=kb)
            screen_message_id = msg.message_id
        else:
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=screen_message_id,
                    text=text,
                    reply_markup=kb,
                )
            except TelegramBadRequest:
                try:
                    await bot.delete_message(chat_id, screen_message_id)
                except Exception:
                    pass
                msg = await bot.send_message(chat_id, text, reply_markup=kb)
                screen_message_id = msg.message_id

    # ===== ветка: экран с медиа =====
    else:
        # хелпер: отправка медиа с fallback по file_id → file_path
        async def send_media_with_fallback() -> Message:
            # кандидаты: сначала id, потом путь
            candidates: list[tuple[str, str]] = []
            if file_id:
                candidates.append(("id", file_id))
            if file_path:
                candidates.append(("path", file_path))

            last_error: Exception | None = None

            for kind, value in candidates:
                try:
                    if kind == "path":
                        media_input = FSInputFile(value)
                    else:
                        media_input = value

                    if media_type == "photo":
                        return await bot.send_photo(
                            chat_id=chat_id,
                            photo=media_input,
                            caption=text,
                            reply_markup=kb,
                        )
                    elif media_type in ("document", "file"):
                        return await bot.send_document(
                            chat_id=chat_id,
                            document=media_input,
                            caption=text,
                            reply_markup=kb,
                        )
                    elif media_type == "video":
                        return await bot.send_video(
                            chat_id=chat_id,
                            video=media_input,
                            caption=text,
                            reply_markup=kb,
                        )
                    else:
                        # неизвестный тип — как текст
                        return await bot.send_message(
                            chat_id=chat_id,
                            text=text,
                            reply_markup=kb,
                        )
                except TelegramBadRequest as e:
                    last_error = e
                    # если проблема именно с file_id — пробуем следующий вариант
                    if "wrong file identifier" in str(e).lower():
                        continue
                    # другая ошибка — не мучаем дальше
                    break
                except Exception as e:
                    last_error = e
                    break

            # если вообще не удалось отправить медиа — деградируем в текст
            return await bot.send_message(chat_id=chat_id, text=text, reply_markup=kb)

        # хелпер: редактирование медиа с fallback по file_id → file_path
        async def edit_media_with_fallback(message_id: int) -> bool:
            """
            Возвращает True, если редактирование удалось, False — если нет.
            """
            # 1. сначала пробуем менять медиа (id -> path)
            for kind in ("id", "path"):
                if kind == "id" and not file_id:
                    continue
                if kind == "path" and not file_path:
                    continue

                try:
                    if kind == "path":
                        media_input = FSInputFile(file_path)
                    else:
                        media_input = file_id

                    if media_type == "photo":
                        input_media = InputMediaPhoto(media=media_input, caption=text)
                    elif media_type in ("document", "file"):
                        input_media = InputMediaDocument(media=media_input, caption=text)
                    elif media_type == "video":
                        input_media = InputMediaVideo(media=media_input, caption=text)
                    else:
                        input_media = None

                    if input_media is None:
                        break

                    await bot.edit_message_media(
                        chat_id=chat_id,
                        message_id=message_id,
                        media=input_media,
                        reply_markup=kb,
                    )
                    return True
                except TelegramBadRequest as e:
                    # если ошибка не про file identifier — не крутим дальше
                    if "wrong file identifier" not in str(e).lower():
                        break
                except Exception:
                    break

            # 2. если не получилось менять медиа — пробуем хотя бы caption + кнопки
            try:
                await bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=message_id,
                    caption=text,
                    reply_markup=kb,
                )
                return True
            except TelegramBadRequest:
                return False
            except Exception:
                return False

        # нет файла вообще → деградация в текст
        if not file_id and not file_path:
            if as_new_message or screen_message_id is None:
                if isinstance(target, CallbackQuery):
                    msg = await target.message.answer(text, reply_markup=kb)
                else:
                    msg = await target.answer(text, reply_markup=kb)
                screen_message_id = msg.message_id
            else:
                try:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=screen_message_id,
                        text=text,
                        reply_markup=kb,
                    )
                except TelegramBadRequest:
                    try:
                        await bot.delete_message(chat_id, screen_message_id)
                    except Exception:
                        pass
                    msg = await bot.send_message(chat_id, text, reply_markup=kb)
                    screen_message_id = msg.message_id

        else:
            # --- 1) НОВЫЙ ЭКРАН С МЕДИА ---
            if as_new_message or screen_message_id is None:
                msg = await send_media_with_fallback()
                screen_message_id = msg.message_id

            # --- 2) ПЫТАЕМСЯ РЕДАКТИРОВАТЬ СУЩЕСТВУЮЩЕЕ ---
            else:
                ok = await edit_media_with_fallback(screen_message_id)
                if not ok:
                    # ничего не получилось — удаляем и шлём текст
                    try:
                        await bot.delete_message(chat_id, screen_message_id)
                    except Exception:
                        pass
                    msg = await bot.send_message(chat_id, text, reply_markup=kb)
                    screen_message_id = msg.message_id

    # сохраняем состояние
    await state.update_data(
        history=history,
        current_screen=screen_id,
        screen_message_id=screen_message_id,
    )
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
#     Универсальный рендер экрана:
#     - media_type = None  → обычный текст + инлайн-клавиатура
#     - media_type задан   → экран с медиа (photo/document/video) + caption + инлайн-клава

#     Для экранов с медиа:
#       1) если это новый экран (as_new_message или нет screen_message_id) → отправляем новое медиа;
#       2) если сообщение уже есть:
#          - пробуем edit_message_media(...)
#          - если ошибка → пробуем edit_message_caption(...)
#          - если снова ошибка → удаляем сообщение и отправляем обычный текст.
#     """

#     if screen_id not in SCREENS:
#         screen_id = "start"

#     cfg = SCREENS[screen_id]

#     data = await state.get_data()
#     history = data.get("history", [])
#     current = data.get("current_screen")
#     screen_message_id = data.get("screen_message_id")

#     # история экранов
#     if push_history and current and current != screen_id:
#         history.append(current)

#     text = cfg.text_module.TEXTS[cfg.text_key]
#     kb = build_inline_kb(cfg.buttons_key)

#     # chat_id
#     if isinstance(target, CallbackQuery):
#         chat_id = target.message.chat.id
#     else:
#         chat_id = target.chat.id

#     media_type = cfg.media_type
#     file_id = cfg.file_id
#     file_path = cfg.file_path

#     # ===== ветка: только текст =====
#     if media_type is None:
#         if as_new_message or screen_message_id is None:
#             if isinstance(target, CallbackQuery):
#                 msg = await target.message.answer(text, reply_markup=kb)
#             else:
#                 msg = await target.answer(text, reply_markup=kb)
#             screen_message_id = msg.message_id
#         else:
#             try:
#                 await bot.edit_message_text(
#                     chat_id=chat_id,
#                     message_id=screen_message_id,
#                     text=text,
#                     reply_markup=kb,
#                 )
#             except TelegramBadRequest:
#                 try:
#                     await bot.delete_message(chat_id, screen_message_id)
#                 except Exception:
#                     pass
#                 msg = await bot.send_message(chat_id, text, reply_markup=kb)
#                 screen_message_id = msg.message_id

#     # ===== ветка: экран с медиа =====
#     else:
#         # подготовка "файла"
#         if file_id:
#             media_input = file_id
#         elif file_path:
#             media_input = FSInputFile(file_path)
#         else:
#             # media_type есть, файла нет → деградируем в текст
#             if as_new_message or screen_message_id is None:
#                 if isinstance(target, CallbackQuery):
#                     msg = await target.message.answer(text, reply_markup=kb)
#                 else:
#                     msg = await target.answer(text, reply_markup=kb)
#                 screen_message_id = msg.message_id
#             else:
#                 try:
#                     await bot.edit_message_text(
#                         chat_id=chat_id,
#                         message_id=screen_message_id,
#                         text=text,
#                         reply_markup=kb,
#                     )
#                 except TelegramBadRequest:
#                     try:
#                         await bot.delete_message(chat_id, screen_message_id)
#                     except Exception:
#                         pass
#                     msg = await bot.send_message(chat_id, text, reply_markup=kb)
#                     screen_message_id = msg.message_id

#             await state.update_data(
#                 history=history,
#                 current_screen=screen_id,
#                 screen_message_id=screen_message_id,
#             )
#             return

#         # --- 1) НОВЫЙ ЭКРАН С МЕДИА ---
#         if as_new_message or screen_message_id is None:
#             if media_type == "photo":
#                 msg = await bot.send_photo(
#                     chat_id=chat_id,
#                     photo=media_input,
#                     caption=text,
#                     reply_markup=kb,
#                 )
#             elif media_type == "document":
#                 msg = await bot.send_document(
#                     chat_id=chat_id,
#                     document=media_input,
#                     caption=text,
#                     reply_markup=kb,
#                 )
#             elif media_type == "video":
#                 msg = await bot.send_video(
#                     chat_id=chat_id,
#                     video=media_input,
#                     caption=text,
#                     reply_markup=kb,
#                 )
#             else:
#                 msg = await bot.send_message(
#                     chat_id=chat_id,
#                     text=text,
#                     reply_markup=kb,
#                 )

#             screen_message_id = msg.message_id

#         # --- 2) ПЫТАЕМСЯ РЕДАКТИРОВАТЬ СУЩЕСТВУЮЩЕЕ МЕДИА ---
#         else:
#             edited = False

#             # 2.1) сначала edit_message_media
#             try:
#                 input_media = None
#                 if media_type == "photo":
#                     input_media = InputMediaPhoto(media=media_input, caption=text)
#                 elif media_type == "document":
#                     input_media = InputMediaDocument(media=media_input, caption=text)
#                 elif media_type == "video":
#                     input_media = InputMediaVideo(media=media_input, caption=text)

#                 if input_media is not None:
#                     await bot.edit_message_media(
#                         chat_id=chat_id,
#                         message_id=screen_message_id,
#                         media=input_media,
#                         reply_markup=kb,
#                     )
#                     edited = True
#             except TelegramBadRequest:
#                 edited = False

#             # 2.2) если не вышло — пробуем только caption
#             if not edited:
#                 try:
#                     await bot.edit_message_caption(
#                         chat_id=chat_id,
#                         message_id=screen_message_id,
#                         caption=text,
#                         reply_markup=kb,
#                     )
#                     edited = True
#                 except TelegramBadRequest:
#                     edited = False

#             # 2.3) если и это не удалось — удаляем и шлём текст
#             if not edited:
#                 try:
#                     await bot.delete_message(chat_id, screen_message_id)
#                 except Exception:
#                     pass

#                 msg = await bot.send_message(
#                     chat_id=chat_id,
#                     text=text,
#                     reply_markup=kb,
#                 )
#                 screen_message_id = msg.message_id

#     # сохраняем состояние
#     await state.update_data(
#         history=history,
#         current_screen=screen_id,
#         screen_message_id=screen_message_id,
#     )
