from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime


def kb_cancel_webinar_create() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="webinar:create_cancel")]
    ])


def kb_confirm_webinar_create() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Сохранить", callback_data="webinar:create_save"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="webinar:create_cancel"),
        ]
    ])


def kb_webinars_list(webinars: list[tuple[int, datetime, bool]]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="➕ Создать новый вебинар", callback_data="webinar:create")]]

    for wid, date_stream, is_active in webinars:
        suffix = "" if is_active else " (архив)"
        rows.append([
            InlineKeyboardButton(
                text=f"{fmt_date_ru(date_stream)}{suffix}",
                callback_data=f"webinar:edit:{wid}",
            )
        ])

    rows.append([InlineKeyboardButton(text="Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
# def kb_webinars_list(webinars: list[tuple[int, str]]) -> InlineKeyboardMarkup:
#     rows = [[InlineKeyboardButton(text="➕ Создать новый вебинар", callback_data="webinar:create")]]
#     for wid, date_stream in webinars:
#         rows.append([InlineKeyboardButton(text=fmt_date_ru(date_stream), callback_data=f"webinar:edit:{wid}")])
#     rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
#     return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_webinar_view(wid: int, is_active: bool) -> InlineKeyboardMarkup:
    toggle_text = "🔴 Деактивировать" if is_active else "🟢 Активировать"
    toggle_cb = f"webinar:toggle:{wid}"

    rows = [
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"webinar:edit_fields:{wid}")],
        [InlineKeyboardButton(text=toggle_text, callback_data=toggle_cb)],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="webinar:back_to_list")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_webinar_edit_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="webinar:edit_cancel")]
    ])


def kb_webinar_edit_confirm(wid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Сохранить", callback_data=f"webinar:edit_save:{wid}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="webinar:edit_cancel")],
    ])


MONTHS_RU = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}


def fmt_date_ru(dt: datetime) -> str:
    return f"{dt.day} {MONTHS_RU[dt.month]}"
