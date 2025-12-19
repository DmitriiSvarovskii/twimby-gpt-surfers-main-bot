from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Импортируем модули с BUTTONS из пакета button
from . import (
    start,
    ai_testing,
    academy,
    # program_view,
    # experts,
    pricing,
    corporate,
    webinar,
    ask_question,
    lead_form,
    ai_photoshoot,
    jobs,
    social_network
)

# Собираем единый реестр кнопок
BUTTONS_REGISTRY = {}

for module in (
    start,
    ai_testing,
    academy,
    # program_view,
    # experts,
    pricing,
    corporate,
    webinar,
    ask_question,
    lead_form,
    ai_photoshoot,
    jobs,
    social_network,
):
    if hasattr(module, "BUTTONS"):
        BUTTONS_REGISTRY.update(module.BUTTONS)


def build_inline_kb(name: str) -> InlineKeyboardMarkup:
    """
    name — ключ в словаре BUTTONS.
    Пример: BUTTONS = {"start_main": [...]} -> build_inline_kb("start_main")
    Поддерживает:
      - текст + callback_data
      - текст + url
      - опциональный параметр "row" для размещения в одном ряду.
    """

    buttons_cfg = BUTTONS_REGISTRY.get(name)
    if not buttons_cfg:
        raise ValueError(f"No buttons config found for '{name}'")

    rows: dict[int, list[InlineKeyboardButton]] = {}

    for btn in buttons_cfg:
        text = btn["text"]

        if "callback" in btn:
            button = InlineKeyboardButton(
                text=text,
                callback_data=btn["callback"],
            )
        elif "url" in btn:
            button = InlineKeyboardButton(
                text=text,
                url=btn["url"],
            )
        else:
            raise ValueError(f"Button must have 'callback' or 'url': {btn}")

        row_index = btn.get("row")

        if row_index is None:
            # каждая кнопка в своём ряду, если row не указан
            row_index = max(rows.keys(), default=-1) + 1

        rows.setdefault(row_index, []).append(button)

    inline_rows = [rows[i] for i in sorted(rows.keys())]

    return InlineKeyboardMarkup(inline_keyboard=inline_rows)
