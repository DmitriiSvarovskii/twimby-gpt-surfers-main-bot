from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Импортируем модули с BUTTONS
from . import (
    start,
    ai_testing,
    academy,
    pricing,
    corporate,
    webinar,
    ask_question,
    lead_form,
    ai_photoshoot,
    jobs,
    social_network,
)
from .admin import main as admin_main

from app.config import settings
# ===== РЕЕСТР ВСЕХ КНОПОК =====

BUTTONS_REGISTRY: dict[str, list[dict]] = {}

for module in (
    start,
    ai_testing,
    academy,
    pricing,
    corporate,
    webinar,
    ask_question,
    lead_form,
    ai_photoshoot,
    jobs,
    social_network,
    admin_main,
):
    if hasattr(module, "BUTTONS"):
        BUTTONS_REGISTRY.update(module.BUTTONS)


# ===== ФАБРИКА КЛАВИАТУР =====

def build_inline_kb(name: str, *, tg_id: int | None = None) -> InlineKeyboardMarkup:
    buttons_cfg = BUTTONS_REGISTRY.get(name)
    if not buttons_cfg:
        raise ValueError(f"No buttons config found for '{name}'")

    is_admin = tg_id is not None and tg_id in set(settings.ADMIN_TG_IDS)

    rows: dict[int, list[InlineKeyboardButton]] = {}

    for btn in buttons_cfg:
        # ✅ скрываем админские кнопки не-админам
        if btn.get("admin_only") and not is_admin:
            continue

        if "callback" in btn:
            button = InlineKeyboardButton(text=btn["text"], callback_data=btn["callback"])
        elif "url" in btn:
            button = InlineKeyboardButton(text=btn["text"], url=btn["url"])
        else:
            raise ValueError(f"Button must have 'callback' or 'url': {btn}")

        row_index = btn.get("row")
        if row_index is None:
            row_index = max(rows.keys(), default=-1) + 1

        rows.setdefault(row_index, []).append(button)

    inline_rows = [rows[i] for i in sorted(rows.keys())]
    return InlineKeyboardMarkup(inline_keyboard=inline_rows)
