from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Импорты всех модулей с BUTTONS
from app.button import (
    start,
    ai_testing,
    academy,
    program_view,
    experts,
    pricing,
    corporate,
    webinar,
    ask_question,
    lead_form,
    ai_photoshoot,
)
from app.config import settings

# Регистр всех кнопок из модулей
BUTTONS_REGISTRY = {}
BUTTONS_REGISTRY.update(start.BUTTONS)
BUTTONS_REGISTRY.update(ai_testing.BUTTONS)
BUTTONS_REGISTRY.update(academy.BUTTONS)
BUTTONS_REGISTRY.update(program_view.BUTTONS)
BUTTONS_REGISTRY.update(experts.BUTTONS)
BUTTONS_REGISTRY.update(pricing.BUTTONS)
BUTTONS_REGISTRY.update(corporate.BUTTONS)
BUTTONS_REGISTRY.update(webinar.BUTTONS)
BUTTONS_REGISTRY.update(ask_question.BUTTONS)
BUTTONS_REGISTRY.update(lead_form.BUTTONS)
BUTTONS_REGISTRY.update(ai_photoshoot.BUTTONS)


def build_inline_kb(name: str, *, tg_id: int | None = None) -> InlineKeyboardMarkup:
    """
    name — ключ в словаре BUTTONS (например: "start", "academy_about", ...)
    tg_id — telegram id пользователя (для фильтрации кнопок)
    """

    buttons_cfg = BUTTONS_REGISTRY.get(name)
    if not buttons_cfg:
        raise ValueError(f"No buttons config found for '{name}'")

    rows: dict[int, list[InlineKeyboardButton]] = {}

    for btn in buttons_cfg:
        cb = btn.get("callback")
        if btn.get("admin_only"):
            if tg_id is None or tg_id not in set(settings.ADMIN_TG_IDS):
                continue

        # Скрываем кнопку админки для не-админов
        if cb == "admin" and (tg_id is None or tg_id not in settings.ADMIN_TG_IDS):
            continue

        # создаём кнопку
        if "callback" in btn:
            button = InlineKeyboardButton(
                text=btn["text"],
                callback_data=btn["callback"],
            )
        elif "url" in btn:
            button = InlineKeyboardButton(
                text=btn["text"],
                url=btn["url"],
            )
        else:
            raise ValueError(f"Button must have 'callback' or 'url': {btn}")

        row_index = btn.get("row")
        if row_index is None:
            rows[len(rows)] = [button]
        else:
            rows.setdefault(row_index, []).append(button)

    inline_rows = [rows[i] for i in sorted(rows.keys())]
    return InlineKeyboardMarkup(inline_keyboard=inline_rows)
# def build_inline_kb(name: str) -> InlineKeyboardMarkup:
#     """
#     name — ключ в словаре BUTTONS (например: "start", "academy_about", "program_navigation" и т.п.)
#     """

#     buttons_cfg = BUTTONS_REGISTRY.get(name)
#     if not buttons_cfg:
#         raise ValueError(f"No buttons config found for '{name}'")

#     # Поддержка опционального поля "row" для размещения нескольких кнопок в один ряд
#     rows = {}

#     for btn in buttons_cfg:
#         # создаём сам InlineKeyboardButton
#         if "callback" in btn:
#             button = InlineKeyboardButton(
#                 text=btn["text"],
#                 callback_data=btn["callback"],
#             )
#         elif "url" in btn:
#             button = InlineKeyboardButton(
#                 text=btn["text"],
#                 url=btn["url"],
#             )
#         else:
#             raise ValueError(f"Button must have 'callback' or 'url': {btn}")

#         row_index = btn.get("row")  # можно не указывать — тогда каждая кнопка в своей строке
#         if row_index is None:
#             # каждая кнопка — отдельный ряд
#             rows[len(rows)] = [button]
#         else:
#             rows.setdefault(row_index, []).append(button)

#     # сортируем ряды по индексу
#     inline_rows = [rows[i] for i in sorted(rows.keys())]

#     return InlineKeyboardMarkup(inline_keyboard=inline_rows)
