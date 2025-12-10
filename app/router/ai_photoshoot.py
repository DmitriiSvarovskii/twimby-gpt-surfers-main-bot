from aiogram.types import InputMediaPhoto
from aiogram import Router, F, Bot, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import StateFilter
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
)

from app.lexicon import ai_photoshoot as ai_photoshoot_lexicon
from app.navigation import show_screen

router = Router()

# Фото для первого экрана (описание бота)
INTRO_PHOTO_ID = "AgACAgUAAxkBAAMnaRoif3SN9uyct6n3NdJ1Q0_tmwkAAiYLaxsVstBUI-TPIvqyyigBAAMCAAN5AAM2BA"

# Фото для экрана с требованиями к загружаемым фото
REQUIREMENTS_PHOTO_ID = "AgACAgUAAxkBAAMlaRoiMe_sNGlBWFUVePfrOUaVy7QAAiULaxsVstBUv3f10q0BwSMBAAMCAAN5AAM2BA"

# Примеры сгенерированных фото (условный итоговый пак)
SAMPLE_PHOTO_IDS = [
    "AgACAgUAAxkBAAMTaRohWNyn_rtI63s08HpNzpaNx8gAAiQLaxsVstBUdC1aN5QO8bUBAAMCAAN5AAM2BA",
    "AgACAgUAAxkBAAMTaRohWNyn_rtI63s08HpNzpaNx8gAAiQLaxsVstBUdC1aN5QO8bUBAAMCAAN5AAM2BA",
    "AgACAgUAAxkBAAMTaRohWNyn_rtI63s08HpNzpaNx8gAAiQLaxsVstBUdC1aN5QO8bUBAAMCAAN5AAM2BA",
    "AgACAgUAAxkBAAMTaRohWNyn_rtI63s08HpNzpaNx8gAAiQLaxsVstBUdC1aN5QO8bUBAAMCAAN5AAM2BA",
    "AgACAgUAAxkBAAMTaRohWNyn_rtI63s08HpNzpaNx8gAAiQLaxsVstBUdC1aN5QO8bUBAAMCAAN5AAM2BA",
]


class AIPhotoshootStates(StatesGroup):
    choosing_category = State()
    choosing_gender = State()
    waiting_for_photos = State()
    waiting_bonus_choice = State()


# Категории: код → человеко-читаемое название
CATEGORIES = {
    "winter": "❄️ Зимняя сказка",
    "surf": "🏄‍♂️ Серфинг",
    "animals": "🐾 Фотосессия с животными",
    "travel": "✈️ Путешествия",
    "business": "💼 Деловой стиль",
}


def build_categories_keyboard() -> InlineKeyboardMarkup:
    """
    Кнопки по 2 в ряд + отмена.
    """
    kb_rows = [
        [
            InlineKeyboardButton(text=CATEGORIES["winter"], callback_data="ai_cat_winter"),
            InlineKeyboardButton(text=CATEGORIES["surf"], callback_data="ai_cat_surf"),
        ],
        [
            InlineKeyboardButton(text=CATEGORIES["animals"], callback_data="ai_cat_animals"),
            InlineKeyboardButton(text=CATEGORIES["travel"], callback_data="ai_cat_travel"),
        ],
        [
            InlineKeyboardButton(text=CATEGORIES["business"], callback_data="ai_cat_business"),
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить фотосессию",
                callback_data="ai_ps_cancel_flow",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb_rows)


def build_gender_keyboard() -> InlineKeyboardMarkup:
    """
    Только два пола, без «не важно» + возможность отмены.
    """
    kb_rows = [
        [
            InlineKeyboardButton(text="👩 Я девушка", callback_data="ai_gender_female"),
            InlineKeyboardButton(text="👨 Я мужчина", callback_data="ai_gender_male"),
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Назад к категориям",
                callback_data="ai_back_to_categories",
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить фотосессию",
                callback_data="ai_ps_cancel_flow",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb_rows)


def build_bonus_keyboard() -> InlineKeyboardMarkup:
    """
    После "пак сгенерирован" — оффер на доп.пак / покупку генераций.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Получить ещё 1 пак за подписку",
                    callback_data="ai_bonus_pack",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Купить дополнительные генерации",
                    callback_data="ai_buy_generations",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Вернуться в меню",
                    callback_data="ai_ps_back_to_menu",
                )
            ],
        ]
    )


# ================== СТАРТ СЦЕНАРИЯ ИИ-ФОТОСЕССИИ ==================


@router.callback_query(F.data == "ai_photoshoot")
async def ai_photoshoot_start(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Старт:
    1) Удаляем текущий экран.
    2) Отправляем ОДНО фото с описанием бота (INTRO_PHOTO_ID).
    3) Отправляем отдельное сообщение с выбором категорий.
    """
    await callback.answer("Данный раздел в разработке, скоро будет доступен ☺️", show_alert=True)
    # data = await state.get_data()
    # prev_screen = data.get("current_screen") or "start"
    # screen_message_id = data.get("screen_message_id")
    # chat_id = callback.message.chat.id

    # # Удаляем прошлый "экран"
    # if screen_message_id:
    #     try:
    #         await bot.delete_message(chat_id, screen_message_id)
    #     except Exception:
    #         pass

    # intro_caption = (
    #     "Загрузи свои фото — и выбери категорию съёмки: зимняя сказка, серфинг, "
    #     "фотосессия с животными, путешествия, деловой.\n"
    #     "Через несколько минут получишь серию реалистичных снимков.\n\n"
    #     "В боте ежемесячно доступно 5 направлений фотосессии. "
    #     "Они меняются ежемесячно исходя из трендов и не только."
    # )

    # # Фото-обложка с описанием
    # intro_msg = await callback.message.answer_photo(
    #     photo=INTRO_PHOTO_ID,
    #     caption=intro_caption,
    # )

    # # Под фото — сообщение с выбором категории
    # categories_msg = await callback.message.answer(
    #     "Выбери категорию ИИ-фотосессии:",
    #     reply_markup=build_categories_keyboard(),
    # )

    # flow_ids = [intro_msg.message_id, categories_msg.message_id]

    # await state.update_data(
    #     ai_prev_screen=prev_screen,
    #     current_screen="ai_photoshoot",
    #     screen_message_id=categories_msg.message_id,
    #     ai_flow_message_ids=flow_ids,
    #     ai_category=None,
    #     ai_gender=None,
    #     ai_user_photos=[],
    # )

    # await state.set_state(AIPhotoshootStates.choosing_category)
    # await callback.answer()


# ================== ВЫБОР КАТЕГОРИИ ==================


@router.callback_query(
    StateFilter(AIPhotoshootStates.choosing_category),
    F.data.startswith("ai_cat_"),
)
async def ai_choose_category(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    msg_ids: list[int] = data.get("ai_flow_message_ids", []) or []
    msg_ids.append(callback.message.message_id)

    cat_code = callback.data.removeprefix("ai_cat_")
    cat_title = CATEGORIES.get(cat_code, "выбранная категория")

    await state.update_data(
        ai_flow_message_ids=msg_ids,
        ai_category=cat_code,
    )

    text = (
        f"Отличный выбор: *{cat_title}*.\n\n"
        "Теперь выбери, пожалуйста, твой пол — это поможет сделать "
        "результат более реалистичным."
    )

    await bot.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        text=text,
        reply_markup=build_gender_keyboard(),
        parse_mode="Markdown",
    )

    await state.set_state(AIPhotoshootStates.choosing_gender)
    await callback.answer()


@router.callback_query(
    StateFilter(AIPhotoshootStates.choosing_gender),
    F.data == "ai_back_to_categories",
)
async def ai_back_to_categories(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Возврат к выбору категории из шага выбора пола.
    """
    data = await state.get_data()
    msg_ids: list[int] = data.get("ai_flow_message_ids", []) or []
    msg_ids.append(callback.message.message_id)

    intro_text = ai_photoshoot_lexicon.TEXTS.get(
        "ai_photoshoot_intro_short",
        "Выбери категорию ИИ-фотосессии:",
    )

    await bot.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        text=intro_text,
        reply_markup=build_categories_keyboard(),
    )

    await state.update_data(
        ai_flow_message_ids=msg_ids,
        ai_category=None,
        ai_gender=None,
    )

    await state.set_state(AIPhotoshootStates.choosing_category)
    await callback.answer()


# ================== ВЫБОР ПОЛА ==================


@router.callback_query(
    StateFilter(AIPhotoshootStates.choosing_gender),
    F.data.startswith("ai_gender_"),
)
async def ai_choose_gender(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    После выбора пола:
    - убираем инлайн-клавиатуру,
    - отправляем ОДНО фото с требованиями (REQUIREMENTS_PHOTO_ID),
      caption = текст требований,
    - отправляем текст + reply-клаву "Отменить фотосессию".
    """
    data = await state.get_data()
    msg_ids: list[int] = data.get("ai_flow_message_ids", []) or []
    msg_ids.append(callback.message.message_id)

    gender_code = callback.data.removeprefix("ai_gender_")
    await state.update_data(
        ai_flow_message_ids=msg_ids,
        ai_gender=gender_code,
    )

    requirements_text = ai_photoshoot_lexicon.TEXTS.get(
        "ai_photos_requirements",
        "Чтобы фото получилось реалистичным, пожалуйста, загрузи качественные снимки лица.\n\n"
        "Вот требования:\n"
        "• Крупный план, чтобы лицо было хорошо видно.\n"
        "• Без фильтров и ретуши.\n"
        "• Хорошее освещение, без сильных теней.\n"
        "• Без очков, кепок, масок и волос, закрывающих лицо.\n\n"
        "Когда будешь готов — отправь фото сюда.",
    )

    # Убираем инлайн-клавиатуру
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    # Фото с требованиями
    req_msg = await callback.message.answer_photo(
        photo=REQUIREMENTS_PHOTO_ID,
        caption=requirements_text,
    )
    msg_ids.append(req_msg.message_id)

    # Сообщение с инструкцией + reply-клава "Отменить фотосессию"
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отменить фотосессию")]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

    helper_msg = await callback.message.answer(
        "Когда будешь готов — просто отправь сюда одно или несколько фото.\n"
        "Если передумаешь, нажми «Отменить фотосессию».",
        reply_markup=kb,
    )
    msg_ids.append(helper_msg.message_id)

    await state.update_data(ai_flow_message_ids=msg_ids)

    await state.set_state(AIPhotoshootStates.waiting_for_photos)
    await callback.answer()


# ================== ПОЛУЧЕНИЕ ФОТО ==================


# @router.message(
#     StateFilter(AIPhotoshootStates.waiting_for_photos),
#     F.photo,
# )
# async def ai_receive_photo(message: types.Message, state: FSMContext):
#     """
#     Пользователь отправил фото.
#     Пока что:
#     - сохраняем file_id,
#     - говорим, что "генерируем",
#     - отправляем медиагруппу SAMPLE_PHOTO_IDS как условный результат,
#     - отправляем текст с бонус-опциями.
#     """
#     data = await state.get_data()
#     msg_ids: list[int] = data.get("ai_flow_message_ids", []) or []
#     user_photos: list[str] = data.get("ai_user_photos", []) or []

#     msg_ids.append(message.message_id)

#     biggest_photo = max(message.photo, key=lambda p: p.width * p.height)
#     user_photos.append(biggest_photo.file_id)

#     await state.update_data(
#         ai_flow_message_ids=msg_ids,
#         ai_user_photos=user_photos,
#     )

#     cat_code = data.get("ai_category")
#     cat_title = CATEGORIES.get(cat_code, "выбранная категория")

#     generating_text = (
#         "Супер! Начинаю подготовку твоей ИИ-фотосессии 📸\n\n"
#         f"Тема: *{cat_title}*\n"
#         "Сейчас на основе твоих фото будет сгенерировано 5 снимков."
#     )

#     gen_msg = await message.answer(
#         generating_text,
#         parse_mode="Markdown",
#     )
#     msg_ids.append(gen_msg.message_id)

#     # Отправляем медиагруппу условно сгенерированных фото
#     media = [InputMediaPhoto(media=file_id) for file_id in SAMPLE_PHOTO_IDS]
#     album_msgs = await message.answer_media_group(media)
#     for m in album_msgs:
#         msg_ids.append(m.message_id)

#     done_text = (
#         "Готово! 🎉\n\n"
#         "Пак из 5 фото по выбранной теме условно сгенерирован.\n"
#         "Дальше мы предложим дополнительные опции:\n"
#         "— получить ещё 1 пак за выполнение простых действий,\n"
#         "— приобрести дополнительные генерации."
#     )

#     done_msg = await message.answer(
#         done_text,
#         reply_markup=build_bonus_keyboard(),
#     )
#     msg_ids.append(done_msg.message_id)

#     await state.update_data(ai_flow_message_ids=msg_ids)
#     await state.set_state(AIPhotoshootStates.waiting_bonus_choice)

@router.message(
    StateFilter(AIPhotoshootStates.waiting_for_photos),
    F.photo,
)
async def ai_receive_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    msg_ids: list[int] = data.get("ai_flow_message_ids", []) or []
    user_photos: list[str] = data.get("ai_user_photos", []) or []

    msg_ids.append(message.message_id)

    biggest_photo = max(message.photo, key=lambda p: p.width * p.height)
    user_photos.append(biggest_photo.file_id)

    await state.update_data(
        ai_flow_message_ids=msg_ids,
        ai_user_photos=user_photos,
    )

    cat_code = data.get("ai_category")
    cat_title = CATEGORIES.get(cat_code, "выбранная категория")

    generating_text = (
        "Супер! Начинаю подготовку твоей ИИ-фотосессии 📸\n\n"
        f"Тема: *{cat_title}*\n"
        "Сейчас на основе твоих фото будет сгенерировано 5 снимков."
    )

    gen_msg = await message.answer(
        generating_text,
        parse_mode="Markdown",
    )
    msg_ids.append(gen_msg.message_id)

    # 👉 Отправляем медиагруппу, но НЕ добавляем её message_id в msg_ids
    media = [InputMediaPhoto(media=file_id) for file_id in SAMPLE_PHOTO_IDS]
    await message.answer_media_group(media)

    done_text = (
        "Готово! 🎉\n\n"
        "Пак из 5 фото по выбранной теме условно сгенерирован.\n"
        "Дальше мы предложим дополнительные опции:\n"
        "— получить ещё 1 пак за выполнение простых действий,\n"
        "— приобрести дополнительные генерации."
    )

    done_msg = await message.answer(
        done_text,
        reply_markup=build_bonus_keyboard(),
    )
    msg_ids.append(done_msg.message_id)

    await state.update_data(ai_flow_message_ids=msg_ids)
    await state.set_state(AIPhotoshootStates.waiting_bonus_choice)
# ================== ДОП.ОПЦИИ ПОСЛЕ ПЕРВОГО ПАКА ==================


@router.callback_query(
    StateFilter(AIPhotoshootStates.waiting_bonus_choice),
    F.data == "ai_bonus_pack",
)
async def ai_bonus_pack(callback: CallbackQuery, state: FSMContext):
    await callback.answer(
        "Здесь позже появится сценарий получения доп.паков "
        "за подписку/действия 🙌",
        show_alert=True,
    )


@router.callback_query(
    StateFilter(AIPhotoshootStates.waiting_bonus_choice),
    F.data == "ai_buy_generations",
)
async def ai_buy_generations(callback: CallbackQuery, state: FSMContext):
    await callback.answer(
        "Здесь позже появится логика оплаты дополнительных генераций 💳",
        show_alert=True,
    )


@router.callback_query(
    StateFilter(AIPhotoshootStates.waiting_bonus_choice),
    F.data == "ai_ps_back_to_menu",
)
async def ai_ps_back_to_menu(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    msg_ids: list[int] = data.get("ai_flow_message_ids", []) or []
    msg_ids.append(callback.message.message_id)

    chat_id = callback.message.chat.id

    for mid in set(msg_ids):
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass

    prev_screen = data.get("ai_prev_screen") or "start"

    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id=prev_screen,
        as_new_message=True,
        push_history=False,
    )

    await state.update_data(
        ai_flow_message_ids=None,
        ai_category=None,
        ai_gender=None,
        ai_user_photos=None,
        ai_prev_screen=None,
    )
    await state.set_state(None)
    await callback.answer()


# ================== ОТМЕНА НА ЛЮБОМ ШАГЕ ==================


@router.message(
    StateFilter(
        AIPhotoshootStates.choosing_category,
        AIPhotoshootStates.choosing_gender,
        AIPhotoshootStates.waiting_for_photos,
        AIPhotoshootStates.waiting_bonus_choice,
    ),
    F.text == "Отменить фотосессию",
)
async def ai_ps_cancel_by_text(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    msg_ids: list[int] = data.get("ai_flow_message_ids", []) or []
    msg_ids.append(message.message_id)

    chat_id = message.chat.id

    for mid in set(msg_ids):
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass

    prev_screen = data.get("ai_prev_screen") or "start"

    tmp = await message.answer(
        "ИИ-фотосессия отменена",
        reply_markup=ReplyKeyboardRemove(),
    )
    try:
        await bot.delete_message(chat_id, tmp.message_id)
    except Exception:
        pass

    await show_screen(
        target=message,
        state=state,
        bot=bot,
        screen_id=prev_screen,
        as_new_message=True,
        push_history=False,
    )

    await state.update_data(
        ai_flow_message_ids=None,
        ai_category=None,
        ai_gender=None,
        ai_user_photos=None,
        ai_prev_screen=None,
    )
    await state.set_state(None)


@router.callback_query(
    StateFilter(
        AIPhotoshootStates.choosing_category,
        AIPhotoshootStates.choosing_gender,
        AIPhotoshootStates.waiting_for_photos,
        AIPhotoshootStates.waiting_bonus_choice,
    ),
    F.data == "ai_ps_cancel_flow",
)
async def ai_ps_cancel_by_inline(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    msg_ids: list[int] = data.get("ai_flow_message_ids", []) or []
    msg_ids.append(callback.message.message_id)

    chat_id = callback.message.chat.id

    for mid in set(msg_ids):
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass

    prev_screen = data.get("ai_prev_screen") or "start"

    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id=prev_screen,
        as_new_message=True,
        push_history=False,
    )

    await callback.answer("ИИ-фотосессия отменена", show_alert=True)

    await state.update_data(
        ai_flow_message_ids=None,
        ai_category=None,
        ai_gender=None,
        ai_user_photos=None,
        ai_prev_screen=None,
    )
    await state.set_state(None)
# app/router/ai_photoshoot.py

# from aiogram.types import InputMediaPhoto
# from aiogram import Router, F, Bot, types
# from aiogram.fsm.context import FSMContext
# from aiogram.fsm.state import StatesGroup, State
# from aiogram.filters import StateFilter
# from aiogram.types import (
#     CallbackQuery,
#     InlineKeyboardMarkup,
#     InlineKeyboardButton,
#     ReplyKeyboardMarkup,
#     ReplyKeyboardRemove,
#     KeyboardButton,
# )

# from app.lexicon import ai_photoshoot as ai_photoshoot_lexicon
# from app.navigation import show_screen

# router = Router()

# SAMPLE_PHOTO_IDS = [
#     "AgACAgUAAxkBAAMTaRohWNyn_rtI63s08HpNzpaNx8gAAiQLaxsVstBUdC1aN5QO8bUBAAMCAAN5AAM2BA",
#     "AgACAgUAAxkBAAMTaRohWNyn_rtI63s08HpNzpaNx8gAAiQLaxsVstBUdC1aN5QO8bUBAAMCAAN5AAM2BA",
#     "AgACAgUAAxkBAAMTaRohWNyn_rtI63s08HpNzpaNx8gAAiQLaxsVstBUdC1aN5QO8bUBAAMCAAN5AAM2BA",
#     "AgACAgUAAxkBAAMTaRohWNyn_rtI63s08HpNzpaNx8gAAiQLaxsVstBUdC1aN5QO8bUBAAMCAAN5AAM2BA",
#     "AgACAgUAAxkBAAMTaRohWNyn_rtI63s08HpNzpaNx8gAAiQLaxsVstBUdC1aN5QO8bUBAAMCAAN5AAM2BA",
# ]


# class AIPhotoshootStates(StatesGroup):
#     choosing_category = State()
#     choosing_gender = State()
#     waiting_for_photos = State()
#     waiting_bonus_choice = State()


# # Категории: код → человеко-читаемое название
# CATEGORIES = {
#     "winter": "❄️ Зимняя сказка",
#     "surf": "🏄‍♂️ Серфинг",
#     "animals": "🐾 Фотосессия с животными",
#     "travel": "✈️ Путешествия",
#     "business": "💼 Деловой стиль",
# }


# def build_categories_keyboard() -> InlineKeyboardMarkup:
#     """
#     Кнопки по 2 в ряд + отмена.
#     """
#     kb_rows = [
#         [
#             InlineKeyboardButton(text=CATEGORIES["winter"], callback_data="ai_cat_winter"),
#             InlineKeyboardButton(text=CATEGORIES["surf"], callback_data="ai_cat_surf"),
#         ],
#         [
#             InlineKeyboardButton(text=CATEGORIES["animals"], callback_data="ai_cat_animals"),
#             InlineKeyboardButton(text=CATEGORIES["travel"], callback_data="ai_cat_travel"),
#         ],
#         [
#             InlineKeyboardButton(text=CATEGORIES["business"], callback_data="ai_cat_business"),
#         ],
#         [
#             InlineKeyboardButton(
#                 text="❌ Отменить фотосессию",
#                 callback_data="ai_ps_cancel_flow",
#             )
#         ],
#     ]
#     return InlineKeyboardMarkup(inline_keyboard=kb_rows)


# def build_gender_keyboard() -> InlineKeyboardMarkup:
#     """
#     Только два пола, без «не важно» + возможность отмены.
#     """
#     kb_rows = [
#         [
#             InlineKeyboardButton(text="👩 Я девушка", callback_data="ai_gender_female"),
#             InlineKeyboardButton(text="👨 Я мужчина", callback_data="ai_gender_male"),
#         ],
#         [
#             InlineKeyboardButton(
#                 text="⬅️ Назад к категориям",
#                 callback_data="ai_back_to_categories",
#             )
#         ],
#         [
#             InlineKeyboardButton(
#                 text="❌ Отменить фотосессию",
#                 callback_data="ai_ps_cancel_flow",
#             )
#         ],
#     ]
#     return InlineKeyboardMarkup(inline_keyboard=kb_rows)


# def build_bonus_keyboard() -> InlineKeyboardMarkup:
#     """
#     После "пак сгенерирован" — оффер на доп.пак / покупку генераций.
#     """
#     return InlineKeyboardMarkup(
#         inline_keyboard=[
#             [
#                 InlineKeyboardButton(
#                     text="Получить ещё 1 пак за подписку",
#                     callback_data="ai_bonus_pack",
#                 )
#             ],
#             [
#                 InlineKeyboardButton(
#                     text="Купить дополнительные генерации",
#                     callback_data="ai_buy_generations",
#                 )
#             ],
#             [
#                 InlineKeyboardButton(
#                     text="Вернуться в меню",
#                     callback_data="ai_ps_back_to_menu",
#                 )
#             ],
#         ]
#     )


# # ================== СТАРТ СЦЕНАРИЯ ИИ-ФОТОСЕССИИ ==================


# @router.callback_query(F.data == "ai_photoshoot")
# async def ai_photoshoot_start(callback: CallbackQuery, state: FSMContext, bot: Bot):
#     """
#     1) Удаляем текущий экран.
#     2) Отправляем медиа-группу (5 фото) с описанием на первой фотке.
#     3) Отправляем отдельное сообщение с инлайн-клавиатурой категорий.
#     """
#     data = await state.get_data()
#     prev_screen = data.get("current_screen") or "start"
#     screen_message_id = data.get("screen_message_id")
#     chat_id = callback.message.chat.id

#     if screen_message_id:
#         try:
#             await bot.delete_message(chat_id, screen_message_id)
#         except Exception:
#             pass

#     intro_text = ai_photoshoot_lexicon.TEXTS.get(
#         "ai_photoshoot_intro",
#         "Привет! Я помогу тебе сделать ИИ-фотосессию за пару минут.\n\n"
#         "Загрузи свои фото — и выбери категорию съёмки: зимняя сказка, серфинг, "
#         "фотосессия с животными, путешествия, деловой.\n"
#         "Через несколько минут получишь серию реалистичных снимков.\n\n"
#         "В боте ежемесячно доступно 5 направлений фотосессии. "
#         "Они меняются ежемесячно исходя из трендов и не только.",
#     )

#     media = []
#     for i, file_id in enumerate(SAMPLE_PHOTO_IDS):
#         if i == 0:
#             media.append(
#                 InputMediaPhoto(
#                     media=file_id,
#                     caption=intro_text,
#                 )
#             )
#         else:
#             media.append(InputMediaPhoto(media=file_id))

#     album_messages = await callback.message.answer_media_group(media)

#     # под альбомом — сообщение с выбором категорий
#     categories_msg = await callback.message.answer(
#         "Выбери категорию ИИ-фотосессии:",
#         reply_markup=build_categories_keyboard(),
#     )

#     flow_ids = [m.message_id for m in album_messages]
#     flow_ids.append(categories_msg.message_id)

#     await state.update_data(
#         ai_prev_screen=prev_screen,
#         current_screen="ai_photoshoot",
#         screen_message_id=categories_msg.message_id,
#         ai_flow_message_ids=flow_ids,
#         ai_category=None,
#         ai_gender=None,
#         ai_user_photos=[],
#     )

#     await state.set_state(AIPhotoshootStates.choosing_category)
#     await callback.answer()


# # ================== ВЫБОР КАТЕГОРИИ ==================


# @router.callback_query(
#     StateFilter(AIPhotoshootStates.choosing_category),
#     F.data.startswith("ai_cat_"),
# )
# async def ai_choose_category(callback: CallbackQuery, state: FSMContext, bot: Bot):
#     data = await state.get_data()
#     msg_ids: list[int] = data.get("ai_flow_message_ids", []) or []
#     msg_ids.append(callback.message.message_id)

#     cat_code = callback.data.removeprefix("ai_cat_")
#     cat_title = CATEGORIES.get(cat_code, "выбранная категория")

#     await state.update_data(
#         ai_flow_message_ids=msg_ids,
#         ai_category=cat_code,
#     )

#     text = (
#         f"Отличный выбор: *{cat_title}*.\n\n"
#         "Теперь выбери, пожалуйста, твой пол — это поможет сделать "
#         "результат более реалистичным."
#     )

#     await bot.edit_message_text(
#         chat_id=callback.message.chat.id,
#         message_id=callback.message.message_id,
#         text=text,
#         reply_markup=build_gender_keyboard(),
#         parse_mode="Markdown",
#     )

#     await state.set_state(AIPhotoshootStates.choosing_gender)
#     await callback.answer()


# @router.callback_query(
#     StateFilter(AIPhotoshootStates.choosing_gender),
#     F.data == "ai_back_to_categories",
# )
# async def ai_back_to_categories(callback: CallbackQuery, state: FSMContext, bot: Bot):
#     """
#     Возврат к выбору категории из шага выбора пола.
#     """
#     data = await state.get_data()
#     msg_ids: list[int] = data.get("ai_flow_message_ids", []) or []
#     msg_ids.append(callback.message.message_id)

#     intro_text = ai_photoshoot_lexicon.TEXTS.get(
#         "ai_photoshoot_intro_short",
#         "Выбери категорию ИИ-фотосессии:",
#     )

#     await bot.edit_message_text(
#         chat_id=callback.message.chat.id,
#         message_id=callback.message.message_id,
#         text=intro_text,
#         reply_markup=build_categories_keyboard(),
#     )

#     await state.update_data(
#         ai_flow_message_ids=msg_ids,
#         ai_category=None,
#         ai_gender=None,
#     )

#     await state.set_state(AIPhotoshootStates.choosing_category)
#     await callback.answer()


# # ================== ВЫБОР ПОЛА ==================


# @router.callback_query(
#     StateFilter(AIPhotoshootStates.choosing_gender),
#     F.data.startswith("ai_gender_"),
# )
# async def ai_choose_gender(callback: CallbackQuery, state: FSMContext, bot: Bot):
#     data = await state.get_data()
#     msg_ids: list[int] = data.get("ai_flow_message_ids", []) or []
#     msg_ids.append(callback.message.message_id)

#     gender_code = callback.data.removeprefix("ai_gender_")
#     await state.update_data(
#         ai_flow_message_ids=msg_ids,
#         ai_gender=gender_code,
#     )

#     # Текст требований
#     requirements_text = ai_photoshoot_lexicon.TEXTS.get(
#         "ai_photos_requirements",
#         "Чтобы фото получилось реалистичным, пожалуйста, загрузи качественные снимки лица.\n\n"
#         "Вот требования:\n"
#         "• Крупный план, чтобы лицо было хорошо видно.\n"
#         "• Без фильтров и ретуши.\n"
#         "• Хорошее освещение, без сильных теней.\n"
#         "• Без очков, кепок, масок и волос, закрывающих лицо.\n\n"
#         "Когда будешь готов — отправь фото сюда.",
#     )

#     # убираем инлайн-клавиатуру, чтобы она не мешала
#     try:
#         await callback.message.edit_reply_markup(reply_markup=None)
#     except Exception:
#         pass

#     # Отправляем медиа-группу с теми же примерными фото, но уже с текстом требований
#     media = []
#     for i, file_id in enumerate(SAMPLE_PHOTO_IDS):
#         if i == 0:
#             media.append(
#                 InputMediaPhoto(
#                     media=file_id,
#                     caption=requirements_text,
#                 )
#             )
#         else:
#             media.append(InputMediaPhoto(media=file_id))

#     album_req = await callback.message.answer_media_group(media)
#     for m in album_req:
#         msg_ids.append(m.message_id)

#     # Отправляем сообщение с reply-клавой "Отменить фотосессию"
#     kb = ReplyKeyboardMarkup(
#         keyboard=[[KeyboardButton(text="Отменить фотосессию")]],
#         resize_keyboard=True,
#         one_time_keyboard=False,
#     )

#     helper_msg = await callback.message.answer(
#         "Когда будешь готов — просто отправь сюда одно или несколько фото.\n"
#         "Если передумаешь, нажми «Отменить фотосессию».",
#         reply_markup=kb,
#     )
#     msg_ids.append(helper_msg.message_id)

#     await state.update_data(ai_flow_message_ids=msg_ids)

#     await state.set_state(AIPhotoshootStates.waiting_for_photos)
#     await callback.answer()


# # ================== ПОЛУЧЕНИЕ ФОТО ==================


# @router.message(
#     StateFilter(AIPhotoshootStates.waiting_for_photos),
#     F.photo,
# )
# async def ai_receive_photo(message: types.Message, state: FSMContext):
#     """
#     Пользователь отправил фото.
#     Пока что просто сохраняем file_id и имитируем генерацию.
#     """
#     data = await state.get_data()
#     msg_ids: list[int] = data.get("ai_flow_message_ids", []) or []
#     user_photos: list[str] = data.get("ai_user_photos", []) or []

#     msg_ids.append(message.message_id)

#     # Берём самое большое фото из message.photo
#     biggest_photo = max(message.photo, key=lambda p: p.width * p.height)
#     user_photos.append(biggest_photo.file_id)

#     await state.update_data(
#         ai_flow_message_ids=msg_ids,
#         ai_user_photos=user_photos,
#     )

#     # Здесь будет ИИ-генерация (TODO: интеграция с API)
#     # Пока просто имитируем процесс
#     cat_code = data.get("ai_category")
#     cat_title = CATEGORIES.get(cat_code, "выбранная категория")

#     generating_text = (
#         "Супер! Начинаю подготовку твоей ИИ-фотосессии 📸\n\n"
#         f"Тема: *{cat_title}*\n"
#         "Сейчас на основе твоих фото будет сгенерировано 5 снимков."
#     )

#     gen_msg = await message.answer(
#         generating_text,
#         parse_mode="Markdown",
#     )
#     msg_ids.append(gen_msg.message_id)

#     # Здесь можно было бы отправить сами сгенерированные фото (по мере готовности)
#     # Сейчас просто имитируем завершение
#     done_text = (
#         "Готово! 🎉\n\n"
#         "Пак из 5 фото по выбранной теме условно сгенерирован.\n"
#         "Дальше мы предложим дополнительные опции:"
#         "\n— получить ещё 1 пак за выполнение простых действий,"
#         "\n— приобрести дополнительные генерации."
#     )

#     done_msg = await message.answer(
#         done_text,
#         reply_markup=build_bonus_keyboard(),
#     )
#     msg_ids.append(done_msg.message_id)

#     await state.update_data(ai_flow_message_ids=msg_ids)
#     await state.set_state(AIPhotoshootStates.waiting_bonus_choice)


# # ================== ДОП.ОПЦИИ ПОСЛЕ ПЕРВОГО ПАКА ==================


# @router.callback_query(
#     StateFilter(AIPhotoshootStates.waiting_bonus_choice),
#     F.data == "ai_bonus_pack",
# )
# async def ai_bonus_pack(callback: CallbackQuery, state: FSMContext):
#     """
#     Заглушка: еще 1 пак за подписку.
#     Здесь позже добавится логика проверок подписки.
#     """
#     await callback.answer(
#         "Здесь позже появится сценарий получения доп.паков "
#         "за подписку/действия 🙌",
#         show_alert=True,
#     )


# @router.callback_query(
#     StateFilter(AIPhotoshootStates.waiting_bonus_choice),
#     F.data == "ai_buy_generations",
# )
# async def ai_buy_generations(callback: CallbackQuery, state: FSMContext):
#     """
#     Заглушка: покупка генераций.
#     """
#     await callback.answer(
#         "Здесь позже появится логика оплаты дополнительных генераций 💳",
#         show_alert=True,
#     )


# @router.callback_query(
#     StateFilter(AIPhotoshootStates.waiting_bonus_choice),
#     F.data == "ai_ps_back_to_menu",
# )
# async def ai_ps_back_to_menu(callback: CallbackQuery, state: FSMContext, bot: Bot):
#     """
#     Завершение сценария и возвращение в основное меню.
#     """
#     data = await state.get_data()
#     msg_ids: list[int] = data.get("ai_flow_message_ids", []) or []
#     msg_ids.append(callback.message.message_id)

#     chat_id = callback.message.chat.id

#     # Удаляем все служебные сообщения сценария
#     for mid in set(msg_ids):
#         try:
#             await bot.delete_message(chat_id, mid)
#         except Exception:
#             pass

#     prev_screen = data.get("ai_prev_screen") or "start"

#     await show_screen(
#         target=callback,
#         state=state,
#         bot=bot,
#         screen_id=prev_screen,
#         as_new_message=True,
#         push_history=False,
#     )

#     await state.update_data(
#         ai_flow_message_ids=None,
#         ai_category=None,
#         ai_gender=None,
#         ai_user_photos=None,
#         ai_prev_screen=None,
#     )
#     await state.set_state(None)
#     await callback.answer()


# # ================== ОТМЕНА НА ЛЮБОМ ШАГЕ (ТЕКСТОМ) ==================

# @router.message(
#     StateFilter(
#         AIPhotoshootStates.choosing_category,
#         AIPhotoshootStates.choosing_gender,
#         AIPhotoshootStates.waiting_for_photos,
#         AIPhotoshootStates.waiting_bonus_choice,
#     ),
#     F.text == "Отменить фотосессию",
# )
# async def ai_ps_cancel_by_text(message: types.Message, state: FSMContext, bot: Bot):
#     data = await state.get_data()
#     msg_ids: list[int] = data.get("ai_flow_message_ids", []) or []
#     msg_ids.append(message.message_id)

#     chat_id = message.chat.id

#     for mid in set(msg_ids):
#         try:
#             await bot.delete_message(chat_id, mid)
#         except Exception:
#             pass

#     prev_screen = data.get("ai_prev_screen") or "start"

#     tmp = await message.answer(
#         "ИИ-фотосессия отменена",
#         reply_markup=ReplyKeyboardRemove(),
#     )
#     try:
#         await bot.delete_message(chat_id, tmp.message_id)
#     except Exception:
#         pass

#     await show_screen(
#         target=message,
#         state=state,
#         bot=bot,
#         screen_id=prev_screen,
#         as_new_message=True,
#         push_history=False,
#     )

#     await state.update_data(
#         ai_flow_message_ids=None,
#         ai_category=None,
#         ai_gender=None,
#         ai_user_photos=None,
#         ai_prev_screen=None,
#     )
#     await state.set_state(None)


# @router.callback_query(
#     StateFilter(
#         AIPhotoshootStates.choosing_category,
#         AIPhotoshootStates.choosing_gender,
#         AIPhotoshootStates.waiting_for_photos,
#         AIPhotoshootStates.waiting_bonus_choice,
#     ),
#     F.data == "ai_ps_cancel_flow",
# )
# async def ai_ps_cancel_by_inline(callback: CallbackQuery, state: FSMContext, bot: Bot):
#     data = await state.get_data()
#     msg_ids: list[int] = data.get("ai_flow_message_ids", []) or []
#     msg_ids.append(callback.message.message_id)

#     chat_id = callback.message.chat.id

#     for mid in set(msg_ids):
#         try:
#             await bot.delete_message(chat_id, mid)
#         except Exception:
#             pass

#     prev_screen = data.get("ai_prev_screen") or "start"

#     await show_screen(
#         target=callback,
#         state=state,
#         bot=bot,
#         screen_id=prev_screen,
#         as_new_message=True,
#         push_history=False,
#     )

#     await callback.answer("ИИ-фотосессия отменена", show_alert=True)

#     await state.update_data(
#         ai_flow_message_ids=None,
#         ai_category=None,
#         ai_gender=None,
#         ai_user_photos=None,
#         ai_prev_screen=None,
#     )
#     await state.set_state(None)
