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
from app.navigation import show_screen  # используем для "Назад" на предыдущий экран

router = Router()

PROGRAM_PHOTO_PATH = "app/static/программа.png"

# список ключей страниц в лексиконе
PROGRAM_PAGE_KEYS = [
    "program_page_1",
    "program_page_2",
    "program_page_3",
    "program_page_4",
    "program_page_5",
    "program_page_6",
    "program_page_7",
]

TOTAL_PAGES = len(PROGRAM_PAGE_KEYS)


def build_program_keyboard(page_index: int) -> InlineKeyboardMarkup:
    """
    Клавиатура:
    ←    1/7    →
    [Назад]
    """
    current_page = page_index + 1  # человек видит нумерацию с 1
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
    """
    Сверху — program_preview, ниже — текст конкретной страницы.
    """
    preview = program_lexicon.TEXTS.get("program_preview", "").strip()
    page_key = PROGRAM_PAGE_KEYS[page_index]
    page_text = program_lexicon.TEXTS[page_key].strip()

    if preview:
        return f"{preview}\n{page_text}"
    return page_text


@router.callback_query(F.data == "program")
async def open_program(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Первый заход в раздел "Программа".
    Всегда показываем фото PROGRAM_PHOTO_PATH + caption (preview + страница 1/7).
    """
    data = await state.get_data()
    prev_screen = data.get("current_screen") or "start"
    screen_message_id = data.get("screen_message_id")
    chat_id = callback.message.chat.id

    page_index = 0
    text = get_program_text(page_index)
    kb = build_program_keyboard(page_index)
    photo = FSInputFile(PROGRAM_PHOTO_PATH)

    msg_id_result = None

    # Пытаемся превратить текущее сообщение в фото с caption
    if screen_message_id is not None and screen_message_id == callback.message.message_id:
        try:
            media = InputMediaPhoto(media=photo, caption=text)
            await callback.message.edit_media(
                media=media,
                reply_markup=kb,
            )
            msg_id_result = callback.message.message_id
        except TelegramBadRequest:
            # не получилось (был текст/другое) — удаляем и шлём новое фото
            try:
                await bot.delete_message(chat_id, screen_message_id)
            except Exception:
                pass
            msg = await callback.message.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=kb,
            )
            msg_id_result = msg.message_id
    else:
        # screen_message_id ещё не зафиксирован — просто шлём фото
        msg = await callback.message.answer_photo(
            photo=photo,
            caption=text,
            reply_markup=kb,
        )
        msg_id_result = msg.message_id

    await state.update_data(
        program_page=page_index,
        program_prev_screen=prev_screen,
        current_screen="program",
        screen_message_id=msg_id_result,
    )

    await callback.answer()


@router.callback_query(F.data.in_(["program_prev", "program_next"]))
async def program_switch(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Листаем модули влево/вправо по caption у одного и того же фото.
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
        # нормальный путь — просто меняем caption у фото
        await callback.message.edit_caption(
            caption=text,
            reply_markup=kb,
        )
    except TelegramBadRequest:
        # если вдруг сообщение оказалось текстовым — дожимаем до нужного формата
        photo = FSInputFile(PROGRAM_PHOTO_PATH)
        try:
            media = InputMediaPhoto(media=photo, caption=text)
            await callback.message.edit_media(
                media=media,
                reply_markup=kb,
            )
        except TelegramBadRequest:
            # крайний случай — шлём новое фото
            msg = await callback.message.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=kb,
            )
            await state.update_data(screen_message_id=msg.message_id)

    await callback.answer()


@router.callback_query(F.data == "program_page_info")
async def program_page_info(callback: CallbackQuery):
    """
    Средняя "кнопка" с индикатором 1/7 — неактивная.
    """
    await callback.answer()


@router.callback_query(F.data == "program_back")
async def program_back(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Кнопка "Назад" в программе:
    возвращает на тот экран, с которого зашли в раздел "Программа".
    """
    data = await state.get_data()
    prev_screen = data.get("program_prev_screen") or "academy"

    await state.update_data(
        program_page=None,
        program_prev_screen=None,
        current_screen=prev_screen,
    )

    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id=prev_screen,
        as_new_message=False,
        push_history=False,
    )

    await callback.answer()

# # app/router/program_view.py

# from aiogram import Router, F, Bot
# from aiogram.fsm.context import FSMContext
# from aiogram.types import (
#     InlineKeyboardMarkup,
#     InlineKeyboardButton,
#     CallbackQuery,
#     FSInputFile,
#     InputMediaPhoto,
# )
# from aiogram.exceptions import TelegramBadRequest

# from app.lexicon import program_view as program_lexicon
# from app.navigation import show_screen  # используем для "Назад" на предыдущий экран

# router = Router()

# PROGRAM_PHOTO_PATH = "app/static/программа.png"

# # список ключей страниц в лексиконе
# PROGRAM_PAGE_KEYS = [
#     "program_page_1",
#     "program_page_2",
#     "program_page_3",
#     "program_page_4",
#     "program_page_5",
#     "program_page_6",
#     "program_page_7",
# ]

# TOTAL_PAGES = len(PROGRAM_PAGE_KEYS)


# def build_program_keyboard(page_index: int) -> InlineKeyboardMarkup:
#     """
#     Клавиатура:
#     ←    1/7    →
#     [Назад]
#     """
#     current_page = page_index + 1  # человек видит нумерацию с 1
#     center_text = f"{current_page}/{TOTAL_PAGES}"

#     keyboard = [
#         [
#             InlineKeyboardButton(text="←", callback_data="program_prev"),
#             InlineKeyboardButton(text=center_text, callback_data="program_page_info"),
#             InlineKeyboardButton(text="→", callback_data="program_next"),
#         ],
#         [
#             InlineKeyboardButton(text="Назад", callback_data="program_back"),
#         ],
#     ]

#     return InlineKeyboardMarkup(inline_keyboard=keyboard)


# def get_program_text(page_index: int) -> str:
#     text_key = PROGRAM_PAGE_KEYS[page_index]
#     return program_lexicon.TEXTS[text_key]


# @router.callback_query(F.data == "program")
# async def open_program(callback: CallbackQuery, state: FSMContext, bot: Bot):
#     """
#     Первый заход в раздел "Программа".
#     Всегда показываем фото PROGRAM_PHOTO_PATH + caption с текстом страницы 1/7.
#     """
#     data = await state.get_data()
#     prev_screen = data.get("current_screen") or "start"
#     screen_message_id = data.get("screen_message_id")
#     chat_id = callback.message.chat.id

#     page_index = 0
#     text = get_program_text(page_index)
#     kb = build_program_keyboard(page_index)
#     photo = FSInputFile(PROGRAM_PHOTO_PATH)

#     msg_id_result = None

#     # Пытаемся превратить текущее сообщение в фото с caption
#     if screen_message_id is not None and screen_message_id == callback.message.message_id:
#         try:
#             media = InputMediaPhoto(media=photo, caption=text)
#             await callback.message.edit_media(
#                 media=media,
#                 reply_markup=kb,
#             )
#             msg_id_result = callback.message.message_id
#         except TelegramBadRequest:
#             # не получилось (был текст/другое) — удаляем и шлём новое фото
#             try:
#                 await bot.delete_message(chat_id, screen_message_id)
#             except Exception:
#                 pass
#             msg = await callback.message.answer_photo(
#                 photo=photo,
#                 caption=text,
#                 reply_markup=kb,
#             )
#             msg_id_result = msg.message_id
#     else:
#         # screen_message_id ещё не зафиксирован — просто шлём фото
#         msg = await callback.message.answer_photo(
#             photo=photo,
#             caption=text,
#             reply_markup=kb,
#         )
#         msg_id_result = msg.message_id

#     await state.update_data(
#         program_page=page_index,
#         program_prev_screen=prev_screen,
#         current_screen="program",
#         screen_message_id=msg_id_result,
#     )

#     await callback.answer()


# @router.callback_query(F.data.in_(["program_prev", "program_next"]))
# async def program_switch(callback: CallbackQuery, state: FSMContext, bot: Bot):
#     """
#     Листаем модули влево/вправо по caption у одного и того же фото.
#     """
#     data = await state.get_data()
#     page = data.get("program_page", 0)

#     if callback.data == "program_next":
#         page = (page + 1) % TOTAL_PAGES
#     else:  # program_prev
#         page = (page - 1) % TOTAL_PAGES

#     await state.update_data(program_page=page)

#     text = get_program_text(page)
#     kb = build_program_keyboard(page)

#     try:
#         # нормальный путь — просто меняем caption у фото
#         await callback.message.edit_caption(
#             caption=text,
#             reply_markup=kb,
#         )
#     except TelegramBadRequest:
#         # если вдруг сообщение оказалось текстовым — дожимаем до нужного формата
#         photo = FSInputFile(PROGRAM_PHOTO_PATH)
#         try:
#             media = InputMediaPhoto(media=photo, caption=text)
#             await callback.message.edit_media(
#                 media=media,
#                 reply_markup=kb,
#             )
#         except TelegramBadRequest:
#             # крайний случай — шлём новое фото
#             msg = await callback.message.answer_photo(
#                 photo=photo,
#                 caption=text,
#                 reply_markup=kb,
#             )
#             await state.update_data(screen_message_id=msg.message_id)

#     await callback.answer()


# @router.callback_query(F.data == "program_page_info")
# async def program_page_info(callback: CallbackQuery):
#     """
#     Средняя "кнопка" с индикатором 1/7 — неактивная.
#     """
#     await callback.answer()


# @router.callback_query(F.data == "program_back")
# async def program_back(callback: CallbackQuery, state: FSMContext, bot: Bot):
#     """
#     Кнопка "Назад" в программе:
#     возвращает на тот экран, с которого зашли в раздел "Программа".
#     """
#     data = await state.get_data()
#     prev_screen = data.get("program_prev_screen") or "academy"

#     await state.update_data(
#         program_page=None,
#         program_prev_screen=None,
#         current_screen=prev_screen,
#     )

#     await show_screen(
#         target=callback,
#         state=state,
#         bot=bot,
#         screen_id=prev_screen,
#         as_new_message=False,
#         push_history=False,
#     )

#     await callback.answer()

# # app/router/program_view.py

# from aiogram import Router, F, types, Bot
# from aiogram.fsm.context import FSMContext
# from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# from app.lexicon import program_view as program_lexicon
# from app.navigation import show_screen  # используем для "Назад" на предыдущий экран

# router = Router()

# # список ключей страниц в лексиконе
# PROGRAM_PAGE_KEYS = [
#     "program_page_1",
#     "program_page_2",
#     "program_page_3",
#     "program_page_4",
#     "program_page_5",
#     "program_page_6",
#     "program_page_7",
# ]

# TOTAL_PAGES = len(PROGRAM_PAGE_KEYS)


# def build_program_keyboard(page_index: int) -> InlineKeyboardMarkup:
#     """
#     Клавиатура:
#     ←    1/7    →
#     [Назад]
#     """

#     current_page = page_index + 1  # человек видит нумерацию с 1
#     center_text = f"{current_page}/{TOTAL_PAGES}"

#     keyboard = [
#         [
#             InlineKeyboardButton(text="←", callback_data="program_prev"),
#             InlineKeyboardButton(text=center_text, callback_data="program_page_info"),
#             InlineKeyboardButton(text="→", callback_data="program_next"),
#         ],
#         [
#             InlineKeyboardButton(text="Назад", callback_data="program_back"),
#         ],
#     ]

#     return InlineKeyboardMarkup(inline_keyboard=keyboard)


# @router.callback_query(F.data == "program")
# async def open_program(callback: CallbackQuery, state: FSMContext, bot: Bot):
#     """
#     Первый заход в раздел "Программа".
#     Показываем страницу 1/7 (обзор + модуль 1).
#     """

#     data = await state.get_data()
#     prev_screen = data.get("current_screen")

#     # запоминаем, откуда пришли, и что сейчас на странице 0 (1/7)
#     await state.update_data(
#         program_page=0,
#         program_prev_screen=prev_screen,
#         current_screen="program",
#     )

#     page_index = 0
#     text_key = PROGRAM_PAGE_KEYS[page_index]
#     text = program_lexicon.TEXTS[text_key]

#     await callback.message.edit_text(
#         text,
#         reply_markup=build_program_keyboard(page_index),
#     )

#     await callback.answer()


# @router.callback_query(F.data.in_(["program_prev", "program_next"]))
# async def program_switch(callback: CallbackQuery, state: FSMContext):
#     """
#     Листаем модули влево/вправо.
#     С цикличностью:
#       - на 7/7 вправо → 1/7
#       - на 1/7 влево → 7/7
#     """

#     data = await state.get_data()
#     page = data.get("program_page", 0)

#     if callback.data == "program_next":
#         page = (page + 1) % TOTAL_PAGES
#     else:  # program_prev
#         page = (page - 1) % TOTAL_PAGES

#     await state.update_data(program_page=page)

#     text_key = PROGRAM_PAGE_KEYS[page]
#     text = program_lexicon.TEXTS[text_key]

#     await callback.message.edit_text(
#         text,
#         reply_markup=build_program_keyboard(page),
#     )

#     await callback.answer()


# @router.callback_query(F.data == "program_page_info")
# async def program_page_info(callback: CallbackQuery):
#     """
#     Средняя "кнопка" с индикатором 1/7 не должна ничего делать.
#     Просто убираем крутилку.
#     """
#     await callback.answer()


# @router.callback_query(F.data == "program_back")
# async def program_back(callback: CallbackQuery, state: FSMContext, bot: Bot):
#     """
#     Кнопка "Назад" в программе:
#     возвращает на тот экран, с которого зашли в раздел "Программа" (обычно academy).
#     """

#     data = await state.get_data()
#     prev_screen = data.get("program_prev_screen") or "academy"

#     # очищаем служебные поля программы
#     await state.update_data(
#         program_page=None,
#         program_prev_screen=None,
#         current_screen=prev_screen,
#     )

#     # показываем предыдущий экран через общий навигатор
#     await show_screen(
#         target=callback,
#         state=state,
#         bot=bot,
#         screen_id=prev_screen,
#         as_new_message=False,
#         push_history=False,
#     )

#     await callback.answer()
