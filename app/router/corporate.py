from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
# app/router/corporate.py

from aiogram import Router, F, Bot, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import StateFilter
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

from app.lexicon import corporate as corporate_lexicon
from app.navigation import show_screen
from app.config import settings

from app.lexicon import corporate as corporate_lexicon
from app.navigation import show_screen

router = Router()

# file_id твоего PDF из лога
PDF_FILE_ID = "BQACAgIAAxkDAAOvaRnDXmncWZObZkJBSIQtDCIO4kIAAv2JAAId09BIuwd9l84WV0I2BA"


def build_corporate_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оставить заявку", callback_data="corporate_request")],
            [InlineKeyboardButton(text="Назад", callback_data="corporate_back")],
        ]
    )


@router.callback_query(F.data == "corporate")
async def open_corporate(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Переход в раздел 'Корпоративное обучение':
    - удаляем прошлый "экран" (если был)
    - отправляем документ по file_id + caption + клавиатуру
    """

    data = await state.get_data()
    prev_screen = data.get("current_screen")
    screen_message_id = data.get("screen_message_id")

    # 1. Удаляем предыдущее экранное сообщение, если оно было
    if screen_message_id is not None:
        try:
            await bot.delete_message(
                chat_id=callback.message.chat.id,
                message_id=screen_message_id,
            )
        except Exception:
            pass
        await state.update_data(screen_message_id=None)

    # 2. Отправляем документ по file_id с подписью и кнопками
    text = corporate_lexicon.TEXTS["corporate_main"]

    msg = await callback.message.answer_document(
        document=PDF_FILE_ID,
        caption=text,
        reply_markup=build_corporate_keyboard(),
    )

    # 3. Сохраняем id экранного сообщения
    await state.update_data(
        current_screen="corporate",
        corporate_prev_screen=prev_screen,
        screen_message_id=msg.message_id,
    )

    await callback.answer()


@router.callback_query(F.data == "corporate_back")
async def corporate_back(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Кнопка 'Назад':
    - удаляем сообщение с документом
    - возвращаемся на предыдущий экран
    """

    data = await state.get_data()
    prev_screen = data.get("corporate_prev_screen") or "academy"
    msg_id = data.get("screen_message_id")
    chat_id = callback.message.chat.id

    # 1. Удаляем сообщение с PDF
    if msg_id:
        try:
            await bot.delete_message(chat_id, msg_id)
        except Exception:
            pass

    await state.update_data(screen_message_id=None)

    # 2. Возвращаем предыдущий экран
    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id=prev_screen,
        as_new_message=False,
        push_history=False,
    )

    await callback.answer()


class CorporateRequestStates(StatesGroup):
    waiting_team_size = State()
    waiting_department = State()
    waiting_name = State()
    waiting_email = State()
    waiting_confirm = State()


@router.callback_query(F.data == "corporate_request")
async def corporate_request_start(callback: CallbackQuery, state: FSMContext):
    """
    Старт сценария заявки:
    задаём первый вопрос "Сколько человек в команде?"
    + reply-клава с 'Отменить'
    """

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отменить")]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

    msg = await callback.message.answer(
        "Сколько человек в команде?",
        reply_markup=kb,
    )

    await state.update_data(
        corp_flow_message_ids=[msg.message_id],
        corp_team_size=None,
        corp_department=None,
        corp_name=None,
        corp_email=None,
    )

    await state.set_state(CorporateRequestStates.waiting_team_size)
    await callback.answer()


# ---- шаг 1: сколько человек ----

@router.message(
    StateFilter(CorporateRequestStates.waiting_team_size),
    F.text,
    F.text != "Отменить",
)
async def corporate_team_size(message: types.Message, state: FSMContext):
    data = await state.get_data()
    msg_ids: list[int] = data.get("corp_flow_message_ids", []) or []
    msg_ids.append(message.message_id)

    await state.update_data(
        corp_flow_message_ids=msg_ids,
        corp_team_size=message.text,
    )

    msg = await message.answer("Какая сфера / отдел?")
    msg_ids.append(msg.message_id)

    await state.update_data(corp_flow_message_ids=msg_ids)

    await state.set_state(CorporateRequestStates.waiting_department)


# ---- шаг 2: сфера / отдел ----

@router.message(
    StateFilter(CorporateRequestStates.waiting_department),
    F.text,
    F.text != "Отменить",
)
async def corporate_department(message: types.Message, state: FSMContext):
    data = await state.get_data()
    msg_ids: list[int] = data.get("corp_flow_message_ids", []) or []
    msg_ids.append(message.message_id)

    await state.update_data(
        corp_flow_message_ids=msg_ids,
        corp_department=message.text,
    )

    msg = await message.answer("Как тебя зовут?")
    msg_ids.append(msg.message_id)

    await state.update_data(corp_flow_message_ids=msg_ids)

    await state.set_state(CorporateRequestStates.waiting_name)


# ---- шаг 3: имя ----

@router.message(
    StateFilter(CorporateRequestStates.waiting_name),
    F.text,
    F.text != "Отменить",
)
async def corporate_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    msg_ids: list[int] = data.get("corp_flow_message_ids", []) or []
    msg_ids.append(message.message_id)

    await state.update_data(
        corp_flow_message_ids=msg_ids,
        corp_name=message.text,
    )

    msg = await message.answer("Укажи, пожалуйста, email.")
    msg_ids.append(msg.message_id)

    await state.update_data(corp_flow_message_ids=msg_ids)

    await state.set_state(CorporateRequestStates.waiting_email)


# ---- шаг 4: email ----

@router.message(
    StateFilter(CorporateRequestStates.waiting_email),
    F.text,
    F.text != "Отменить",
)
async def corporate_email(message: types.Message, state: FSMContext):
    data = await state.get_data()
    msg_ids: list[int] = data.get("corp_flow_message_ids", []) or []
    msg_ids.append(message.message_id)

    await state.update_data(
        corp_flow_message_ids=msg_ids,
        corp_email=message.text,
    )

    data = await state.get_data()
    team = data.get("corp_team_size", "-")
    dept = data.get("corp_department", "-")
    name = data.get("corp_name", "-")
    email = data.get("corp_email", "-")

    # сначала убираем reply-клавиатуру
    tmp = await message.answer(
        "Сейчас покажу сводку твоей заявки 👇",
        reply_markup=ReplyKeyboardRemove(),
    )
    msg_ids.append(tmp.message_id)

    # инлайн-клавиатура подтверждения
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Оставить заявку на корпоративный пакет",
                    callback_data="corporate_submit",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Отменить",
                    callback_data="corporate_cancel_flow",
                )
            ],
        ]
    )

    confirm_text = (
        "Проверь, всё ли верно:\n\n"
        f"• Сколько человек в команде: {team}\n"
        f"• Сфера / отдел: {dept}\n"
        f"• Имя: {name}\n"
        f"• Email: {email}\n\n"
        "Если всё ок — нажми «Оставить заявку на корпоративный пакет»."
    )

    confirm_msg = await message.answer(confirm_text, reply_markup=kb)
    msg_ids.append(confirm_msg.message_id)

    await state.update_data(corp_flow_message_ids=msg_ids)

    await state.set_state(CorporateRequestStates.waiting_confirm)


# ---- подтверждение заявки (inline + show_alert) ----

@router.callback_query(
    StateFilter(CorporateRequestStates.waiting_confirm),
    F.data == "corporate_submit",
)
async def corporate_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    msg_ids: list[int] = data.get("corp_flow_message_ids", []) or []
    # добавим текущее сообщение с кнопками на всякий
    msg_ids.append(callback.message.message_id)

    chat_id = callback.message.chat.id

    team = data.get("corp_team_size", "-")
    dept = data.get("corp_department", "-")
    name = data.get("corp_name", "-")
    email = data.get("corp_email", "-")

    # 1. удаляем все сообщения сценария
    for mid in set(msg_ids):
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass

    # 2. алёрт пользователю
    thanks_text = "Спасибо! Мы с вами свяжемся в Telegram в ближайшее время"
    await callback.answer(thanks_text, show_alert=True)

    # 3. отправляем заявку в админ-чат
    user = callback.from_user
    if user and user.username:
        header = f"💸 💸 💸 \nНовая #заявка на корпоративное обучение от @{user.username}"
    elif user:
        header = f"💸 💸 💸 \nНовая #заявка на корпоративное обучение от пользователя (id: {user.id})"
    else:
        header = "💸 💸 💸 \nНовая #заявка на корпоративное обучение"

    parts = [
        header,
        "",
        f"Сколько человек в команде: {team}",
        f"Сфера / отдел: {dept}",
        f"Имя: {name}",
        f"Email: {email}",
    ]

    admin_text = "\n".join(parts)

    try:
        await bot.send_message(settings.ADMINT_CHAT, admin_text)
    except Exception:
        pass

    # 4. чистим временные данные и выходим из FSM
    await state.update_data(
        corp_flow_message_ids=None,
        corp_team_size=None,
        corp_department=None,
        corp_name=None,
        corp_email=None,
    )
    await state.set_state(None)


# ---- отмена на любом шаге (текстовая) ----

@router.message(
    StateFilter(
        CorporateRequestStates.waiting_team_size,
        CorporateRequestStates.waiting_department,
        CorporateRequestStates.waiting_name,
        CorporateRequestStates.waiting_email,
        CorporateRequestStates.waiting_confirm,
    ),
    F.text == "Отменить",
)
async def corporate_cancel(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    msg_ids: list[int] = data.get("corp_flow_message_ids", []) or []
    msg_ids.append(message.message_id)

    chat_id = message.chat.id

    for mid in set(msg_ids):
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass

    tmp = await message.answer(
        "Заявка отменена",
        reply_markup=ReplyKeyboardRemove(),
    )
    try:
        await bot.delete_message(chat_id, tmp.message_id)
    except Exception:
        pass

    await state.update_data(
        corp_flow_message_ids=None,
        corp_team_size=None,
        corp_department=None,
        corp_name=None,
        corp_email=None,
    )
    await state.set_state(None)


# ---- отмена на этапе подтверждения (inline) ----

@router.callback_query(
    StateFilter(CorporateRequestStates.waiting_confirm),
    F.data == "corporate_cancel_flow",
)
async def corporate_cancel_flow(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    msg_ids: list[int] = data.get("corp_flow_message_ids", []) or []
    msg_ids.append(callback.message.message_id)

    chat_id = callback.message.chat.id

    for mid in set(msg_ids):
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass

    await callback.answer("Заявка отменена", show_alert=True)

    await state.update_data(
        corp_flow_message_ids=None,
        corp_team_size=None,
        corp_department=None,
        corp_name=None,
        corp_email=None,
    )
    await state.set_state(None)
