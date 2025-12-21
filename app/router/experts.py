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
from aiogram.exceptions import TelegramBadRequest

from app.lexicon import experts as experts_lexicon
from app.navigation import show_screen

router = Router()

EXPERTS = [
    {"key": "expert_ilya", "photo": "app/static/expert/Илья_Шитов.jpg"},
    {"key": "expert_alexander", "photo": "app/static/expert/Александр_Масленников.jpg"},
    {"key": "expert_eduard", "photo": "app/static/expert/Эдуард_Эргашев.jpg"},
    {"key": "expert_mikhail", "photo": "app/static/expert/МИША.jpg"},
    {"key": "expert_maxim", "photo": "app/static/expert/МАКС.jpg"},
]

TOTAL_EXPERTS = len(EXPERTS)

router = Router()

EXPERTS = [
    {"key": "expert_ilya", "photo": "app/static/expert/Илья_Шитов.jpg"},
    {"key": "expert_alexander", "photo": "app/static/expert/Александр_Масленников.jpg"},
    {"key": "expert_eduard", "photo": "app/static/expert/Эдуард_Эргашев.jpg"},
    {"key": "expert_mikhail", "photo": "app/static/expert/МИША.jpg"},
    {"key": "expert_maxim", "photo": "app/static/expert/МАКС.jpg"},
]

TOTAL_EXPERTS = len(EXPERTS)


def build_experts_keyboard(index: int) -> InlineKeyboardMarkup:
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
    Новая логика:
    1) удаляем текущий экран (screen_message_id, если есть);
    2) отправляем отдельным сообщением интро-текст;
    3) отправляем карточку первого эксперта (фото + caption + стрелки);
    4) в state:
       - screen_message_id -> сообщение с карточкой эксперта
       - experts_intro_message_id -> сообщение с интро-текстом
       - experts_prev_screen -> откуда пришли.
    """

    data = await state.get_data()
    prev_screen = data.get("current_screen") or "start"
    screen_message_id = data.get("screen_message_id")
    chat_id = callback.message.chat.id

    # 1) удаляем старый "экран"
    if screen_message_id:
        try:
            await bot.delete_message(chat_id, screen_message_id)
        except Exception:
            pass

    # 2) отправляем интро-текст
    intro_text = experts_lexicon.TEXTS.get(
        "experts_intro",
        "Наше обучение создано менеджерами и фаундерами, которые прямо сейчас "
        "управляют командами, растят продукты и ежедневно используют ИИ как вторые мозги. "
        "Мы говорим на твоем языке, используя понятные определения, а не заумным и "
        "академическим языком, от которого хочется закрыть лекцию и уснуть.",
    )

    intro_msg = await callback.message.answer(intro_text)

    # 3) карточка первого эксперта
    index = 0
    expert_cfg = EXPERTS[index]
    text_key = expert_cfg["key"]
    caption = experts_lexicon.TEXTS[text_key]
    photo_path = expert_cfg["photo"]

    expert_msg = await callback.message.answer_photo(
        photo=FSInputFile(photo_path),
        caption=caption,
        reply_markup=build_experts_keyboard(index),
    )

    # 4) сохраняем состояние
    await state.update_data(
        experts_index=index,
        experts_prev_screen=prev_screen,
        current_screen="experts",
        screen_message_id=expert_msg.message_id,        # "экранное" сообщение = карточка
        experts_intro_message_id=intro_msg.message_id,  # отдельное сообщение с интро
    )

    await callback.answer()


@router.callback_query(F.data.in_(["experts_prev", "experts_next"]))
async def experts_switch(callback: CallbackQuery, state: FSMContext):
    """
    Листаем экспертов в пределах одного message_id (карточки).
    Интро-сообщение сверху не трогаем.
    """
    data = await state.get_data()
    index = data.get("experts_index", 0)

    if callback.data == "experts_next":
        index = (index + 1) % TOTAL_EXPERTS
    else:  # "experts_prev"
        index = (index - 1) % TOTAL_EXPERTS

    await state.update_data(experts_index=index)

    expert_cfg = EXPERTS[index]
    text_key = expert_cfg["key"]
    caption = experts_lexicon.TEXTS[text_key]
    photo = FSInputFile(expert_cfg["photo"])

    media = InputMediaPhoto(
        media=photo,
        caption=caption,
    )

    try:
        await callback.message.edit_media(
            media=media,
            reply_markup=build_experts_keyboard(index),
        )
    except TelegramBadRequest:
        # на всякий случай, если по какой-то причине не фото
        pass

    await callback.answer()


@router.callback_query(F.data == "experts_page_info")
async def experts_page_info(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "experts_back")
async def experts_back(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Назад:
    - удаляем интро-сообщение;
    - "экранное" сообщение (карточку эксперта) отдаём под управление show_screen,
      который перерисует его под предыдущий экран.
    """

    data = await state.get_data()
    prev_screen = data.get("experts_prev_screen") or "academy"
    intro_id = data.get("experts_intro_message_id")
    chat_id = callback.message.chat.id

    # удаляем интро-текст
    if intro_id:
        try:
            await bot.delete_message(chat_id, intro_id)
        except Exception:
            pass

    await state.update_data(experts_intro_message_id=None)

    # возвращаем предыдущий экран в концепции навигатора
    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id=prev_screen,
        as_new_message=False,   # редактируем карточку эксперта
        push_history=False,
    )

    await callback.answer()
