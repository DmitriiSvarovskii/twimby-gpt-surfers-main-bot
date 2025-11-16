# app/router/experts.py

from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    FSInputFile,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
)

from app.lexicon import experts as experts_lexicon
from app.navigation import show_screen

router = Router()

# Описываем экспертов: ключ текста и путь к фото
EXPERTS = [
    {
        "key": "expert_ilya",
        "photo": "app/static/expert/Илья_Шитов.jpg",
    },
    {
        "key": "expert_alexander",
        "photo": "app/static/expert/Александр_Масленников.jpg",
    },
    {
        "key": "expert_eduard",
        "photo": "app/static/expert/Эдуард_Эргашев.jpg",
    },
    {
        "key": "expert_mikhail",
        "photo": "app/static/expert/no_photo.png",
    },
    {
        "key": "expert_maxim",
        "photo": "app/static/expert/no_photo.png",
    },
]

TOTAL_EXPERTS = len(EXPERTS)


def build_experts_keyboard(index: int) -> InlineKeyboardMarkup:
    """
    Клавиатура:
    ←   1/5   →
    [Назад]
    """
    center = f"{index + 1}/{TOTAL_EXPERTS}"

    keyboard = [
        [
            InlineKeyboardButton(text="←", callback_data="experts_prev"),
            InlineKeyboardButton(text=center, callback_data="experts_page_info"),
            InlineKeyboardButton(text="→", callback_data="experts_next"),
        ],
        [
            InlineKeyboardButton(text="Назад", callback_data="experts_back"),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.callback_query(F.data == "experts")
async def open_experts(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Первый вход в раздел экспертов.
    Логика:
    - удаляем предыдущее "экранное" сообщение (если есть)
    - показываем карточку первого эксперта с фото
    """
    data = await state.get_data()
    prev_screen = data.get("current_screen")            # откуда пришли (обычно 'academy')
    screen_message_id = data.get("screen_message_id")   # экран, который рисовал show_screen

    # 1) Удаляем предыдущее экранное сообщение, если оно есть
    if screen_message_id is not None:
        try:
            await bot.delete_message(
                chat_id=callback.message.chat.id,
                message_id=screen_message_id,
            )
        except Exception:
            pass

        # Обнуляем, чтобы show_screen потом прислал новый экран, а не редактировал удалённый
        await state.update_data(screen_message_id=None)

    # 2) Показываем первого эксперта
    index = 0
    expert_cfg = EXPERTS[index]
    text_key = expert_cfg["key"]
    text = experts_lexicon.TEXTS[text_key]

    photo = FSInputFile(expert_cfg["photo"])

    await state.update_data(
        experts_index=index,
        experts_prev_screen=prev_screen,
        current_screen="experts",
    )

    await callback.message.answer_photo(
        photo=photo,
        caption=text,
        reply_markup=build_experts_keyboard(index),
    )

    await callback.answer()


@router.callback_query(F.data.in_(["experts_prev", "experts_next"]))
async def experts_switch(callback: CallbackQuery, state: FSMContext):
    """
    Листаем экспертов:
      - на 5/5 вправо → 1/5
      - на 1/5 влево → 5/5
    """
    data = await state.get_data()
    index = data.get("experts_index", 0)

    if callback.data == "experts_next":
        index = (index + 1) % TOTAL_EXPERTS
    else:  # experts_prev
        index = (index - 1) % TOTAL_EXPERTS

    await state.update_data(experts_index=index)

    expert_cfg = EXPERTS[index]
    text_key = expert_cfg["key"]
    text = experts_lexicon.TEXTS[text_key]
    photo = FSInputFile(expert_cfg["photo"])

    media = InputMediaPhoto(
        media=photo,
        caption=text,
    )

    await callback.message.edit_media(
        media=media,
        reply_markup=build_experts_keyboard(index),
    )

    await callback.answer()


@router.callback_query(F.data == "experts_page_info")
async def experts_page_info(callback: CallbackQuery):
    """
    Средняя "кнопка" с индикатором 1/5 — неактивная.
    """
    await callback.answer()


@router.callback_query(F.data == "experts_back")
async def experts_back(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Кнопка "Назад" в разделе экспертов:
    - удаляем сообщение с фото
    - возвращаемся на экран, с которого зашли (academy, start и т.п.)
    """
    data = await state.get_data()
    prev_screen = data.get("experts_prev_screen") or "academy"

    # 1) Удаляем сообщение с фото-каруселью
    try:
        await callback.message.delete()
    except Exception:
        pass

    # 2) Возвращаем предыдущий экран через общий навигатор
    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id=prev_screen,
        as_new_message=False,
        push_history=False,
    )

    await callback.answer()
