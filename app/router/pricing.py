# app/router/pricing.py

from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from app.lexicon import pricing as pricing_lexicon
from app.navigation import show_screen

router = Router()

# Описание тарифов: какой текст и какая ссылка
PRICING_PLANS = [
    {
        "key": "pricing_first_wave",
        "button_text": "Оплатить FIRST WAVE",
        "url": "https://gptsurfers.ai/#order:%D0%A2%D0%B0%D1%80%D0%B8%D1%84%20FIRST%20WAVE%20=35000",
    },
    {
        "key": "pricing_big_wave",
        "button_text": "Оплатить BIG WAVE",
        "url": "https://gptsurfers.ai/#order:%D0%A2%D0%B0%D1%80%D0%B8%D1%84%20BIG%20WAVE%20=45000",
    },
    {
        "key": "pricing_corporate",
        "button_text": "Оставить заявку",
        "url": "https://gptsurfers.ai/#popup:myform",
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

    keyboard = [
        [
            InlineKeyboardButton(
                text=plan["button_text"],
                url=plan["url"],
            )
        ],
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
    Собираем текст для страницы:
    - на первой странице: интро + FIRST WAVE
    - на остальных: только текст тарифа
    """
    intro = pricing_lexicon.TEXTS.get("pricing_intro", "")
    plan_key = PRICING_PLANS[index]["key"]
    plan_text = pricing_lexicon.TEXTS[plan_key]

    if index == 0 and intro:
        return f"{intro}\n\n{plan_text}"
    return plan_text


@router.callback_query(F.data == "pricing")
async def open_pricing(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Первый вход в раздел тарифов.
    Теперь: НЕ отправляем новое сообщение, а редактируем текущее.
    """
    data = await state.get_data()
    prev_screen = data.get("current_screen")  # откуда пришли (обычно 'academy')

    index = 0

    await state.update_data(
        pricing_index=index,
        pricing_prev_screen=prev_screen,
        current_screen="pricing",
    )

    text = get_pricing_text(index)

    # 🔴 Раньше здесь было answer(...) → новое сообщение
    # ✅ Теперь редактируем то же сообщение
    await callback.message.edit_text(
        text,
        reply_markup=build_pricing_keyboard(index),
    )

    await callback.answer()


@router.callback_query(F.data.in_(["pricing_prev", "pricing_next"]))
async def pricing_switch(callback: CallbackQuery, state: FSMContext):
    """
    Листаем тарифы по кругу:
      - на 3/3 вправо → 1/3
      - на 1/3 влево → 3/3
    """
    data = await state.get_data()
    index = data.get("pricing_index", 0)

    if callback.data == "pricing_next":
        index = (index + 1) % TOTAL_PLANS
    else:  # pricing_prev
        index = (index - 1) % TOTAL_PLANS

    await state.update_data(pricing_index=index)

    text = get_pricing_text(index)

    await callback.message.edit_text(
        text,
        reply_markup=build_pricing_keyboard(index),
    )

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
    - НЕ удаляем сообщение
    - просто возвращаем предыдущий экран, редактируя это же сообщение
    """
    data = await state.get_data()
    prev_screen = data.get("pricing_prev_screen") or "academy"

    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id=prev_screen,
        as_new_message=False,
        push_history=False,
    )

    await callback.answer()
