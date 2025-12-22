from aiogram.fsm.context import FSMContext
from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.navigation import show_screen
from app.schema.user import UserCreate
from app.services.users.service import get_or_create_user
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def kb_after_photos() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="go_start_new")],
        ]
    )


router = Router(name=__name__)

START_LOG_CHAT_ID = -5041400670


@router.message(CommandStart())
async def process_start_command(
    message: types.Message,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,  # <-- должно прокидываться через middleware
):
    # Если show_screen завязан на state и тебе нельзя clear — замени на set_state(None)
    await state.clear()

    tg_user = message.from_user
    if tg_user:
        payload = UserCreate(
            tg_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
        )
        await get_or_create_user(session, payload)

    # лог в чат
    parts: list[str] = ["🚀 Новый /start"]
    if tg_user:
        parts.append(f"ID: {tg_user.id}")
        name_bits = []
        if tg_user.first_name:
            name_bits.append(tg_user.first_name)
        if tg_user.last_name:
            name_bits.append(tg_user.last_name)
        if name_bits:
            parts.append("Имя: " + " ".join(name_bits))
        if tg_user.username:
            parts.append(f"Username: @{tg_user.username}")

    try:
        await bot.send_message(START_LOG_CHAT_ID, "\n".join(parts))
    except Exception:
        pass

    await show_screen(
        target=message,
        state=state,
        bot=bot,
        screen_id="start",
        as_new_message=True,
        push_history=False,
    )


@router.callback_query(F.data == "go_start_new")
async def go_start_new(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.delete()
    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id="start",
        as_new_message=True,
        push_history=False,
    )
    await callback.answer()


# @router.message(F.photo | F.document)
# async def catch_media_and_log_file_id(message: types.Message):
#     """
#     Ловим:
#     - фото → берём file_id последней (самой большой) версии
#     - документ с mime_type application/pdf → берём file_id документа

#     И выводим всё в print.
#     """
#     user = message.from_user
#     user_part = ""
#     if user:
#         user_bits = [f"ID: {user.id}"]
#         if user.username:
#             user_bits.append(f"@{user.username}")
#         name_bits = []
#         if user.first_name:
#             name_bits.append(user.first_name)
#         if user.last_name:
#             name_bits.append(user.last_name)
#         if name_bits:
#             user_bits.append(" ".join(name_bits))
#         user_part = " | ".join(user_bits)

#     # Фото
#     if message.photo:
#         file_id = message.photo[-1].file_id
#         print(
#             "🖼 Получено фото\n"
#             f"{user_part}\n"
#             f"file_id: {file_id}\n"
#             "----------------------"
#         )
#         return

#     # Документ (PDF)
#     if message.document and message.document.mime_type == "application/pdf":
#         file_id = message.document.file_id
#         file_name = message.document.file_name or "без имени"
#         print(
#             "📄 Получен PDF-документ\n"
#             f"{user_part}\n"
#             f"Название файла: {file_name}\n"
#             f"file_id: {file_id}\n"
#             "----------------------"
#         )
#         return


#@router.message(F.photo | F.document)
async def catch_media_and_log_file_id(message: types.Message, bot: Bot):
    """
    Ловим:
    - фото → берём file_id последней (самой большой) версии
    - документ с mime_type application/pdf → берём file_id документа

    И отправляем file_id в служебный чат START_LOG_CHAT_ID.
    """
    user = message.from_user
    user_part = ""
    if user:
        user_bits = [f"ID: {user.id}"]
        if user.username:
            user_bits.append(f"@{user.username}")
        name_bits = []
        if user.first_name:
            name_bits.append(user.first_name)
        if user.last_name:
            name_bits.append(user.last_name)
        if name_bits:
            user_bits.append(" ".join(name_bits))
        user_part = " | ".join(user_bits)

    # Фото
    if message.photo:
        file_id = message.photo[-1].file_id
        text = f"🖼 Получено фото\n{user_part}\nfile_id:\n<code>{file_id}</code>"
        try:
            await bot.send_message(START_LOG_CHAT_ID, text, parse_mode="HTML")
        except Exception:
            pass
        return

    # Документ (PDF)
    if message.document and message.document.mime_type == "application/pdf":
        file_id = message.document.file_id
        file_name = message.document.file_name or "без имени"
        text = (
            "📄 Получен PDF-документ\n"
            f"{user_part}\n"
            f"Название файла: {file_name}\n"
            f"file_id:\n<code>{file_id}</code>"
        )
        try:
            await bot.send_message(START_LOG_CHAT_ID, text, parse_mode="HTML")
        except Exception:
            pass
        return
