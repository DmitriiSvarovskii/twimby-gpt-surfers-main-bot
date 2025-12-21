from app.model.webinar import Webinar, WebinarRegistration
from app.model.user import User
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram import Router, types, F, Bot

from app.navigation import show_screen
from app.config import settings


router = Router()


@router.callback_query(F.data == "admin")
async def admin_panel(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    if callback.from_user.id not in settings.ADMIN_TG_IDS:
        await callback.answer("Нет доступа ❌", show_alert=True)
        return
    await callback.answer()
    await show_screen(callback, state, bot, "admin_main")


def _kb_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data="back")]]
    )


@router.callback_query(F.data == "users")
async def admin_users_stats(
    callback: CallbackQuery,
    bot: Bot,
    session: AsyncSession,
    state: FSMContext,   # ✅ добавили
):
    if callback.from_user.id not in set(settings.ADMIN_TG_IDS):
        await callback.answer("Нет доступа", show_alert=True)
        return

    # ✅ фикс истории
    data = await state.get_data()
    history = list(data.get("history", []))
    current = data.get("current_screen")

    # если мы пришли из admin_main — запомним его
    if current and current != "users":
        history.append(current)

    await state.update_data(history=history, current_screen="users")

    # ---- дальше твоя логика статистики ----
    total_users = await session.scalar(select(func.count(User.id)))

    photo_users = await session.scalar(
        select(func.count(User.id)).where(
            or_(
                User.welcome_photo_generated.is_(True),
                User.subbscribed_photo_generated.is_(True),
            )
        )
    )

    rows = (await session.execute(
        select(
            Webinar.id,
            Webinar.title,
            func.count(WebinarRegistration.id).label("cnt"),
        )
        .outerjoin(WebinarRegistration, WebinarRegistration.webinar_id == Webinar.id)
        .group_by(Webinar.id, Webinar.title)
        .order_by(Webinar.id)
    )).all()

    parts = [
        "<b>Статистика по пользователям</b>",
        "",
        f"👥 Всего пользователей: <b>{total_users or 0}</b>",
        f"🖼 Делали генерацию фото: <b>{photo_users or 0}</b>",
        "",
        "<b>Записи на вебинары:</b>",
    ]

    if rows:
        for webinar_id, title, cnt in rows:
            parts.append(f"\n— {title}: <b>{cnt}</b>\n")
    else:
        parts.append("🚫 Нет данных по вебинарам")

    text = "\n".join(parts)

    try:
        await bot.edit_message_caption(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            caption=text,
            reply_markup=_kb_back(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(text, reply_markup=_kb_back(), parse_mode="HTML")

    await callback.answer()
