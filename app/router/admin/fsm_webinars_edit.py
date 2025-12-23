import re
from datetime import datetime, timezone

from aiogram import Router, F, Bot, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.redis_client import redis_client

from app.utils.check_admin import is_admin
from app.navigation import show_screen

from app.keyboard.admin.webinars import (
    kb_webinar_view,
    kb_webinar_edit_cancel,
    kb_webinar_edit_confirm,
)
from app.fsm.admin_webinar_edit import WebinarEditStates
from app.services.webinars.service import (
    get_webinar_by_id,
    render_webinar_full,
    text_with_entities_to_html,
    refresh_webinars_cache,
)
from app.services.webinars.cache import refresh_webinars_cache_admin

router = Router()

# --- утилиты: удаление "страниц" и шаговых сообщений ---
WEBINAR_UI_KEYS = {
    "webinar_page_msg_id",
    "webinar_edit_msg_ids",
    "webinar_edit_wid",
    "webinar_edit_title",
    "webinar_edit_desc_small",
    "webinar_edit_desc_full",
    "webinar_edit_date",
    "webinar_edit_time",
}


async def _track_edit_msg(state: FSMContext, msg: types.Message) -> None:
    data = await state.get_data()
    ids = data.get("webinar_edit_msg_ids") or []
    ids.append(msg.message_id)
    await state.update_data(webinar_edit_msg_ids=ids)


async def _cleanup_webinar_ui(bot: Bot, state: FSMContext, chat_id: int) -> None:
    data = await state.get_data()

    # удаляем "страницу" вебинара (отдельным сообщением)
    page_mid = data.get("webinar_page_msg_id")
    if page_mid:
        try:
            await bot.delete_message(chat_id, page_mid)
        except Exception:
            pass

    # удаляем все шаговые сообщения (вопросы/подтверждение/и т.д.)
    for mid in (data.get("webinar_edit_msg_ids") or []):
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass

    # если админ что-то вводил текстом — это НЕ удаляем (обычно нельзя без трекинга)
    # если хочешь удалять и сообщения админа — надо хранить их message_id на каждом шаге.


async def _reset_edit_state(state: FSMContext) -> None:
    data = await state.get_data()
    for k in WEBINAR_UI_KEYS:
        data.pop(k, None)
    await state.set_data(data)
    await state.set_state(None)


# --- 1) Открыть страницу вебинара (полный текст, не caption) ---
@router.callback_query(F.data.startswith("webinar:edit:"))
async def webinar_open(callback: types.CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа ❌", show_alert=True)
        return

    wid = int(callback.data.split(":")[-1])
    w = await get_webinar_by_id(session, wid)
    if not w:
        await callback.answer("Вебинар не найден", show_alert=True)
        return

    # удалим предыдущую "страницу", если была
    data = await state.get_data()
    old_mid = data.get("webinar_page_msg_id")
    if old_mid:
        try:
            await bot.delete_message(callback.message.chat.id, old_mid)
        except Exception:
            pass

    text = render_webinar_full(w)
    msg = await bot.send_message(
        chat_id=callback.message.chat.id,
        text=text,
        reply_markup=kb_webinar_view(wid, bool(w.is_active)),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await state.update_data(webinar_page_msg_id=msg.message_id)

    await callback.answer()


# --- 2) Назад в список вебинаров (через show_screen) ---
@router.callback_query(F.data == "webinar:back_to_list")
async def webinar_back_to_list(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа ❌", show_alert=True)
        return

    await _cleanup_webinar_ui(bot, state, chat_id=callback.message.chat.id)
    await _reset_edit_state(state)

    # возвращаемся на страницу вебинаров через show_screen
    await show_screen(callback, state, bot, "admin_webinars", push_history=False)
    await callback.answer()


# --- 3) Toggle is_active ---
@router.callback_query(F.data.startswith("webinar:toggle:"))
async def webinar_toggle_active(
    callback: types.CallbackQuery,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession
):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа ❌", show_alert=True)
        return

    wid = int(callback.data.split(":")[-1])
    w = await get_webinar_by_id(session, wid)
    if not w:
        await callback.answer("Вебинар не найден", show_alert=True)
        return

    w.is_active = not bool(w.is_active)
    await session.commit()

    # обновим кеш
    await refresh_webinars_cache(session, redis_client)
    await refresh_webinars_cache_admin(session, redis_client)
    # обновим текст на странице (сообщение отдельное, не caption)
    page_mid = (await state.get_data()).get("webinar_page_msg_id")
    if page_mid:
        try:
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=page_mid,
                text=render_webinar_full(w),
                reply_markup=kb_webinar_view(wid, bool(w.is_active)),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except Exception:
            pass

    await callback.answer("Сохранено ✅", show_alert=True)


# --- 4) Старт редактирования полей ---
@router.callback_query(F.data.startswith("webinar:edit_fields:"))
async def webinar_edit_fields_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа ❌", show_alert=True)
        return

    wid = int(callback.data.split(":")[-1])
    await state.update_data(webinar_edit_wid=wid, webinar_edit_msg_ids=[])
    await state.set_state(WebinarEditStates.waiting_title)

    msg = await callback.message.answer("Введи <b>Название вебинара</b>:", parse_mode="HTML", reply_markup=kb_webinar_edit_cancel())
    await _track_edit_msg(state, msg)

    await callback.answer()


# --- 5) Отмена (на любом шаге) ---
@router.callback_query(F.data == "webinar:edit_cancel")
async def webinar_edit_cancel(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа ❌", show_alert=True)
        return

    await _cleanup_webinar_ui(bot, state, chat_id=callback.message.chat.id)

    # возвращаемся на страницу просмотра вебинара (если wid есть)
    data = await state.get_data()
    wid = data.get("webinar_edit_wid")

    await _reset_edit_state(state)

    if wid:
        # просто переоткроем страницу вебинара (полный текст)
        # имитируем callback в один шаг: вызываем handler напрямую не будем,
        # отправим заново (проще/надёжнее).
        await callback.answer("Отменено", show_alert=True)
    else:
        await callback.answer("Отменено", show_alert=True)
    # чтобы было “как раньше”: возвращаем на страницу вебинаров
    await show_screen(callback, state, bot, "admin_webinars", push_history=False)


# --- 6) Шаги FSM ---
@router.message(WebinarEditStates.waiting_title)
async def webinar_edit_title(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(webinar_edit_title=(message.text or "").strip())
    await state.set_state(WebinarEditStates.waiting_desc_small)

    msg = await message.answer(
        "Введи <b>Короткое описание, которое будет отображаться в выборе из списка вебинаров</b>:",
        parse_mode="HTML",
        reply_markup=kb_webinar_edit_cancel(),
    )
    await _track_edit_msg(state, msg)


@router.message(WebinarEditStates.waiting_desc_small)
async def webinar_edit_desc_small(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    html = text_with_entities_to_html(message.text or "", message.entities)
    await state.update_data(webinar_edit_desc_small=html)
    await state.set_state(WebinarEditStates.waiting_desc_full)

    msg = await message.answer(
        "Введи <b>Полное описание вебинара, которое будет отображаться в карточке вебинара</b>:",
        parse_mode="HTML",
        reply_markup=kb_webinar_edit_cancel(),
    )
    await _track_edit_msg(state, msg)


@router.message(WebinarEditStates.waiting_desc_full)
async def webinar_edit_desc_full(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    html = text_with_entities_to_html(message.text or "", message.entities)
    await state.update_data(webinar_edit_desc_full=html)
    await state.set_state(WebinarEditStates.waiting_date)

    msg = await message.answer(
        "Введи дату в формате <b>дд.мм.гггг</b>, например: <code>24.07.2026</code>",
        parse_mode="HTML",
        reply_markup=kb_webinar_edit_cancel(),
    )
    await _track_edit_msg(state, msg)


_DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")


@router.message(WebinarEditStates.waiting_date)
async def webinar_edit_date(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    s = (message.text or "").strip()
    if not _DATE_RE.match(s):
        msg = await message.answer("Неверный формат. Нужно <b>дд.мм.гггг</b>", parse_mode="HTML", reply_markup=kb_webinar_edit_cancel())
        await _track_edit_msg(state, msg)
        return

    await state.update_data(webinar_edit_date=s)
    await state.set_state(WebinarEditStates.waiting_time)

    msg = await message.answer(
        "Введи время в формате <b>чч:мм</b>, например: <code>14:00</code>",
        parse_mode="HTML",
        reply_markup=kb_webinar_edit_cancel(),
    )
    await _track_edit_msg(state, msg)


@router.message(WebinarEditStates.waiting_time)
async def webinar_edit_time(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    s = (message.text or "").strip()
    if not _TIME_RE.match(s):
        msg = await message.answer("Неверный формат. Нужно <b>чч:мм</b>", parse_mode="HTML", reply_markup=kb_webinar_edit_cancel())
        await _track_edit_msg(state, msg)
        return

    await state.update_data(webinar_edit_time=s)
    await state.set_state(WebinarEditStates.confirm)

    data = await state.get_data()
    title = data.get("webinar_edit_title") or ""
    ds = data.get("webinar_edit_desc_small") or ""
    df = data.get("webinar_edit_desc_full") or ""
    date_s = data.get("webinar_edit_date")
    time_s = data.get("webinar_edit_time")

    preview = (
        "<b>Проверь данные:</b>\n\n"
        f"<b>Title:</b> {title}\n"
        f"<b>Date:</b> {date_s} {time_s}\n\n"
        f"<b>description_small:</b>\n{ds}\n\n"
        f"<b>description_full:</b>\n{df}"
    )
    wid = int(data["webinar_edit_wid"])

    msg = await message.answer(preview, parse_mode="HTML", reply_markup=kb_webinar_edit_confirm(wid))
    await _track_edit_msg(state, msg)


# --- 7) Сохранение ---
@router.callback_query(F.data.startswith("webinar:edit_save:"))
async def webinar_edit_save(
    callback: types.CallbackQuery,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession
):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа ❌", show_alert=True)
        return

    wid = int(callback.data.split(":")[-1])
    data = await state.get_data()

    w = await get_webinar_by_id(session, wid)
    if not w:
        await callback.answer("Вебинар не найден", show_alert=True)
        return

    title = (data.get("webinar_edit_title") or "").strip()
    ds = data.get("webinar_edit_desc_small") or ""
    df = data.get("webinar_edit_desc_full") or ""
    date_s = data.get("webinar_edit_date")
    time_s = data.get("webinar_edit_time")

    # соберём datetime в UTC (как у тебя было при создании)
    dt = datetime.strptime(f"{date_s} {time_s}", "%d.%m.%Y %H:%M").replace(tzinfo=timezone.utc)

    w.title = title
    w.description_small = ds   # ✅ уже HTML со всеми <b>/<i>/<a>
    w.description_full = df
    w.date_stream = dt

    await session.commit()

    # обновим кеш
    await refresh_webinars_cache(session, redis_client)
    await refresh_webinars_cache_admin(session, redis_client)
    # удалим все UI-сообщения (подтверждение/шаги/страницу)
    await _cleanup_webinar_ui(bot, state, chat_id=callback.message.chat.id)
    await _reset_edit_state(state)

    # вернёмся на страницу вебинаров
    await show_screen(callback, state, bot, "admin_webinars", push_history=False)
    await callback.answer("Сохранено ✅", show_alert=True)
