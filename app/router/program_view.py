# app/router/program_view.py

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

from app.lexicon import program_view as program_lexicon
from app.navigation import show_screen
from app.utils.send_photo import send_photo_with_fallback

router = Router()

PROGRAM_PHOTO_PATH = "app/static/программа.png"

PROGRAM_PAGE_KEYS = [
    "program_page_1",
    "program_page_2",
    "program_page_3",
    "program_page_4",
    "program_page_5",
    "program_page_6",
    "program_page_7",
]
PROGRAM_CFG = {
    "file_id": "AgACAgIAAxkBAAIDvmk6waq-xWgGvZpaDP0Ug4oRyxmaAALTDGsbmfrZSRKOXQcftEFXAQADAgADeQADNgQ",  # или сохранённый file_id картинки
    "file_path": "app/static/программа.png",
}
TOTAL_PAGES = len(PROGRAM_PAGE_KEYS)


def build_program_keyboard(page_index: int) -> InlineKeyboardMarkup:
    current_page = page_index + 1
    center_text = f"{current_page}/{TOTAL_PAGES}"

    keyboard = [
        [
            InlineKeyboardButton(text="←", callback_data="program_prev"),
            InlineKeyboardButton(text=center_text, callback_data="program_page_info"),
            InlineKeyboardButton(text="→", callback_data="program_next"),
        ],
        [
            InlineKeyboardButton(text="Назад", callback_data="program_back"),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_program_text(page_index: int) -> str:
    """Только текст модуля, без превью."""
    text_key = PROGRAM_PAGE_KEYS[page_index]
    return program_lexicon.TEXTS[text_key].strip()


@router.callback_query(F.data == "program")
async def open_program(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Логика как у экспертов:
    - удаляем прошлый экран (screen_message_id), если был
    - (на всякий) удаляем старый program_preview_message_id, если остался
    - отправляем отдельным сообщением program_preview
    - после него отправляем фото с модулем 1/7 + карусель
    """
    data = await state.get_data()
    prev_screen = data.get("current_screen") or "start"
    old_screen_msg_id = data.get("screen_message_id")
    old_preview_msg_id = data.get("program_preview_message_id")
    chat_id = callback.message.chat.id

    # 1. Удаляем старый "экран" (если был)
    if old_screen_msg_id:
        try:
            await bot.delete_message(chat_id, old_screen_msg_id)
        except Exception:
            pass

    # 2. На всякий случай сносим старый превью-текст, если остался
    if old_preview_msg_id:
        try:
            await bot.delete_message(chat_id, old_preview_msg_id)
        except Exception:
            pass

    # 3. Отправляем превью-текст (отдельное сообщение)
    preview_text = program_lexicon.TEXTS.get("program_preview", "").strip()
    preview_msg = None
    if preview_text:
        preview_msg = await callback.message.answer(preview_text)

    # 4. Отправляем фото-карусель с модулем 1/7
    page_index = 0
    text = get_program_text(page_index)
    kb = build_program_keyboard(page_index)

    carousel_msg = await send_photo_with_fallback(
        message=callback.message,
        bot=bot,
        file_id=PROGRAM_CFG.get("file_id"),     # если есть
        file_path=PROGRAM_PHOTO_PATH,           # путь
        caption=text,
        reply_markup=kb,
    )
    await state.update_data(
        program_page=page_index,
        program_prev_screen=prev_screen,
        program_preview_message_id=preview_msg.message_id if preview_msg else None,
        current_screen="program",
        screen_message_id=carousel_msg.message_id,  # главный "экран" = карусель
    )

    await callback.answer()


@router.callback_query(F.data.in_(["program_prev", "program_next"]))
async def program_switch(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Листаем модули по caption у одного и того же фото.
    Превью-текст остаётся отдельным сообщением сверху, мы его не трогаем.
    """
    data = await state.get_data()
    page = data.get("program_page", 0)

    if callback.data == "program_next":
        page = (page + 1) % TOTAL_PAGES
    else:  # program_prev
        page = (page - 1) % TOTAL_PAGES

    await state.update_data(program_page=page)

    text = get_program_text(page)
    kb = build_program_keyboard(page)

    try:
        await callback.message.edit_caption(
            caption=text,
            reply_markup=kb,
        )
    except TelegramBadRequest:
        # если вдруг сообщение стало текстовым — пересобираем экран
        chat_id = callback.message.chat.id
        photo = FSInputFile(PROGRAM_PHOTO_PATH)

        try:
            media = InputMediaPhoto(media=photo, caption=text)
            await callback.message.edit_media(
                media=media,
                reply_markup=kb,
            )
        except TelegramBadRequest:
            msg = await callback.message.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=kb,
            )
            await state.update_data(screen_message_id=msg.message_id)

    await callback.answer()


@router.callback_query(F.data == "program_page_info")
async def program_page_info(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "program_back")
async def program_back(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Назад из программы:
    - удаляем только превью-текст
    - отдаём текущее сообщение (карусель) под управление show_screen
      → оно превратится в предыдущий экран
    """
    data = await state.get_data()
    prev_screen = data.get("program_prev_screen") or "academy"
    preview_msg_id = data.get("program_preview_message_id")
    chat_id = callback.message.chat.id

    # Удаляем превью-текст
    if preview_msg_id:
        try:
            await bot.delete_message(chat_id, preview_msg_id)
        except Exception:
            pass

    # Чистим служебные поля программы
    await state.update_data(
        program_page=None,
        program_prev_screen=None,
        program_preview_message_id=None,
        current_screen=prev_screen,
    )

    # Возвращаем предыдущий экран через общий навигатор
    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id=prev_screen,
        as_new_message=False,
        push_history=False,
    )

    await callback.answer()
