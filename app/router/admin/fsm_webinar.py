from aiogram.utils.text_decorations import html_decoration
from aiogram import types
import re
from datetime import datetime, timezone

from aiogram import Router, F, Bot, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.utils.check_admin import is_admin
from app.navigation import show_screen
from app.model.webinar import Webinar
from app.fsm.admin import WebinarCreateStates
from app.keyboard.admin.webinars import (
    kb_webinars_list,
    kb_cancel_webinar_create,
    kb_confirm_webinar_create,
)
from app.services.webinars.cache import get_upcoming_webinars, refresh_webinars_cache, get_all_webinars_admin, refresh_webinars_cache_admin
from app.db.redis_client import redis_client


router = Router()

DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}$")

# -------------------------
# 1) Открыть список вебинаров
# -------------------------


@router.callback_query(F.data == "admin:webinars")
async def admin_webinars(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа ❌", show_alert=True)
        return

    webinars = await get_all_webinars_admin(redis_client)

    items = [(w["id"], w["date_stream"], w["is_active"]) for w in webinars]

    await show_screen(callback, state, bot, "admin_webinars", push_history=True)

    try:
        await callback.message.edit_reply_markup(reply_markup=kb_webinars_list(items))
    except Exception:
        pass

    await callback.answer()
# @router.callback_query(F.data == "admin:webinars")
# async def admin_webinars(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
#     if not is_admin(callback.from_user.id):
#         await callback.answer("Нет доступа ❌", show_alert=True)
#         return

#     upcoming = await get_all_webinars_admin(redis_client)  # только неархив
#     items = [(w.id, w.date_stream) for w in upcoming]

#     # Рисуем "окно" вебинаров через show_screen или вручную.
#     # Важно: у тебя show_screen уже умеет ставить фото/текст.
#     await show_screen(callback, state, bot, "admin_webinars", push_history=True)

#     # И поверх — меняем кнопки на динамические
#     try:
#         await callback.message.edit_reply_markup(reply_markup=kb_webinars_list(items))
#     except Exception:
#         pass

#     await callback.answer()


# -------------------------
# 2) Старт создания
# -------------------------
@router.callback_query(F.data == "webinar:create")
async def webinar_create_start(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа ❌", show_alert=True)
        return

    await state.set_state(WebinarCreateStates.title)

    msg = await callback.message.answer(
        "Введите <b>название</b> вебинара",
        reply_markup=kb_cancel_webinar_create(),
        parse_mode="HTML",
    )
    await track_webinar_ui_msg(state, msg)
    await callback.answer()


# -------------------------
# 3) Отмена (на любом шаге)
# -------------------------
@router.callback_query(F.data == "webinar:create_cancel")
async def webinar_create_cancel(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа ❌", show_alert=True)
        return

    await cleanup_webinar_ui(bot, state, chat_id=callback.message.chat.id)
    await state.clear()

    # возвращаемся на страницу вебинаров
    await show_screen(callback, state, bot, "admin_webinars", push_history=False)

    # кнопки снова динамически
    upcoming = await get_upcoming_webinars(redis_client)
    items = [(w.id, w.title) for w in upcoming]
    try:
        await callback.message.edit_reply_markup(reply_markup=kb_webinars_list(items))
    except Exception:
        pass

    await callback.answer("Отменено", show_alert=True)


# -------------------------
# 4) Ввод title
# -------------------------
@router.message(WebinarCreateStates.title)
async def webinar_create_title(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    # сохраняем HTML с разметкой
    title_html = text_with_entities_to_html(message.text or "", message.entities)

    await state.update_data(title=title_html)
    await state.set_state(WebinarCreateStates.description_small)

    await track_webinar_ui_msg(state, message)

    msg = await message.answer(
        "Введите <b>короткое описание</b>",
        reply_markup=kb_cancel_webinar_create(),
        parse_mode="HTML",
    )
    await track_webinar_ui_msg(state, msg)


# -------------------------
# 5) Ввод description_small
# -------------------------
@router.message(WebinarCreateStates.description_small)
async def webinar_create_desc_small(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    desc_html = text_with_entities_to_html(message.text or "", message.entities)

    await state.update_data(description_small=desc_html)
    await state.set_state(WebinarCreateStates.description_full)

    await track_webinar_ui_msg(state, message)

    msg = await message.answer(
        "Введите <b>полное описание</b>",
        reply_markup=kb_cancel_webinar_create(),
        parse_mode="HTML",
    )
    await track_webinar_ui_msg(state, msg)


# -------------------------
# 6) Ввод description_full
# -------------------------
@router.message(WebinarCreateStates.description_full)
async def webinar_create_desc_full(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    desc_html = text_with_entities_to_html(message.text or "", message.entities)

    await state.update_data(description_full=desc_html)
    await state.set_state(WebinarCreateStates.date)

    await track_webinar_ui_msg(state, message)

    msg = await message.answer(
        "Введите <b>дату</b> строго в формате <code>ДД.ММ.ГГГГ</code>\n"
        "Например: <code>24.07.2026</code>",
        reply_markup=kb_cancel_webinar_create(),
        parse_mode="HTML",
    )
    await track_webinar_ui_msg(state, msg)


# -------------------------
# 7) Ввод даты
# -------------------------
@router.message(WebinarCreateStates.date)
async def webinar_create_date(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    text = (message.text or "").strip()
    await track_webinar_ui_msg(state, message)

    if not DATE_RE.match(text):
        msg = await message.answer(
            "❌ Неверный формат. Нужно строго <code>ДД.ММ.ГГГГ</code>, например <code>24.07.2026</code>",
            reply_markup=kb_cancel_webinar_create(),
            parse_mode="HTML",
        )
        await track_webinar_ui_msg(state, msg)
        return

    await state.update_data(date_str=text)
    await state.set_state(WebinarCreateStates.time)

    msg = await message.answer(
        "Введите <b>время</b> строго в формате <code>ЧЧ:ММ</code>\n"
        "Например: <code>14:00</code>",
        reply_markup=kb_cancel_webinar_create(),
        parse_mode="HTML",
    )
    await track_webinar_ui_msg(state, msg)


# -------------------------
# 8) Ввод времени + превью
# -------------------------
@router.message(WebinarCreateStates.time)
async def webinar_create_time(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    text = (message.text or "").strip()
    await track_webinar_ui_msg(state, message)

    if not TIME_RE.match(text):
        msg = await message.answer(
            "❌ Неверный формат. Нужно строго <code>ЧЧ:ММ</code>, например <code>14:00</code>",
            reply_markup=kb_cancel_webinar_create(),
            parse_mode="HTML",
        )
        await track_webinar_ui_msg(state, msg)
        return

    data = await state.get_data()
    date_str = data["date_str"]

    # Собираем datetime (UTC). Если у тебя другой TZ — скажешь, поменяю.
    dt = datetime.strptime(f"{date_str} {text}", "%d.%m.%Y %H:%M").replace(tzinfo=timezone.utc)

    await state.update_data(time_str=text, date_stream=dt.isoformat())
    await state.set_state(WebinarCreateStates.confirm)

    # превью как будет выглядеть
    title = data["title"]
    ds = data["description_small"]
    df = data["description_full"]

    preview = (
        f"🎓 <b>{title}</b>\n\n"
        f"{ds}\n\n"
        f"{df}\n\n"
        f"🗓 <b>Дата:</b> {dt.strftime('%d.%m.%Y')}  ⏰ <b>Время:</b> {dt.strftime('%H:%M')} (UTC)"
    )

    msg = await message.answer(
        preview,
        reply_markup=kb_confirm_webinar_create(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await track_webinar_ui_msg(state, msg)


# -------------------------
# 9) Сохранение
# -------------------------
@router.callback_query(F.data == "webinar:create_save")
async def webinar_create_save(
    callback: types.CallbackQuery,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession
):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа ❌", show_alert=True)
        return

    data = await state.get_data()

    title = data["title"]
    description_small = data["description_small"]
    description_full = data["description_full"]
    date_stream = datetime.fromisoformat(data["date_stream"])

    w = Webinar(
        title=title,
        description_small=description_small,
        description_full=description_full,
        date_stream=date_stream,
        is_active=True,
    )
    session.add(w)
    await session.commit()

    # обновляем кеш
    await refresh_webinars_cache(session, redis_client)
    await refresh_webinars_cache_admin(session, redis_client)
    # чистим все сообщения сценария
    await cleanup_webinar_ui(bot, state, chat_id=callback.message.chat.id)
    await state.clear()

    # возвращаемся на страницу вебинаров
    await show_screen(callback, state, bot, "admin_webinars", push_history=False)
    upcoming = await get_upcoming_webinars(redis_client)
    items = [(x.id, x.title) for x in upcoming]
    try:
        await callback.message.edit_reply_markup(reply_markup=kb_webinars_list(items))
    except Exception:
        pass

    await callback.answer("Вебинар сохранён ✅", show_alert=True)


WEBINAR_UI_KEYS = {"webinar_ui_msg_ids"}


async def track_webinar_ui_msg(state: FSMContext, msg: types.Message) -> None:
    data = await state.get_data()
    ids = data.get("webinar_ui_msg_ids") or []
    ids.append(msg.message_id)
    await state.update_data(webinar_ui_msg_ids=ids)


async def cleanup_webinar_ui(bot, state: FSMContext, chat_id: int) -> None:
    data = await state.get_data()
    ids = data.get("webinar_ui_msg_ids") or []
    for mid in ids:
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass
    # не трогаем screen_message_id (экран админки), только мусор сценария
    for k in WEBINAR_UI_KEYS:
        data.pop(k, None)
    await state.set_data(data)


def text_with_entities_to_html(text: str, entities: list[types.MessageEntity] | None) -> str:
    # вернёт HTML-строку: <b>, <i>, <a href="...">...</a> и т.п.
    return html_decoration.unparse(text, entities or [])
