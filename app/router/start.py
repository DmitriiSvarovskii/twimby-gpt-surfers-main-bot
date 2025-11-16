from aiogram.fsm.context import FSMContext
from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram import Bot

from app.navigation import show_screen

router = Router(name=__name__)


@router.message(CommandStart())
async def process_start_command(message: types.Message, state: FSMContext, bot: Bot):

    await state.clear()

    await show_screen(
        target=message,
        state=state,
        bot=bot,
        screen_id="start",
        as_new_message=True,
        push_history=False,
    )


@router.message()
async def process_any_message(message: types.Message):
    # Если прислали документ (PDF и любые другие файлы)
    if message.document:
        await message.answer(
            f"📄 Документ\n"
            f"file_id:\n`{message.document.file_id}`\n\n"
            f"file_unique_id:\n`{message.document.file_unique_id}`",
            parse_mode="Markdown"
        )
        return

    # Если прислали фото (в Telegram фото → массив размеров)
    if message.photo:
        biggest = message.photo[-1]  # самое большое фото
        await message.answer(
            f"🖼 Фото\n"
            f"file_id:\n`{biggest.file_id}`\n\n"
            f"file_unique_id:\n`{biggest.file_unique_id}`",
            parse_mode="Markdown"
        )
        return

    # Просто текст
    await message.answer("Отправь фото или PDF, я верну file_id 🙂")
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
