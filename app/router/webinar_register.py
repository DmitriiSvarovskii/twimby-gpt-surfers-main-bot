from __future__ import annotations
from datetime import datetime, timezone
from app.services.webinars.cache import CachedWebinar
from aiogram.fsm.context import FSMContext


from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, InputMediaPhoto
from aiogram.exceptions import TelegramBadRequest

from app.db.redis_client import redis_client
from app.navigation import show_screen
from app.services.webinars.cache import get_upcoming_webinars

router = Router(name=__name__)

WEBINAR_PHOTO = "app/static/webinar/efiry.png"
NO_PHOTO = "app/static/expert/no_photo.png"


def _fmt_dt(dt) -> str:
    # отображаем в UTC (можешь поменять)
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%d.%m.%Y %H:%M UTC")


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


def _kb_webinar_list(webinars: list[CachedWebinar]) -> InlineKeyboardMarkup:
    rows = []
    for w in webinars:
        rows.append([InlineKeyboardButton(text=fmt_date_ru(w.date_stream), callback_data=f"webinar:open:{w.id}")])
    rows.append([InlineKeyboardButton(text="Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _kb_webinar_detail(webinar_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Зарегистрироваться", callback_data=f"webinar:register:{webinar_id}")],
            [InlineKeyboardButton(text="Назад", callback_data="webinar_main")],
        ]
    )


async def push_history(state: FSMContext, screen: str) -> None:
    data = await state.get_data()
    hist = list(data.get("history") or ["start"])
    if not hist or hist[-1] != screen:
        hist.append(screen)
        await state.update_data(history=hist)


@router.callback_query(F.data == "webinar_main")
async def webinar_main(callback: CallbackQuery, state, bot: Bot):
    chat_id = callback.message.chat.id
    message_id = callback.message.message_id

    webinars = await get_upcoming_webinars(redis_client)

    if not webinars:
        text = "Пока нет ближайших вебинаров 🙌"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data="back")]])
    else:
        parts = ["<b>Ближайшие вебинары:</b>\n"]
        for w in webinars:
            parts.append(f"<b>{w.title}</b>\n{w.description_small}\n")
        text = "\n".join(parts)
        kb = _kb_webinar_list(webinars)

    photo_path = WEBINAR_PHOTO if __import__("os").path.exists(WEBINAR_PHOTO) else NO_PHOTO

    # держим тот же “screen message”, который пришёл от show_screen
    try:
        await bot.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=InputMediaPhoto(media=FSInputFile(photo_path), caption=text, parse_mode="HTML"),
            reply_markup=kb,
        )
    except TelegramBadRequest:
        # если не редактируется — деградируем в caption
        try:
            await bot.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=text,
                reply_markup=kb,
                parse_mode="HTML",
            )
        except Exception:
            await bot.send_photo(chat_id, FSInputFile(photo_path), caption=text, reply_markup=kb, parse_mode="HTML")
    await push_history(state, "webinar_main")
    await callback.answer()


@router.callback_query(F.data.startswith("webinar:open:"))
async def webinar_open(callback: CallbackQuery, bot: Bot):
    chat_id = callback.message.chat.id
    message_id = callback.message.message_id

    webinar_id = int(callback.data.split(":")[-1])
    webinars = await get_upcoming_webinars(redis_client)
    w = next((x for x in webinars if x.id == webinar_id), None)

    if not w:
        await callback.answer("Вебинар не найден или уже прошёл", show_alert=True)
        return

    text = (
        f"<b>{w.title}</b>\n"
        # f"🗓 {_fmt_dt(w.date_stream)}\n\n"
        f"{w.description_full}"
    )

    kb = _kb_webinar_detail(webinar_id)

    # медиа не трогаем, меняем только caption + кнопки
    try:
        await bot.edit_message_caption(
            chat_id=chat_id,
            message_id=message_id,
            caption=text,
            reply_markup=kb,
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        await bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")

    await callback.answer()


@router.callback_query(F.data == "webinar_back")
async def webinar_back(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    # экран, с которого зашли в вебинары
    prev_screen = data.get("webinar_prev_screen")

    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id=prev_screen,
        as_new_message=False,
        push_history=False,
    )

    await callback.answer()
