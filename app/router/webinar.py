# app/router/webinar_register.py

from aiogram import Router, F, Bot, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import StateFilter
from aiogram.types import (
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from app.config import settings

router = Router()


# ======= СТЕЙТЫ РЕГИСТРАЦИИ НА ВЕБИНАР =======

class WebinarRegisterStates(StatesGroup):
    waiting_name = State()
    waiting_nick = State()
    waiting_email = State()
    waiting_confirm = State()


# ======= СТАРТ РЕГИСТРАЦИИ (ИЗ КНОПОК 11/18 ДЕКАБРЯ) =======

@router.callback_query(F.data.in_(["webinar_18_register", "webinar_21_register"]))
async def webinar_register_start(callback: CallbackQuery, state: FSMContext):
    """
    Старт регистрации на вебинар.
    В callback.data лежит info, на какой именно вебинар:
    - webinar_18_register
    - webinar_21_register
    """

    # вытащим код вебинара
    if callback.data == "webinar_18_register":
        webinar_code = "18 декабря"
    else:
        webinar_code = "21 декабря"

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отменить")]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

    msg = await callback.message.answer(
        f"Регистрация на вебинар {webinar_code}.\n\nКак тебя зовут?",
        reply_markup=kb,
    )

    await state.update_data(
        webinar_flow_message_ids=[msg.message_id],
        webinar_code=webinar_code,
        webinar_name=None,
        webinar_nick=None,
        webinar_email=None,
    )

    await state.set_state(WebinarRegisterStates.waiting_name)
    await callback.answer()


# ======= ШАГ 1 — ИМЯ =======

@router.message(
    StateFilter(WebinarRegisterStates.waiting_name),
    F.text,
    F.text != "Отменить",
)
async def webinar_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    msg_ids: list[int] = data.get("webinar_flow_message_ids", []) or []
    msg_ids.append(message.message_id)

    await state.update_data(
        webinar_flow_message_ids=msg_ids,
        webinar_name=message.text.strip(),
    )

    msg = await message.answer("Укажи свой ник в Telegram (например, @username).")
    msg_ids.append(msg.message_id)

    await state.update_data(webinar_flow_message_ids=msg_ids)
    await state.set_state(WebinarRegisterStates.waiting_nick)


# ======= ШАГ 2 — НИК В TELEGRAM =======

@router.message(
    StateFilter(WebinarRegisterStates.waiting_nick),
    F.text,
    F.text != "Отменить",
)
async def webinar_nick(message: types.Message, state: FSMContext):
    data = await state.get_data()
    msg_ids: list[int] = data.get("webinar_flow_message_ids", []) or []
    msg_ids.append(message.message_id)

    await state.update_data(
        webinar_flow_message_ids=msg_ids,
        webinar_nick=message.text.strip(),
    )

    msg = await message.answer("Оставь, пожалуйста, свою почту.")
    msg_ids.append(msg.message_id)

    await state.update_data(webinar_flow_message_ids=msg_ids)
    await state.set_state(WebinarRegisterStates.waiting_email)


# ======= ШАГ 3 — EMAIL =======

@router.message(
    StateFilter(WebinarRegisterStates.waiting_email),
    F.text,
    F.text != "Отменить",
)
async def webinar_email(message: types.Message, state: FSMContext):
    data = await state.get_data()
    msg_ids: list[int] = data.get("webinar_flow_message_ids", []) or []
    msg_ids.append(message.message_id)

    await state.update_data(
        webinar_flow_message_ids=msg_ids,
        webinar_email=message.text.strip(),
    )

    data = await state.get_data()
    webinar_code = data.get("webinar_code", "-")
    name = data.get("webinar_name", "-")
    nick = data.get("webinar_nick", "-")
    email = data.get("webinar_email", "-")

    # убираем reply-клавиатуру
    tmp = await message.answer(
        "Сейчас покажу, как будет выглядеть твоя регистрация 👇",
        reply_markup=ReplyKeyboardRemove(),
    )
    msg_ids.append(tmp.message_id)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отправить заявку",
                    callback_data="webinar_submit",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Отменить",
                    callback_data="webinar_cancel_flow",
                )
            ],
        ]
    )

    confirm_text = (
        f"Проверь, всё ли верно:\n\n"
        f"• Вебинар: {webinar_code}\n"
        f"• Имя: {name}\n"
        f"• Ник в Telegram: {nick}\n"
        f"• Почта: {email}\n\n"
        "Если всё ок — нажми «Отправить заявку»."
    )

    confirm_msg = await message.answer(confirm_text, reply_markup=kb)
    msg_ids.append(confirm_msg.message_id)

    await state.update_data(webinar_flow_message_ids=msg_ids)
    await state.set_state(WebinarRegisterStates.waiting_confirm)


# ======= ПОДТВЕРЖДЕНИЕ (INLINE) =======
@router.callback_query(
    StateFilter(WebinarRegisterStates.waiting_confirm),
    F.data == "webinar_submit",
)
async def webinar_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    msg_ids: list[int] = data.get("webinar_flow_message_ids", []) or []
    msg_ids.append(callback.message.message_id)

    chat_id = callback.message.chat.id

    webinar_code = data.get("webinar_code", "-")
    name = data.get("webinar_name", "-")
    nick = data.get("webinar_nick", "-")
    email = data.get("webinar_email", "-")

    # 1. удаляем все сообщения сценария
    for mid in set(msg_ids):
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass

    # 2. алёрт пользователю
    await callback.answer(
        "Спасибо! Твоя заявка на вебинар отправлена. Мы свяжемся с тобой в Telegram.",
        show_alert=True,
    )

    # 3. отправляем заявку в админ-чат
    user = callback.from_user
    user_id = user.id if user else "-"

    if user and user.username:
        header = f"🎓 Новая заявка на вебинар от @{user.username}"
    elif user:
        header = f"🎓 Новая заявка на вебинар от пользователя (id: {user.id})"
    else:
        header = "🎓 Новая заявка на вебинар"

    parts = [
        header,
        "",
        f"ID пользователя: {user_id}",
        f"Вебинар: {webinar_code}",
        f"Имя: {name}",
        f"Ник в Telegram: {nick}",
        f"Email: {email}",
        "#вебинар",
    ]
    admin_text = "\n".join(parts)

    try:
        await bot.send_message(settings.ADMINT_CHAT, admin_text)
    except Exception:
        pass

    # 4. чистим данные
    await state.update_data(
        webinar_flow_message_ids=None,
        webinar_code=None,
        webinar_name=None,
        webinar_nick=None,
        webinar_email=None,
    )
    await state.set_state(None)


# ======= ОТМЕНА НА ЛЮБОМ ШАГЕ (ТЕКСТ «Отменить») =======

@router.message(
    StateFilter(
        WebinarRegisterStates.waiting_name,
        WebinarRegisterStates.waiting_nick,
        WebinarRegisterStates.waiting_email,
        WebinarRegisterStates.waiting_confirm,
    ),
    F.text == "Отменить",
)
async def webinar_cancel_text(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    msg_ids: list[int] = data.get("webinar_flow_message_ids", []) or []
    msg_ids.append(message.message_id)

    chat_id = message.chat.id

    for mid in set(msg_ids):
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass

    tmp = await message.answer(
        "Регистрация на вебинар отменена.",
        reply_markup=ReplyKeyboardRemove(),
    )
    try:
        await bot.delete_message(chat_id, tmp.message_id)
    except Exception:
        pass

    await state.update_data(
        webinar_flow_message_ids=None,
        webinar_code=None,
        webinar_name=None,
        webinar_nick=None,
        webinar_email=None,
    )
    await state.set_state(None)


# ======= ОТМЕНА С ЭКРАНА ПОДТВЕРЖДЕНИЯ (INLINE) =======

@router.callback_query(
    StateFilter(WebinarRegisterStates.waiting_confirm),
    F.data == "webinar_cancel_flow",
)
async def webinar_cancel_flow(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    msg_ids: list[int] = data.get("webinar_flow_message_ids", []) or []
    msg_ids.append(callback.message.message_id)

    chat_id = callback.message.chat.id

    for mid in set(msg_ids):
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass

    await callback.answer("Регистрация на вебинар отменена.", show_alert=True)

    await state.update_data(
        webinar_flow_message_ids=None,
        webinar_code=None,
        webinar_name=None,
        webinar_nick=None,
        webinar_email=None,
    )
    await state.set_state(None)
