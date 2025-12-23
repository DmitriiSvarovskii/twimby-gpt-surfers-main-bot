from collections import defaultdict
import asyncio
from aiogram import Router, F, Bot, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, desc

from app.navigation import show_screen
from app.model.webinar import Webinar
from app.config import settings
from app.utils.telegram.broadcast import (
    broadcast_job,
)
from app.services.mailling.mail import (
    get_recipients_all,
    get_recipients_by_webinar,
)
from app.fsm.admin import BroadcastStates
from app.keyboard.admin.broadcast import (
    kb_broadcast_entry,
    kb_webinars,
    kb_cancel,
    kb_confirm,
    kb_start,
)
from app.utils.check_admin import is_admin
from app.utils.telegram.broadcast import serialize_message, send_payload, serialize_media_group_item, _dump_entities

router = Router()


_mg_locks = defaultdict(asyncio.Lock)


@router.callback_query(F.data == "message_broadcast")
async def broadcast_enter(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа ❌", show_alert=True)
        return

    # await state.clear()
    await state.set_state(BroadcastStates.choose_audience)

    await callback.message.edit_caption(
        caption="<b>Рассылка</b>\n\nКому отправляем?",
        reply_markup=kb_broadcast_entry(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "bc:cancel")
async def broadcast_cancel(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа ❌", show_alert=True)
        return

    await callback.answer("Отменено", show_alert=True)

    # ✅ удаляем все сообщения рассылки
    await cleanup_broadcast_ui(bot, state, chat_id=callback.message.chat.id)

    # ✅ возвращаем админку
    await show_screen(callback, state, bot, "admin_main", push_history=False)

    # ✅ чистим только локальные ключи (без state.clear())
    await clear_broadcast_only(state)


@router.callback_query(F.data == "bc:all")
async def broadcast_choose_all(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа ❌", show_alert=True)
        return

    await state.update_data(audience="all", webinar_id=None)
    await state.set_state(BroadcastStates.waiting_content)

    await callback.message.edit_caption(
        caption="Ок. Пришли контент для рассылки (любой: текст/фото/видео/файл/альбом).",
        reply_markup=kb_cancel(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "bc:by_webinar")
async def broadcast_choose_by_webinar(
    callback: types.CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа ❌", show_alert=True)
        return

    webinars = (
        await session.execute(
            select(Webinar.id, Webinar.title, Webinar.date_stream)
            .order_by(desc(Webinar.date_stream), desc(Webinar.id))
        )
    ).all()

    await state.set_state(BroadcastStates.choose_webinar)

    await callback.message.edit_caption(
        caption="Выбери вебинар для рассылки:",
        reply_markup=kb_webinars([(w[0], w[1], w[2]) for w in webinars]),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "bc:back_to_audience")
async def broadcast_back_to_audience(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа ❌", show_alert=True)
        return

    await state.set_state(BroadcastStates.choose_audience)
    await callback.message.edit_caption(
        caption="<b>Рассылка</b>\n\nКому отправляем?",
        reply_markup=kb_broadcast_entry(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bc:webinar:"))
async def broadcast_webinar_selected(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа ❌", show_alert=True)
        return

    webinar_id = int(callback.data.split(":")[-1])
    await state.update_data(audience="webinar", webinar_id=webinar_id)
    await state.set_state(BroadcastStates.waiting_content)

    await callback.message.edit_caption(
        caption="Ок. Пришли контент для рассылки (любой: текст/фото/видео/файл/альбом).",
        reply_markup=kb_cancel(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(BroadcastStates.waiting_content)
async def broadcast_receive_content(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    # ✅ альбом
    if message.media_group_id:
        lock = _mg_locks[(message.chat.id, message.from_user.id)]
        async with lock:
            item = serialize_media_group_item(message)
            if item["type"] == "unsupported":
                await message.answer("В альбоме поддерживаю только фото/видео.")
                return

            data = await state.get_data()
            admin_ids = data.get("admin_content_message_ids") or []
            admin_ids.append(message.message_id)
            await state.update_data(
                admin_content_chat_id=message.chat.id,
                admin_content_message_ids=admin_ids,
            )
            if data.get("mg_id") != message.media_group_id:
                await state.update_data(
                    mg_id=message.media_group_id,
                    mg_items=[],
                    mg_caption=None,
                    mg_caption_entities=None,
                    mg_show_caption_above_media=None,
                    mg_finalize_scheduled=False,
                )
                data = await state.get_data()

            mg_items = data.get("mg_items") or []
            mg_items.append(item)
            await state.update_data(mg_items=mg_items)

            if message.caption:
                await state.update_data(
                    mg_caption=message.caption,
                    mg_caption_entities=_dump_entities(message.caption_entities),
                    mg_show_caption_above_media=getattr(message, "show_caption_above_media", None),
                )

            # ✅ теперь точно один раз
            data = await state.get_data()
            if not data.get("mg_finalize_scheduled"):
                await state.update_data(mg_finalize_scheduled=True)
                asyncio.create_task(_finalize_media_group(state, message))

        return

    # ✅ одиночное сообщение
    payload = serialize_message(message)
    if payload["type"] == "unsupported":
        await message.answer(
            "Этот тип контента пока не поддерживается.\n"
            "Пришли текст / фото / видео / видео-кружочек / файл / аудио / стикер."
        )
        return

    await state.update_data(
        payload=payload,
        admin_content_chat_id=message.chat.id,
        admin_content_message_ids=[message.message_id],

    )
    await state.set_state(BroadcastStates.confirm)
    msg = await message.answer(
        "Принято ✅\n\nПроверь контент. Могу отправить тест в чат админов.",
        reply_markup=kb_confirm(),
    )
    await track_broadcast_msg(state, msg)


@router.callback_query(F.data == "bc:send_test")
async def broadcast_send_test(
    callback: types.CallbackQuery,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа ❌", show_alert=True)
        return

    data = await state.get_data()

    # 1) payload вместо copy_message
    payload = data.get("payload")
    if not payload:
        await callback.answer("Контент не найден. Пришли сообщение заново.", show_alert=True)
        return

    # отправляем тест в админ-чат
    try:
        await send_payload(bot=bot, chat_id=settings.ADMINT_CHAT, payload=payload)
    except Exception as e:
        await callback.answer(f"Не смог отправить тест: {e}", show_alert=True)
        return

    await callback.answer("Тест отправлен. Проверьте чат админов.", show_alert=True)

    # 2) считаем получателей
    audience = data.get("audience")
    webinar_id = data.get("webinar_id")

    if audience == "all":
        recipients = await get_recipients_all(session)
    else:
        recipients = await get_recipients_by_webinar(session, int(webinar_id))

    await state.update_data(recipients_count=len(recipients))
    await state.set_state(BroadcastStates.ready)

    # 3) НЕ answer() (новое сообщение), а редактируем текущее
    text = f"Запустить рассылку по <b>{len(recipients)}</b> пользователям?"

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=kb_start(len(recipients)),
            parse_mode="HTML",
        )
        # если хочешь — трекать можно текущее сообщение
        await track_broadcast_msg(state, callback.message)
    except Exception:
        # fallback — если вдруг edit_caption нельзя (например, это текстовое сообщение)
        msg = await callback.message.answer(
            text,
            reply_markup=kb_start(len(recipients)),
            parse_mode="HTML",
        )
        await track_broadcast_msg(state, msg)

    await state.set_state(BroadcastStates.ready)


@router.callback_query(BroadcastStates.ready, F.data == "bc:start")
async def broadcast_start(
    callback: types.CallbackQuery,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],  # ✅ нужен factory для фона
):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа ❌", show_alert=True)
        return

    data = await state.get_data()
    audience = data.get("audience")
    webinar_id = data.get("webinar_id")
    # content_chat_id = data["content_chat_id"]
    # content_message_id = data["content_message_id"]

    if audience == "all":
        recipients = await get_recipients_all(session)
    else:
        recipients = await get_recipients_by_webinar(session, int(webinar_id))

    # запускаем фоном
    payload = data["payload"]

    asyncio.create_task(
        broadcast_job(
            bot,
            session_factory,
            admin_tg_id=callback.from_user.id,
            recipients=recipients,
            payload=payload,
        )
    )

    await callback.answer("Рассылка запущена ✅\nВам придёт отчёт по завершению.", show_alert=True)
    await cleanup_broadcast_ui(bot, state, chat_id=callback.message.chat.id)

    # чистим state и возвращаем в админку
    await show_screen(callback, state, bot, "admin_main", push_history=False)
    await clear_broadcast_only(state)


BROADCAST_KEYS = {
    "audience",
    "webinar_id",
    "content_chat_id",
    "content_message_id",
    "recipients_count",
    "broadcast_msg_ids",  # ✅ новые
    "admin_content_chat_id",
    "admin_content_message_ids",  # list[int]
}

MEDIA_GROUP_KEYS = {
    "mg_id",
    "mg_items",
    "mg_caption",
    "mg_caption_entities",
    "mg_show_caption_above_media",
    "mg_finalize_scheduled",
}


async def track_broadcast_msg(state: FSMContext, msg: types.Message) -> None:
    data = await state.get_data()
    ids = data.get("broadcast_msg_ids") or []
    ids.append(msg.message_id)
    await state.update_data(broadcast_msg_ids=ids)


async def cleanup_broadcast_ui(bot: Bot, state: FSMContext, chat_id: int) -> None:
    """
    Удаляет все сообщения, которые бот отправлял в ходе сценария рассылки,
    и (если есть) удаляет сообщение-контент админа.
    """
    data = await state.get_data()
    # 1) удаляем "контент" сообщение админа (которое он прислал для рассылки)
    admin_chat_id = data.get("admin_content_chat_id")
    admin_message_ids = data.get("admin_content_message_ids") or []

    if admin_chat_id and admin_message_ids:
        for mid in admin_message_ids:
            try:
                await bot.delete_message(admin_chat_id, mid)
            except Exception:
                pass

    # 2) удаляем сообщения бота, которые мы отправляли (answer())
    msg_ids = data.get("broadcast_msg_ids") or []
    for mid in msg_ids:
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass


async def clear_broadcast_only(state: FSMContext) -> None:
    data = await state.get_data()
    for k in BROADCAST_KEYS:
        data.pop(k, None)
    await state.set_data(data)
    await state.set_state(None)


async def _finalize_media_group(state: FSMContext, message: types.Message) -> None:
    # ждём, пока прилетят остальные элементы альбома
    await asyncio.sleep(0.8)

    data = await state.get_data()
    items = data.get("mg_items") or []
    if not items:
        return

    payload = {
        "type": "media_group",
        "items": items,  # list of {"type": photo/video, "file_id":..., "has_spoiler":...}
        "caption": data.get("mg_caption"),
        "caption_entities": data.get("mg_caption_entities"),
        "show_caption_above_media": data.get("mg_show_caption_above_media"),
    }

    await state.update_data(payload=payload)
    await state.set_state(BroadcastStates.confirm)

    msg = await message.answer(
        "Принято ✅ (альбом)\n\nПроверь контент. Могу отправить тест в чат админов.",
        reply_markup=kb_confirm(),
    )
    await track_broadcast_msg(state, msg)

    # подчистим временные ключи альбома (payload оставляем)
    d = await state.get_data()
    for k in MEDIA_GROUP_KEYS:
        d.pop(k, None)
    await state.set_data(d)
