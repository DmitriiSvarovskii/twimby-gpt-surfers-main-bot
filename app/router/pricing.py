# app/router/pricing.py

from aiogram import Router, F, types, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    FSInputFile,
)

from app.lexicon import pricing as pricing_lexicon
from app.navigation import show_screen

router = Router()

PRICING_PHOTO_PATH = "app/static/pricing/pricing.png"

# Описание тарифов: какой текст и какая ссылка/коллбэк
PRICING_PLANS = [
    {
        "key": "pricing_first_wave",
        "button_text": "Оплатить FIRST WAVE",
        "url": "https://gptsurfers.ai/#tarif",
    },
    {
        "key": "pricing_big_wave",
        "button_text": "Оплатить BIG WAVE",
        "url": "https://gptsurfers.ai/#tarif",
    },
    {
        "key": "pricing_corporate",
        "button_text": "Оставить заявку",
        "callback": "corporate_request",  # <- тут именно callback
    },
]

TOTAL_PLANS = len(PRICING_PLANS)


def build_pricing_keyboard(index: int) -> InlineKeyboardMarkup:
    """
    Клавиатура:
    [Оплатить / Оставить заявку]
    [←   1/3   →]
    [Назад]
    """
    plan = PRICING_PLANS[index]
    center = f"{index + 1}/{TOTAL_PLANS}"

    # Кнопка действия: либо URL, либо callback_data
    if "url" in plan:
        action_button = InlineKeyboardButton(
            text=plan["button_text"],
            url=plan["url"],
        )
    else:
        action_button = InlineKeyboardButton(
            text=plan["button_text"],
            callback_data=plan["callback"],
        )

    keyboard = [
        [action_button],
        [
            InlineKeyboardButton(text="←", callback_data="pricing_prev"),
            InlineKeyboardButton(text=center, callback_data="pricing_page_info"),
            InlineKeyboardButton(text="→", callback_data="pricing_next"),
        ],
        [
            InlineKeyboardButton(text="Назад", callback_data="pricing_back"),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_pricing_text(index: int) -> str:
    """
    Текст именно тарифа (без интро).
    Интро теперь отдельным сообщением сверху.
    """
    plan_key = PRICING_PLANS[index]["key"]
    return pricing_lexicon.TEXTS[plan_key]


@router.callback_query(F.data == "pricing")
async def open_pricing(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Логика "как у экспертов":
    1) удаляем текущий экран (screen_message_id), если есть;
    2) отправляем отдельным сообщением интро-текст;
    3) отправляем фото с тарифами (одна картинка), caption = текст первого тарифа;
    4) в state:
       - screen_message_id -> сообщение с фото тарифов
       - pricing_intro_message_id -> сообщение с интро
       - pricing_prev_screen -> откуда пришли.
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

    # 2) интро-текст
    intro_text = pricing_lexicon.TEXTS.get(
        "pricing_intro",
        "Тарифы GPT Surfers:",
    )
    intro_msg = await callback.message.answer(intro_text)

    # 3) карточка первого тарифа
    index = 0
    caption = get_pricing_text(index)
    photo = FSInputFile(PRICING_PHOTO_PATH)

    tariff_msg = await callback.message.answer_photo(
        photo=photo,
        caption=caption,
        reply_markup=build_pricing_keyboard(index),
    )

    # 4) сохраняем состояние
    await state.update_data(
        pricing_index=index,
        pricing_prev_screen=prev_screen,
        current_screen="pricing",
        screen_message_id=tariff_msg.message_id,          # экран = фотка с тарифом
        pricing_intro_message_id=intro_msg.message_id,    # верхний текст
    )

    await callback.answer()


@router.callback_query(F.data.in_(["pricing_prev", "pricing_next"]))
async def pricing_switch(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Листаем тарифы по кругу:
      - на 3/3 вправо → 1/3
      - на 1/3 влево → 3/3
    Все страницы используют одно и то же фото, меняется только caption + клавиатура.
    """
    data = await state.get_data()
    index = data.get("pricing_index", 0)

    if callback.data == "pricing_next":
        index = (index + 1) % TOTAL_PLANS
    else:  # "pricing_prev"
        index = (index - 1) % TOTAL_PLANS

    await state.update_data(pricing_index=index)

    caption = get_pricing_text(index)

    try:
        # Нормальный сценарий — редактируем только caption и кнопки у фото
        await callback.message.edit_caption(
            caption=caption,
            reply_markup=build_pricing_keyboard(index),
        )
    except TelegramBadRequest:
        # На всякий пожарный: если вдруг сообщение не фото — пересоздадим экран
        chat_id = callback.message.chat.id
        photo = FSInputFile(PRICING_PHOTO_PATH)

        try:
            await bot.delete_message(chat_id, callback.message.message_id)
        except Exception:
            pass

        msg = await callback.message.answer_photo(
            photo=photo,
            caption=caption,
            reply_markup=build_pricing_keyboard(index),
        )

        await state.update_data(screen_message_id=msg.message_id)

    await callback.answer()


@router.callback_query(F.data == "pricing_page_info")
async def pricing_page_info(callback: CallbackQuery):
    """
    Средняя "кнопка" с индикатором 1/3 — неактивная.
    """
    await callback.answer()


@router.callback_query(F.data == "pricing_back")
async def pricing_back(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Кнопка "Назад" в тарифах:
    - удаляем интро-сообщение;
    - "экранное" сообщение (фото тарифа) отдаём под управление show_screen,
      который перерисует его под предыдущий экран.
    """
    data = await state.get_data()
    prev_screen = data.get("pricing_prev_screen") or "academy"
    intro_id = data.get("pricing_intro_message_id")
    chat_id = callback.message.chat.id

    # удаляем интро
    if intro_id:
        try:
            await bot.delete_message(chat_id, intro_id)
        except Exception:
            pass

    await state.update_data(pricing_intro_message_id=None)

    # возвращаемся на prev_screen через навигатор
    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id=prev_screen,
        as_new_message=False,
        push_history=False,
    )

    await callback.answer()
# # app/router/pricing.py

# from aiogram import Router, F, types, Bot
# from aiogram.exceptions import TelegramBadRequest
# from aiogram.fsm.context import FSMContext
# from aiogram.types import (
#     InlineKeyboardMarkup,
#     InlineKeyboardButton,
#     CallbackQuery,
#     FSInputFile,
# )

# from app.lexicon import pricing as pricing_lexicon
# from app.navigation import show_screen

# router = Router()

# PRICING_PHOTO_PATH = "app/static/pricing/pricing.png"

# # Описание тарифов: какой текст и какая ссылка
# PRICING_PLANS = [
#     {
#         "key": "pricing_first_wave",
#         "button_text": "Оплатить FIRST WAVE",
#         "url": "https://gptsurfers.ai/#tarif",
#     },
#     {
#         "key": "pricing_big_wave",
#         "button_text": "Оплатить BIG WAVE",
#         "url": "https://gptsurfers.ai/#tarif",
#     },
#     {
#         "key": "pricing_corporate",
#         "button_text": "Оставить заявку",
#         "callback": "corporate_request",
#     },
# ]

# TOTAL_PLANS = len(PRICING_PLANS)


# def build_pricing_keyboard(index: int) -> InlineKeyboardMarkup:
#     """
#     Клавиатура:
#     [Оплатить / Оставить заявку]
#     [←   1/3   →]
#     [Назад]
#     """
#     plan = PRICING_PLANS[index]
#     center = f"{index + 1}/{TOTAL_PLANS}"

#     keyboard = [
#         [
#             InlineKeyboardButton(
#                 text=plan["button_text"],
#                 url=plan["url"],
#             )
#         ],
#         [
#             InlineKeyboardButton(text="←", callback_data="pricing_prev"),
#             InlineKeyboardButton(text=center, callback_data="pricing_page_info"),
#             InlineKeyboardButton(text="→", callback_data="pricing_next"),
#         ],
#         [
#             InlineKeyboardButton(text="Назад", callback_data="pricing_back"),
#         ],
#     ]

#     return InlineKeyboardMarkup(inline_keyboard=keyboard)


# def get_pricing_text(index: int) -> str:
#     """
#     Собираем текст для страницы:
#     - на первой странице: интро + FIRST WAVE
#     - на остальных: только текст тарифа
#     """
#     intro = pricing_lexicon.TEXTS.get("pricing_intro", "")
#     plan_key = PRICING_PLANS[index]["key"]
#     plan_text = pricing_lexicon.TEXTS[plan_key]

#     if index == 0 and intro:
#         return f"{intro}\n\n{plan_text}"
#     return plan_text


# @router.callback_query(F.data == "pricing")
# async def open_pricing(callback: CallbackQuery, state: FSMContext, bot: Bot):
#     """
#     Первый вход в раздел тарифов:
#     - берём prev_screen из current_screen
#     - пытаемся превратить текущее экранное сообщение в фото с тарифом
#     - если редактирование медиа не удалось — удаляем старое экранное и шлём новое фото
#     - screen_message_id указывает на сообщение с фото тарифов
#     """
#     data = await state.get_data()
#     prev_screen = data.get("current_screen") or "start"
#     screen_message_id = data.get("screen_message_id")
#     chat_id = callback.message.chat.id

#     index = 0
#     text = get_pricing_text(index)
#     photo = FSInputFile(PRICING_PHOTO_PATH)

#     media = types.InputMediaPhoto(
#         media=photo,
#         caption=text,
#     )

#     msg_obj = None

#     if screen_message_id:
#         # пробуем заменить текущее "экранное" сообщение на фото с тарифом
#         try:
#             msg_obj = await bot.edit_message_media(
#                 chat_id=chat_id,
#                 message_id=screen_message_id,
#                 media=media,
#                 reply_markup=build_pricing_keyboard(index),
#             )
#         except TelegramBadRequest:
#             # например, там был чистый текст — удаляем и создаём новый экран
#             try:
#                 await bot.delete_message(chat_id, screen_message_id)
#             except Exception:
#                 pass

#             msg_obj = await callback.message.answer_photo(
#                 photo=photo,
#                 caption=text,
#                 reply_markup=build_pricing_keyboard(index),
#             )
#     else:
#         # экранного сообщения ещё нет — просто отправляем фото
#         msg_obj = await callback.message.answer_photo(
#             photo=photo,
#             caption=text,
#             reply_markup=build_pricing_keyboard(index),
#         )

#     await state.update_data(
#         pricing_index=index,
#         pricing_prev_screen=prev_screen,
#         current_screen="pricing",
#         screen_message_id=msg_obj.message_id,
#     )

#     await callback.answer()


# @router.callback_query(F.data.in_(["pricing_prev", "pricing_next"]))
# async def pricing_switch(callback: CallbackQuery, state: FSMContext, bot: Bot):
#     """
#     Листаем тарифы по кругу:
#       - на 3/3 вправо → 1/3
#       - на 1/3 влево → 3/3
#     Всегда одно и то же фото, меняется только caption + клавиатура.
#     """
#     data = await state.get_data()
#     index = data.get("pricing_index", 0)

#     if callback.data == "pricing_next":
#         index = (index + 1) % TOTAL_PLANS
#     else:  # pricing_prev
#         index = (index - 1) % TOTAL_PLANS

#     await state.update_data(pricing_index=index)

#     text = get_pricing_text(index)

#     try:
#         # в нормальном случае это фото → меняем только caption и кнопки
#         await callback.message.edit_caption(
#             caption=text,
#             reply_markup=build_pricing_keyboard(index),
#         )
#     except TelegramBadRequest:
#         # на всякий случай, если почему-то сообщение оказалось не фото — пересоздаём экран
#         chat_id = callback.message.chat.id
#         photo = FSInputFile(PRICING_PHOTO_PATH)

#         try:
#             await bot.delete_message(chat_id, callback.message.message_id)
#         except Exception:
#             pass

#         msg = await callback.message.answer_photo(
#             photo=photo,
#             caption=text,
#             reply_markup=build_pricing_keyboard(index),
#         )

#         await state.update_data(screen_message_id=msg.message_id)

#     await callback.answer()


# @router.callback_query(F.data == "pricing_page_info")
# async def pricing_page_info(callback: CallbackQuery):
#     """
#     Средняя "кнопка" с индикатором 1/3 — неактивная.
#     """
#     await callback.answer()


# @router.callback_query(F.data == "pricing_back")
# async def pricing_back(callback: CallbackQuery, state: FSMContext, bot: Bot):
#     """
#     Кнопка "Назад" в тарифах:
#     - ничего не удаляем руками
#     - просто возвращаемся на prev_screen через show_screen,
#       которое само аккуратно приведёт экран к нужному виду
#     """
#     data = await state.get_data()
#     prev_screen = data.get("pricing_prev_screen") or "academy"

#     await show_screen(
#         target=callback,
#         state=state,
#         bot=bot,
#         screen_id=prev_screen,
#         as_new_message=False,
#         push_history=False,
#     )

#     await callback.answer()
