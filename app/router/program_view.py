# app/router/program_view.py

from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from app.lexicon import program_view as program_lexicon
from app.navigation import show_screen  # используем для "Назад" на предыдущий экран

router = Router()

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


@router.callback_query(F.data == "program")
async def open_program(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Первый заход в раздел "Программа".
    Показываем страницу 1/7 (обзор + модуль 1).
    """

    data = await state.get_data()
    prev_screen = data.get("current_screen")

    # запоминаем, откуда пришли, и что сейчас на странице 0 (1/7)
    await state.update_data(
        program_page=0,
        program_prev_screen=prev_screen,
        current_screen="program",
    )

    page_index = 0
    text_key = PROGRAM_PAGE_KEYS[page_index]
    text = program_lexicon.TEXTS[text_key]

    await callback.message.edit_text(
        text,
        reply_markup=build_program_keyboard(page_index),
    )

    await callback.answer()


@router.callback_query(F.data.in_(["program_prev", "program_next"]))
async def program_switch(callback: CallbackQuery, state: FSMContext):
    """
    Листаем модули влево/вправо.
    С цикличностью:
      - на 7/7 вправо → 1/7
      - на 1/7 влево → 7/7
    """

    data = await state.get_data()
    page = data.get("program_page", 0)

    if callback.data == "program_next":
        page = (page + 1) % TOTAL_PAGES
    else:  # program_prev
        page = (page - 1) % TOTAL_PAGES

    await state.update_data(program_page=page)

    text_key = PROGRAM_PAGE_KEYS[page]
    text = program_lexicon.TEXTS[text_key]

    await callback.message.edit_text(
        text,
        reply_markup=build_program_keyboard(page),
    )

    await callback.answer()


@router.callback_query(F.data == "program_page_info")
async def program_page_info(callback: CallbackQuery):
    """
    Средняя "кнопка" с индикатором 1/7 не должна ничего делать.
    Просто убираем крутилку.
    """
    await callback.answer()


@router.callback_query(F.data == "program_back")
async def program_back(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Кнопка "Назад" в программе:
    возвращает на тот экран, с которого зашли в раздел "Программа" (обычно academy).
    """

    data = await state.get_data()
    prev_screen = data.get("program_prev_screen") or "academy"

    # очищаем служебные поля программы
    await state.update_data(
        program_page=None,
        program_prev_screen=None,
        current_screen=prev_screen,
    )

    # показываем предыдущий экран через общий навигатор
    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id=prev_screen,
        as_new_message=False,
        push_history=False,
    )

    await callback.answer()
