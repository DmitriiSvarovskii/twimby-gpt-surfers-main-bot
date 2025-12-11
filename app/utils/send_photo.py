from aiogram.types import FSInputFile
from aiogram.exceptions import TelegramBadRequest


async def send_photo_with_fallback(
    message,
    bot,
    file_id: str | None,
    file_path: str,
    caption: str,
    reply_markup=None
):
    """
    Пытаемся отправить фото по file_id.
    Если file_id невалидный → отправляем через путь (FSInputFile).
    """

    # 1. Попытка отправить по file_id
    if file_id:
        try:
            return await message.answer_photo(
                photo=file_id,
                caption=caption,
                reply_markup=reply_markup,
            )
        except TelegramBadRequest:
            pass  # Падаем на fallback

    # 2. Fallback — отправка через путь
    photo = FSInputFile(file_path)
    return await message.answer_photo(
        photo=photo,
        caption=caption,
        reply_markup=reply_markup,
    )
