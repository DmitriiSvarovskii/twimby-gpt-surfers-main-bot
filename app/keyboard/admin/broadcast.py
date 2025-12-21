from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, date
from zoneinfo import ZoneInfo
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.config.month import MONTHS_RU


def _today_berlin() -> date:
    return datetime.now(ZoneInfo("Europe/Berlin")).date()


def _as_date(dt) -> date | None:
    if dt is None:
        return None
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt
    if isinstance(dt, datetime):
        # если dt без tz — считаем локальным; если с tz — переводим в Berlin
        if dt.tzinfo is not None:
            dt = dt.astimezone(ZoneInfo("Europe/Berlin"))
        return dt.date()
    return None


def _format_ru_day_month(d: date) -> str:
    return f"{d.day} {MONTHS_RU[d.month]}"


def kb_webinars(items: list[tuple[int, str, object]]) -> InlineKeyboardMarkup:
    # items: [(webinar_id, title, date_stream), ...]
    today = _today_berlin()

    rows: list[list[InlineKeyboardButton]] = []
    for wid, title, dt in items:
        d = _as_date(dt)
        if d:
            label = _format_ru_day_month(d)
            if d < today:
                label += " (архив)"
        else:
            label = "Без даты"

        # если тебе НЕ нужен title на кнопке — замени text=label
        rows.append([InlineKeyboardButton(text=label, callback_data=f"bc:webinar:{wid}")])

    rows.append([InlineKeyboardButton(text="Назад", callback_data="bc:back_to_audience")])
    rows.append([InlineKeyboardButton(text="✖️ Отмена", callback_data="bc:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_broadcast_entry() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📣 Всем пользователям", callback_data="bc:all")],
        [InlineKeyboardButton(text="🎓 По вебинару", callback_data="bc:by_webinar")],
        [InlineKeyboardButton(text="✖️ Отмена", callback_data="bc:cancel")],
    ])


def kb_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✖️ Отмена", callback_data="bc:cancel")]
    ])


# def kb_webinars(items: list[tuple[int, str]]) -> InlineKeyboardMarkup:
#     # items: [(webinar_id, title), ...]
#     rows = [[InlineKeyboardButton(text=title, callback_data=f"bc:webinar:{wid}")]
#             for wid, title in items]
#     rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="bc:back_to_audience")])
#     rows.append([InlineKeyboardButton(text="✖️ Отмена", callback_data="bc:cancel")])
#     return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить тест в чат админов", callback_data="bc:send_test")],
        [InlineKeyboardButton(text="✖️ Отмена", callback_data="bc:cancel")],
    ])


def kb_start(recipients_count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🚀 Запустить рассылку по {recipients_count}", callback_data="bc:start")],
        [InlineKeyboardButton(text="✖️ Отмена", callback_data="bc:cancel")],
    ])
