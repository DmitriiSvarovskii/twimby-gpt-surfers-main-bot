from aiogram.fsm.context import FSMContext
from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram import Bot

from app.navigation import show_screen

router = Router(name=__name__)


START_LOG_CHAT_ID = -5041400670   # id группы, куда шлём лог /start


@router.message(CommandStart())
async def process_start_command(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()

    user = message.from_user

    # Собираем текст для логирования
    parts: list[str] = ["🚀 Новый /start"]

    if user:
        parts.append(f"ID: {user.id}")

        # Имя и фамилия, если есть
        name_bits = []
        if user.first_name:
            name_bits.append(user.first_name)
        if user.last_name:
            name_bits.append(user.last_name)
        if name_bits:
            parts.append("Имя: " + " ".join(name_bits))

        # username, если есть
        if user.username:
            parts.append(f"Username: @{user.username}")

    log_text = "\n".join(parts)

    # Пытаемся отправить сообщение в группу
    try:
        await bot.send_message(START_LOG_CHAT_ID, log_text)
    except Exception:
        # Логгировать/проглотить — по желанию
        pass

    # Рисуем стартовый экран пользователю
    await show_screen(
        target=message,
        state=state,
        bot=bot,
        screen_id="start",
        as_new_message=True,
        push_history=False,
    )


@router.message(F.photo | F.document)
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

# @router.message()
# async def process_any_message(message: types.Message):
#     # Документ (PDF и т.п.)
#     if message.document:
#         await message.answer(
#             "📄 Документ\n"
#             f"file_id:\n{message.document.file_id}\n\n"
#             f"file_unique_id:\n{message.document.file_unique_id}"
#         )
#         return

#     # Фото
#     if message.photo:
#         biggest = message.photo[-1]  # самое большое по размеру
#         await message.answer(
#             "🖼 Фото\n"
#             f"file_id:\n{biggest.file_id}\n\n"
#             f"file_unique_id:\n{biggest.file_unique_id}"
#         )
#         return

#     await message.answer("Отправь фото или PDF, я верну file_id 🙂")
# @router.message(CommandStart())
# async def process_start_command(message: types.Message, state: FSMContext, bot: Bot):

#     # 1) Фото-обложка
#     photo = types.FSInputFile("app/static/start/surfers_main.jpg")
#     await message.answer_photo(
#         photo=photo,
#         caption=start_lexicon.TEXTS["start"],
#         reply_markup=None,   # можно без кнопок или с ними — как хочешь
#     )

#     # 2) Основной "экран" как текст + клавиатура
#     screen_msg = await message.answer(
#         start_lexicon.TEXTS["start"],
#         reply_markup=build_inline_kb("start"),
#     )

#     await state.update_data(
#         history=[],
#         current_screen="start",
#         screen_message_id=screen_msg.message_id,
#     )
