from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def kb_after_photos() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Главное меню", callback_data="go_start_new")],
        ]
    )
