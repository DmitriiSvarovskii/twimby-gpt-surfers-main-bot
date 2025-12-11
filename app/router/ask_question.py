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

from app.lexicon import ask_question as ask_question_lexicon
from app.config import settings
from app.navigation import show_screen

router = Router()


class AskQuestionStates(StatesGroup):
    waiting_for_question = State()
    waiting_for_contact_or_skip = State()
    waiting_confirm = State()


# ==== старт сценария по инлайн-кнопке "Задать вопрос" ====

@router.callback_query(F.data == "ask_question")
async def start_ask_question(callback: CallbackQuery, state: FSMContext):
    """
    1. Удаляем текущий экранное сообщение.
    2. Отправляем текст "Задай любой интересующий тебя вопрос..."
    3. Показываем reply-клаву "Отменить вопрос".
    4. Ждём текст вопроса.
    """
    # удаляем экранное сообщение
    try:
        await callback.message.delete()
    except Exception:
        pass

    # reply-клава только с отменой
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отменить вопрос")]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

    prompt_msg = await callback.message.answer(
        ask_question_lexicon.TEXTS["ask_question_intro"],
        reply_markup=kb,
    )

    # сохраняем id служебных сообщений сценария
    data = await state.get_data()
    await state.update_data(
        ask_flow_message_ids=[prompt_msg.message_id],
        ask_question_text=None,
        ask_contact_phone=None,
        ask_contact_first_name=None,
        ask_contact_last_name=None,
        # важно: экранное сообщение мы удалили
        screen_message_id=None,
        # current_screen оставляем как есть (start/academy/...), чтобы вернуться к нему
        current_screen=data.get("current_screen", "start"),
    )

    await state.set_state(AskQuestionStates.waiting_for_question)
    await callback.answer()


# ==== отмена через "Отменить вопрос" (на шагах вопрос/контакт) ====

@router.message(
    StateFilter(
        AskQuestionStates.waiting_for_question,
        AskQuestionStates.waiting_for_contact_or_skip,
    ),
    F.text == "Отменить вопрос",
)
async def cancel_question(message: types.Message, state: FSMContext, bot: Bot):
    """
    Отмена вопроса:
    - удаляем все сообщения сценария
    - убираем reply-клавиатуру
    - возвращаем экран, на котором пользователь был до сценария
    """
    data = await state.get_data()
    msg_ids: list[int] = data.get("ask_flow_message_ids", []) or []
    msg_ids.append(message.message_id)

    chat_id = message.chat.id

    # 1. Удаляем служебные сообщения сценария (подсказка, вопрос, доп. сообщения)
    for mid in set(msg_ids):
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass

    # 2. Убираем reply-клавиатуру (служебное сообщение, потом удаляем его)
    tmp = await message.answer(
        "Вопрос отменён",
        reply_markup=ReplyKeyboardRemove(),
    )
    try:
        await bot.delete_message(chat_id, tmp.message_id)
    except Exception:
        pass

    # 3. Возвращаем предыдущий экран с инлайн-клавиатурой
    prev_screen = data.get("current_screen") or "start"

    await show_screen(
        target=message,
        state=state,
        bot=bot,
        screen_id=prev_screen,
        as_new_message=True,
        push_history=False,
    )

    # 4. Чистим только данные сценария и выходим из FSM-состояния
    await state.update_data(
        ask_flow_message_ids=None,
        ask_question_text=None,
        ask_contact_phone=None,
        ask_contact_first_name=None,
        ask_contact_last_name=None,
    )
    await state.set_state(None)


# ==== пользователь прислал сам вопрос ====

@router.message(
    StateFilter(AskQuestionStates.waiting_for_question),
    F.text,
    F.text != "Отменить вопрос",
)
async def receive_question(message: types.Message, state: FSMContext, bot: Bot):
    """
    Получаем текст вопроса.
    Меняем клавиатуру у подсказки:
      [Пропустить] [Поделиться контактом(request_contact)]
      [Отменить вопрос]
    И ждём контакт или пропуск.
    """
    data = await state.get_data()
    msg_ids: list[int] = data.get("ask_flow_message_ids", []) or []

    # сохраняем id сообщения с вопросом, чтобы потом удалить
    msg_ids.append(message.message_id)

    # первая служебная подсказка
    prompt_id = msg_ids[0] if msg_ids else None

    # новая клава: Пропустить / Поделиться контактом / Отменить
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Пропустить"),
                KeyboardButton(text="Поделиться контактом", request_contact=True),
            ],
            [
                KeyboardButton(text="Отменить вопрос"),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

    # меняем клавиатуру у подсказки, текст оставляем тот же
    if prompt_id:
        try:
            await bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=prompt_id,
                reply_markup=kb,
            )
        except Exception:
            # если не получилось — просто отправим новое сообщение (на крайний случай)
            helper = await message.answer(
                "Можешь поделиться контактом, чтобы мы могли ответить:",
                reply_markup=kb,
            )
            msg_ids.append(helper.message_id)

    await state.update_data(
        ask_flow_message_ids=msg_ids,
        ask_question_text=message.text,
    )

    await state.set_state(AskQuestionStates.waiting_for_contact_or_skip)


# ==== helper: показ сводки + инлайн-кнопки отправки вопроса ====

async def _show_question_confirm(message: types.Message, state: FSMContext, with_contact: bool):
    data = await state.get_data()
    msg_ids: list[int] = data.get("ask_flow_message_ids", []) or []
    question_text: str | None = data.get("ask_question_text")

    # убираем reply-клавиатуру отдельным сообщением
    tmp = await message.answer(
        "Сейчас покажу сводку твоего вопроса 👇",
        reply_markup=ReplyKeyboardRemove(),
    )
    msg_ids.append(tmp.message_id)

    contact_block = "Контакт: не указан"
    if with_contact:
        phone = data.get("ask_contact_phone")
        fn = data.get("ask_contact_first_name")
        ln = data.get("ask_contact_last_name")
        fio = " ".join(filter(None, [fn, ln])).strip()
        if phone:
            contact_block = "Контакт:\n" + (f"{phone} {fio}".strip())

    text = "Проверь, всё ли верно:\n\n"
    text += "Текст вопроса:\n"
    text += (question_text or "—") + "\n\n"
    text += contact_block

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отправить вопрос",
                    callback_data="ask_submit",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Отменить",
                    callback_data="ask_cancel_flow",
                )
            ],
        ]
    )

    confirm_msg = await message.answer(text, reply_markup=kb)
    msg_ids.append(confirm_msg.message_id)

    await state.update_data(ask_flow_message_ids=msg_ids)
    await state.set_state(AskQuestionStates.waiting_confirm)


# ==== пользователь поделился контактом ====

@router.message(StateFilter(AskQuestionStates.waiting_for_contact_or_skip), F.contact)
async def receive_contact(message: types.Message, state: FSMContext, bot: Bot):
    """
    Пользователь нажал 'Поделиться контактом'.
    Сохраняем контакт в state и показываем сводку с инлайн-кнопками.
    """
    data = await state.get_data()
    msg_ids: list[int] = data.get("ask_flow_message_ids", []) or []
    msg_ids.append(message.message_id)

    contact = message.contact
    await state.update_data(
        ask_flow_message_ids=msg_ids,
        ask_contact_phone=contact.phone_number,
        ask_contact_first_name=contact.first_name,
        ask_contact_last_name=contact.last_name,
    )

    await _show_question_confirm(message, state, with_contact=True)


# ==== пользователь нажал "Пропустить" ====

@router.message(
    StateFilter(AskQuestionStates.waiting_for_contact_or_skip),
    F.text == "Пропустить",
)
async def skip_contact(message: types.Message, state: FSMContext, bot: Bot):
    """
    Пользователь не хочет оставлять контакт.
    Переходим к сводке и инлайн-кнопкам.
    """
    data = await state.get_data()
    msg_ids: list[int] = data.get("ask_flow_message_ids", []) or []
    msg_ids.append(message.message_id)

    # чистим возможный контакт
    await state.update_data(
        ask_flow_message_ids=msg_ids,
        ask_contact_phone=None,
        ask_contact_first_name=None,
        ask_contact_last_name=None,
    )

    await _show_question_confirm(message, state, with_contact=False)


# ==== подтверждение отправки вопроса (inline + show_alert) ====

@router.callback_query(
    StateFilter(AskQuestionStates.waiting_confirm),
    F.data == "ask_submit",
)
async def submit_question(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Пользователь подтвердил отправку вопроса.
    - удаляем все служебные сообщения
    - возвращаем предыдущий экран
    - шлём вопрос (и контакт) в админ-чат
    - показываем alert "Спасибо! ..."
    """
    data = await state.get_data()
    msg_ids: list[int] = data.get("ask_flow_message_ids", []) or []
    msg_ids.append(callback.message.message_id)

    chat_id = callback.message.chat.id

    question_text: str | None = data.get("ask_question_text")
    phone = data.get("ask_contact_phone")
    fn = data.get("ask_contact_first_name")
    ln = data.get("ask_contact_last_name")

    # 1. удаляем все сообщения сценария
    for mid in set(msg_ids):
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass

    # 2. восстанавливаем экран, с которого зашли
    prev_screen = data.get("current_screen") or "start"

    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id=prev_screen,
        as_new_message=True,
        push_history=False,
    )

    # 3. отправляем вопрос в админ-чат
    user = callback.from_user
    if user and user.username:
        header = f"❔❓\nНовый вопрос от пользователя @{user.username}"
    elif user:
        header = f"❔❓\nНовый вопрос от пользователя (id: {user.id})"
    else:
        header = "❔❓\nНовый вопрос от пользователя"

    parts = [header, ""]

    if question_text:
        parts.append("Текст вопроса:")
        parts.append(question_text)
        parts.append("")

    if phone:
        fio = " ".join(filter(None, [fn, ln])).strip()
        contact_block = f"{phone} {fio}".strip()
        parts.append("Контакт:")
        parts.append(contact_block)
    parts.append("#задать_вопрос")
    admin_text = "\n".join(parts) if parts else "Новый вопрос (данные не получены)"

    try:
        await bot.send_message(settings.ADMINT_CHAT, admin_text)
    except Exception as e:
        print(e)

    # 4. alert пользователю
    thanks_text = ask_question_lexicon.TEXTS.get(
        "ask_question_thanks",
        "Спасибо! Мы с вами свяжемся в Telegram в ближайшее время",
    )
    await callback.answer(thanks_text, show_alert=True)

    # 5. чистим данные сценария и FSM
    await state.update_data(
        ask_flow_message_ids=None,
        ask_question_text=None,
        ask_contact_phone=None,
        ask_contact_first_name=None,
        ask_contact_last_name=None,
    )
    await state.set_state(None)


# ==== отмена на этапе подтверждения (inline) ====

@router.callback_query(
    StateFilter(AskQuestionStates.waiting_confirm),
    F.data == "ask_cancel_flow",
)
async def cancel_flow_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Отмена после показа сводки:
    - удаляем служебные сообщения
    - возвращаем предыдущий экран
    - alert "Вопрос отменён"
    """
    data = await state.get_data()
    msg_ids: list[int] = data.get("ask_flow_message_ids", []) or []
    msg_ids.append(callback.message.message_id)

    chat_id = callback.message.chat.id

    for mid in set(msg_ids):
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass

    prev_screen = data.get("current_screen") or "start"

    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id=prev_screen,
        as_new_message=True,
        push_history=False,
    )

    await callback.answer("Вопрос отменён", show_alert=True)

    await state.update_data(
        ask_flow_message_ids=None,
        ask_question_text=None,
        ask_contact_phone=None,
        ask_contact_first_name=None,
        ask_contact_last_name=None,
    )
    await state.set_state(None)
# from aiogram import Router, F, Bot, types
# from aiogram.fsm.context import FSMContext
# from aiogram.fsm.state import StatesGroup, State
# from aiogram.filters import StateFilter
# from aiogram.types import (
#     CallbackQuery,
#     ReplyKeyboardMarkup,
#     KeyboardButton,
#     ReplyKeyboardRemove,
# )

# from app.lexicon import ask_question as ask_question_lexicon
# from app.button.factory import build_inline_kb
# from app.config import settings

# router = Router()


# class AskQuestionStates(StatesGroup):
#     waiting_for_question = State()
#     waiting_for_contact_or_skip = State()


# # ==== старт сценария по инлайн-кнопке "Задать вопрос" ====

# @router.callback_query(F.data == "ask_question")
# async def start_ask_question(callback: CallbackQuery, state: FSMContext):
#     """
#     1. Отправляем текст "Задай любой интересующий тебя вопрос..."
#     2. Показываем reply-клаву "Отменить вопрос"
#     3. Ждём текст вопроса
#     """
#     await callback.message.delete()
#     # reply-клава только с отменой
#     kb = ReplyKeyboardMarkup(
#         keyboard=[[KeyboardButton(text="Отменить вопрос")]],
#         resize_keyboard=True,
#         one_time_keyboard=False,
#     )

#     prompt_msg = await callback.message.answer(
#         ask_question_lexicon.TEXTS["ask_question_intro"],
#         reply_markup=kb,
#     )

#     # сохраняем id служебных сообщений сценария
#     await state.update_data(
#         ask_flow_message_ids=[prompt_msg.message_id],
#         ask_question_text=None,
#     )

#     await state.set_state(AskQuestionStates.waiting_for_question)
#     await callback.answer()


# @router.message(
#     StateFilter(
#         AskQuestionStates.waiting_for_question,
#         AskQuestionStates.waiting_for_contact_or_skip,
#     ),
#     F.text == "Отменить вопрос",
# )
# async def cancel_question(message: types.Message, state: FSMContext, bot: Bot):
#     """
#     Отмена вопроса:
#     - удаляем все сообщения сценария
#     - убираем reply-клавиатуру
#     - возвращаем экран, на котором пользователь был до сценария
#     """
#     data = await state.get_data()
#     msg_ids: list[int] = data.get("ask_flow_message_ids", []) or []
#     msg_ids.append(message.message_id)

#     chat_id = message.chat.id

#     # 1. Удаляем служебные сообщения сценария (подсказка, вопрос, доп. сообщения)
#     for mid in set(msg_ids):
#         try:
#             await bot.delete_message(chat_id, mid)
#         except Exception:
#             pass

#     # 2. Убираем reply-клавиатуру (служебное сообщение, потом удаляем его)
#     tmp = await message.answer(
#         "Вопрос отменён",
#         reply_markup=ReplyKeyboardRemove(),
#     )
#     try:
#         await bot.delete_message(chat_id, tmp.message_id)
#     except Exception:
#         pass

#     # 3. Возвращаем предыдущий экран с инлайн-клавиатурой
#     # current_screen мы до сценария менять не должны были, там 'start' / 'academy' и т.п.
#     prev_screen = data.get("current_screen") or "start"

#     from app.navigation import show_screen

#     await show_screen(
#         target=message,
#         state=state,
#         bot=bot,
#         screen_id=prev_screen,
#         as_new_message=True,   # рисуем новый экран, чтобы он был последним сообщением
#         push_history=False,    # не пушим в историю повторно
#     )

#     # 4. Чистим только данные сценария и выходим из FSM-состояния
#     await state.update_data(
#         ask_flow_message_ids=None,
#         ask_question_text=None,
#     )
#     await state.set_state(None)


# # ==== пользователь прислал сам вопрос ====

# @router.message(StateFilter(AskQuestionStates.waiting_for_question), F.text)
# async def receive_question(message: types.Message, state: FSMContext, bot: Bot):
#     """
#     Получаем текст вопроса.
#     Меняем клавиатуру у подсказки:
#       [Пропустить] [Поделиться контактом(request_contact)]
#       [Отменить вопрос]
#     И ждём контакт или пропуск.
#     """
#     data = await state.get_data()
#     msg_ids: list[int] = data.get("ask_flow_message_ids", []) or []

#     # сохраняем id сообщения с вопросом, чтобы потом удалить
#     msg_ids.append(message.message_id)

#     # первая служебная подсказка
#     prompt_id = msg_ids[0] if msg_ids else None

#     # новая клава: Пропустить / Поделиться контактом / Отменить
#     kb = ReplyKeyboardMarkup(
#         keyboard=[
#             [
#                 KeyboardButton(text="Пропустить"),
#                 KeyboardButton(text="Поделиться контактом", request_contact=True),
#             ],
#             [
#                 KeyboardButton(text="Отменить вопрос"),
#             ],
#         ],
#         resize_keyboard=True,
#         one_time_keyboard=False,
#     )

#     # меняем клавиатуру у подсказки, текст оставляем тот же
#     if prompt_id:
#         try:
#             await bot.edit_message_reply_markup(
#                 chat_id=message.chat.id,
#                 message_id=prompt_id,
#                 reply_markup=kb,
#             )
#         except Exception:
#             # если не получилось — просто отправим новое сообщение (на крайний случай)
#             helper = await message.answer(
#                 "Можешь поделиться контактом, чтобы мы могли ответить:",
#                 reply_markup=kb,
#             )
#             msg_ids.append(helper.message_id)

#     await state.update_data(
#         ask_flow_message_ids=msg_ids,
#         ask_question_text=message.text,
#     )

#     await state.set_state(AskQuestionStates.waiting_for_contact_or_skip)


# # ==== пользователь поделился контактом ====

# @router.message(StateFilter(AskQuestionStates.waiting_for_contact_or_skip), F.contact)
# async def receive_contact(message: types.Message, state: FSMContext, bot: Bot):
#     """
#     Пользователь нажал 'Поделиться контактом'.
#     Удаляем служебные сообщения, шлём 'Спасибо!' + инлайн-клаву start,
#     и отправляем вопрос+контакт в админ-чат.
#     """
#     data = await state.get_data()
#     msg_ids: list[int] = data.get("ask_flow_message_ids", []) or []
#     msg_ids.append(message.message_id)
#     question_text: str | None = data.get("ask_question_text")

#     chat_id = message.chat.id

#     # удаляем все служебные сообщения сценария
#     for mid in set(msg_ids):
#         try:
#             await bot.delete_message(chat_id, mid)
#         except Exception:
#             pass

#     # благодарность + инлайн-клавиатура (например, главное меню)
#     thanks_text = ask_question_lexicon.TEXTS.get(
#         "ask_question_thanks",
#         "Спасибо! Мы с вами свяжемся в Telegram в ближайшее время",
#     )

#     from app.button.factory import build_inline_kb  # чтобы не тащить наверх лишнее

#     thanks_msg = await message.answer(
#         thanks_text,
#         reply_markup=build_inline_kb("start"),
#     )

#     # отправляем вопрос и контакт в админ-чат
#     user = message.from_user
#     if user and user.username:
#         header = f"❔❓\nНовый #вопрос от пользователя @{user.username}"
#     elif user:
#         header = f"❔❓\nНовый #вопрос от пользователя (id: {user.id})"
#     else:
#         header = "❔❓\nНовый #вопрос от пользователя"

#     parts = [header]

#     if question_text:
#         parts.append("")
#         parts.append("Текст вопроса:")
#         parts.append(question_text)

#     if message.contact:
#         parts.append("")
#         parts.append("Контакт:")
#         contact = message.contact
#         fio = f"{contact.first_name or ''} {contact.last_name or ''}".strip()
#         parts.append(f"{contact.phone_number} {fio}".strip())

#     admin_text = "\n".join(parts)

#     try:
#         await bot.send_message(settings.ADMINT_CHAT, admin_text)
#     except Exception:
#         pass

#     # очищаем состояние и фиксируем новый экран как start
#     await state.clear()
#     await state.update_data(
#         current_screen="start",
#         screen_message_id=thanks_msg.message_id,
#         history=[],
#     )


# # ==== пользователь нажал "Пропустить" ====

# @router.message(StateFilter(AskQuestionStates.waiting_for_contact_or_skip), F.text == "Пропустить")
# async def skip_contact(message: types.Message, state: FSMContext, bot: Bot):
#     """
#     Пользователь не хочет оставлять контакт.
#     Удаляем служебные сообщения, шлём 'Спасибо!' + старт-клаву,
#     в админ-чат уходит вопрос без контакта.
#     """
#     data = await state.get_data()
#     msg_ids: list[int] = data.get("ask_flow_message_ids", []) or []
#     msg_ids.append(message.message_id)
#     question_text: str | None = data.get("ask_question_text")

#     chat_id = message.chat.id

#     # удаляем служебные сообщения
#     for mid in set(msg_ids):
#         try:
#             await bot.delete_message(chat_id, mid)
#         except Exception:
#             pass

#     thanks_text = ask_question_lexicon.TEXTS.get(
#         "ask_question_thanks",
#         "Спасибо! Мы с вами свяжемся в Telegram в ближайшее время",
#     )

#     from app.button.factory import build_inline_kb

#     thanks_msg = await message.answer(
#         thanks_text,
#         reply_markup=build_inline_kb("start"),
#     )

#     # отправляем вопрос в админ-чат без контакта
#     user = message.from_user
#     if user and user.username:
#         header = f"❔❓\nНовый #вопрос от пользователя @{user.username}"
#     elif user:
#         header = f"❔❓\nНовый #вопрос от пользователя (id: {user.id})"
#     else:
#         header = "❔❓\nНовый #вопрос от пользователя"

#     parts = [header]

#     if question_text:
#         parts.append("")
#         parts.append("Текст вопроса:")
#         parts.append(question_text)

#     admin_text = "\n".join(parts)

#     try:
#         await bot.send_message(settings.ADMINT_CHAT, admin_text)
#     except Exception:
#         pass

#     await state.clear()
#     await state.update_data(
#         current_screen="start",
#         screen_message_id=thanks_msg.message_id,
#         history=[],
#     )
