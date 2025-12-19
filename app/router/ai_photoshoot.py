from __future__ import annotations
from app.services.users.flags import mark_user_photos_generated
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.users.ai_photoshoot_gate import get_user_by_tg_id
from app.utils.telegram.subscription import is_user_subscribed
from aiogram.types import InputMediaPhoto
import logging
from typing import Dict
import os
import asyncio

from typing import Optional
import aiohttp
import tempfile
import os
import uuid

from aiogram import Bot
from aiogram.types import InputMediaDocument, FSInputFile

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
    FSInputFile,
    Message,
)
from aiogram.exceptions import TelegramBadRequest
from app.lexicon.promt import AI_PHOTO_PROMPTS

from app.navigation import show_screen
from app.utils.ai_photoshoot_service import generate_photoshoot_pack

router = Router()

logger = logging.getLogger(__name__)


async def _run_photoshoot_background(
    *,
    bot: Bot,
    chat_id: int,
    kie_api_key: str,
    ai_photo_prompts: dict,
    gender: str | None,
    category_key: str | None,
    reference_file_ids: list[str],
    dev_upload_chat_id: int,
):
    temp_files: list[str] = []

    try:
        urls = await generate_photoshoot_pack(
            bot,
            kie_api_key=kie_api_key,
            ai_photo_prompts=ai_photo_prompts,
            gender=gender,
            category_key=category_key,
            reference_file_ids=reference_file_ids,
            dev_upload_chat_id=dev_upload_chat_id,
            fallback_chat_id=chat_id,
        )

        urls = [u for u in (urls or []) if u]
        if not urls:
            await bot.send_message(chat_id=chat_id, text="⚠️ Генерация вернула пустой результат.")
            return

        # Telegram media_group: максимум 10 вложений
        urls = urls[:10]

        async with aiohttp.ClientSession() as session:
            for url in urls:
                async with session.get(url) as resp:
                    resp.raise_for_status()

                    tmp_path = os.path.join(
                        tempfile.gettempdir(),
                        f"ai_photoshoot_{uuid.uuid4().hex}.jpg",
                    )

                    with open(tmp_path, "wb") as f:
                        f.write(await resp.read())

                    temp_files.append(tmp_path)

        media = [InputMediaDocument(media=FSInputFile(path)) for path in temp_files]

        # caption можно только у первого элемента
        # media[0].caption = "✅ Готово!"
        # media[0].parse_mode = "HTML"

        await bot.send_media_group(chat_id=chat_id, media=media)

    except Exception as e:
        # logger.exception("Photoshoot generation failed")
        try:
            await bot.send_message(chat_id=chat_id, text=f"⚠️ Ошибка генерации: {e}")
        except Exception:
            pass

    finally:
        for path in temp_files:
            try:
                os.remove(path)
            except Exception:
                pass


# lock на пользователя, чтобы не было гонок при media_group
_USER_LOCKS: Dict[int, asyncio.Lock] = {}


def _get_lock(user_id: int) -> asyncio.Lock:
    lock = _USER_LOCKS.get(user_id)
    if lock is None:
        lock = asyncio.Lock()
        _USER_LOCKS[user_id] = lock
    return lock


KIE_API_KEY = "381ef4085dd3c9a1e28ce9bb24df8cc0"


# Минимальное число фото для аватарок (по описанию)
MIN_PHOTOS = 1

# Первый экран (вход в фотобудку)
START_PHOTO = "app/static/ai_photo/ии_аватарки.png"

# Второй экран (инструкция + выбор пола)
INTRO_PHOTO = "app/static/ai_photoshoot/ai_photoshoot_intro.jpg"  # можно оставить как запасной

NO_PHOTO = "app/static/expert/no_photo.png"  # если нужного фото нет
REF_PHOTO = "app/static/референс.png"

# ======= FSM =======


class AiPhotoshootStates(StatesGroup):
    waiting_start = State()
    waiting_gender = State()
    waiting_category = State()
    waiting_photos = State()


# ======= Категории =======
CATEGORIES = [
    {"id": "winter", "title": "❄️ Зимняя сказка"},
    {"id": "surfing", "title": "🏄 Серфинг"},
    {"id": "animals", "title": "🐾 С животными"},
    {"id": "travel", "title": "🌍 Путешествия"},
    {"id": "style", "title": "💼 Деловой"},
]


# ======= Keyboards =======
def kb_gender() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Мужской", callback_data="ai_ps_gender:male"),
                InlineKeyboardButton(text="Женский", callback_data="ai_ps_gender:female"),
            ],
            [InlineKeyboardButton(text="Главное меню", callback_data="ai_ps_back_to_menu")],
        ]
    )


def kb_categories() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=c["title"], callback_data=f"ai_ps_cat:{c['id']}")] for c in CATEGORIES]
    rows.append([InlineKeyboardButton(text="Назад", callback_data="ai_ps_back_to_gender")])
    rows.append([InlineKeyboardButton(text="Главное меню", callback_data="ai_ps_back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# Первый экран: кнопка "Начать"
def kb_start() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Начать", callback_data="ai_ps_start")],
            [InlineKeyboardButton(text="Главное меню", callback_data="ai_ps_back_to_menu")],
        ]
    )


def kb_photos_wait(uploaded_count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"📷 Жду фото… ({uploaded_count}/{MIN_PHOTOS})", callback_data="ai_ps_noop")],
            [InlineKeyboardButton(text="Назад", callback_data="ai_ps_back_to_categories")],
            [InlineKeyboardButton(text="Главное меню", callback_data="ai_ps_back_to_menu")],
        ]
    )


def kb_confirm(uploaded_count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"✅ Подтвердить ({uploaded_count} фото)", callback_data="ai_ps_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="ai_ps_cancel")],
            [InlineKeyboardButton(text="Главное меню", callback_data="ai_ps_back_to_menu")],
        ]
    )


# ======= Texts =======
def _intro_gender_text() -> str:
    return (
        "Ты в разделе ИИ-фотобудки📷\n"
        "Тут можно создать классные аватарки для соцсетей в разных стилях и темах.\n\n"
        "Как работает?\n"
        "1) Выберете пол. Это улучшит точность генерации\n"
        "2) Выберете тему будущих Аватарок - они будут меняться каждый месяц\n"
        "3) Загрузите свое лучшее селфи, где хорошо видно ваше лицо.\n"
        "4) В течение 5 минут бот создаст и отправит вам 5 аватарок по выбранной категории.\n\n"
        "Условия:\n"
        "— первая генерация 5 аватарок - бесплатно\n"
        "— следующие 5 аватарок за подписку на наш <a href=\"https://t.me/gptsurfers\">Telegram-канал</a>\n"
        # "— Все последующие можно купить за звезды⭐\n\n"
        "\n\nВо время генерации аватарок можно работать с ботом/телеграмом как обычно. "
        "Аватарки придут автоматически, как будут готовы🏄🏻‍♂️"
    )


def _intro_category_text(gender: str) -> str:
    g = "мужской" if gender == "male" else "женский"
    return f"Отлично, выбран <b>{g}</b> пол.\n\nТеперь выбери категорию фотосессии:"


def _photos_requirements_text(category_id: str, gender: str, uploaded_count: int) -> str:
    cat_title = next((c["title"] for c in CATEGORIES if c["id"] == category_id), category_id)
    g = "мужской" if gender == "male" else "женский"
    return (
        f"<b>Категория:</b> {cat_title}\n"
        f"<b>Пол:</b> {g}\n\n"
        "Загрузи 1 фото лица:\n"
        "• Крупный план\n"
        "• Без фильтров/ретуши\n"
        "• Хороший свет\n"
        "• Без очков/кепок/масок\n\n"
        f"Загружено: <b>{uploaded_count}</b> / {MIN_PHOTOS}\n\n"
    )


def _confirm_text(category_id: str, gender: str, uploaded_count: int) -> str:
    cat_title = next((c["title"] for c in CATEGORIES if c["id"] == category_id), category_id)
    g = "мужской" if gender == "male" else "женский"
    return (
        "✅ <b>Готово!</b>\n\n"
        f"<b>Категория:</b> {cat_title}\n"
        f"<b>Пол:</b> {g}\n"
        f"<b>Фото:</b> {uploaded_count}\n\n"
        "Подтверди — и я запущу фотосессию."
    )


# ======= Helpers =======
async def _edit_to_photo_caption(
    bot: Bot,
    chat_id: int,
    message_id: int,
    photo_path: str,
    caption: str,
    reply_markup: InlineKeyboardMarkup,
) -> None:
    await bot.edit_message_media(
        chat_id=chat_id,
        message_id=message_id,
        media=InputMediaPhoto(media=FSInputFile(photo_path), caption=caption, parse_mode="HTML"),
        reply_markup=reply_markup,
    )


async def _safe_delete(bot: Bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass


def _get_screen_message_id(callback: CallbackQuery, state_data: dict) -> int:
    # У тебя вход на ai_photoshoot со стартового окна (оно фото+caption)
    # Поэтому по умолчанию редактируем callback.message.message_id.
    smid = state_data.get("ai_ps_screen_message_id")
    if smid:
        return int(smid)
    return callback.message.message_id


# =====================================================================
# ENTRY: ai_photoshoot
# =====================================================================
@router.callback_query(F.data == "ai_photoshoot")
async def open_ai_photoshoot(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    prev_screen = data.get("current_screen") or "start"

    await state.update_data(
        ai_ps_prev_screen=prev_screen,
        ai_ps_gender=None,
        ai_ps_category=None,
        ai_ps_uploaded_file_ids=[],
        ai_ps_uploaded_message_ids=[],
        ai_ps_screen_message_id=callback.message.message_id,
        current_screen="ai_photoshoot",
    )
    await state.set_state(AiPhotoshootStates.waiting_start)

    chat_id = callback.message.chat.id
    msg_id = callback.message.message_id

    start_path = START_PHOTO if os.path.exists(START_PHOTO) else NO_PHOTO

    # Первый экран: картинка + кнопка "Начать"
    try:
        await _edit_to_photo_caption(
            bot=bot,
            chat_id=chat_id,
            message_id=msg_id,
            photo_path=start_path,
            caption=_intro_gender_text(),
            reply_markup=kb_start(),
        )
    except TelegramBadRequest:
        msg = await callback.message.answer_photo(
            photo=FSInputFile(start_path),
            caption=_intro_gender_text(),
            reply_markup=kb_start(),
            parse_mode="HTML",
        )
        await state.update_data(ai_ps_screen_message_id=msg.message_id)

    await callback.answer()


# Новый обработчик: "Начать" → показываем инструкцию и выбор пола (второй экран)


@router.callback_query(AiPhotoshootStates.waiting_start, F.data == "ai_ps_start")
async def ai_ps_start(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,  # <-- важно
):
    tg_id = callback.from_user.id

    # 1) получаем пользователя из БД
    user = await get_user_by_tg_id(session, tg_id)
    if user is None:
        await callback.answer("Пожалуйста перезапустите бота. Отправьте команду /start", show_alert=True)
        return

    # 2) условия доступа
    generation_kind: str | None = None

    if user.welcome_photo_generated is False:
        # первая генерация бесплатна
        generation_kind = "welcome"

    else:
        # welcome уже было
        if user.subbscribed_photo_generated is False:
            # вторая генерация доступна только подписанным
            subscribed = await is_user_subscribed(bot, tg_id)
            if not subscribed:
                await callback.answer(
                    "Чтобы сделать генерацию аватарок, подпишись на нашу группу",
                    show_alert=True,
                )
                return
            generation_kind = "subscribed"
        else:
            # обе генерации уже использованы (дальше будет stars/покупка)
            await callback.answer("Лимит бесплатных генераций исчерпан ⭐", show_alert=True)
            return

    # ✅ сохраняем, с каким режимом пользователь вошёл
    await state.update_data(ai_ps_generation_kind=generation_kind)

    # 3) дальше — твоя текущая логика
    data = await state.get_data()
    await state.set_state(AiPhotoshootStates.waiting_gender)

    chat_id = callback.message.chat.id
    screen_mid = int(data.get("ai_ps_screen_message_id") or callback.message.message_id)

    photo_path = "app/static/ai_photo/м_ж.png"

    try:
        await _edit_to_photo_caption(
            bot=bot,
            chat_id=chat_id,
            message_id=screen_mid,
            photo_path=photo_path,
            caption="Сначала выбери пол — это нужно, чтобы правильно подобрать стилизацию.",
            reply_markup=kb_gender(),
        )
    except TelegramBadRequest:
        msg = await callback.message.answer_photo(
            photo=FSInputFile(photo_path),
            caption="Сначала выбери пол — это нужно, чтобы правильно подобрать стилизацию.",
            reply_markup=kb_gender(),
            parse_mode="HTML",
        )
        await state.update_data(ai_ps_screen_message_id=msg.message_id)

    await callback.answer()


# =====================================================================
# STEP 1: gender
# =====================================================================
@router.callback_query(AiPhotoshootStates.waiting_gender, F.data.startswith("ai_ps_gender:"))
async def ai_ps_choose_gender(callback: CallbackQuery, state: FSMContext, bot: Bot):
    gender = callback.data.split(":", 1)[1]  # male/female
    chat_id = callback.message.chat.id
    data = await state.get_data()

    screen_mid = int(data.get("ai_ps_screen_message_id") or callback.message.message_id)
    photo_path = "app/static/ai_photo/Зима.png"

    await state.update_data(ai_ps_gender=gender)
    await state.set_state(AiPhotoshootStates.waiting_category)
    await _edit_to_photo_caption(
        bot=bot,
        chat_id=chat_id,
        message_id=screen_mid,
        photo_path=photo_path,
        caption=_intro_category_text(gender),
        reply_markup=kb_categories(),
    )
    # await callback.message.edit_caption(
    #     caption=_intro_category_text(gender),
    #     reply_markup=kb_categories(),
    #     parse_mode="HTML",
    # )
    await callback.answer()


# =====================================================================
# STEP 2: category -> waiting_photos
# =====================================================================
@router.callback_query(AiPhotoshootStates.waiting_category, F.data.startswith("ai_ps_cat:"))
async def ai_ps_choose_category(callback: CallbackQuery, state: FSMContext):
    category_id = callback.data.split(":", 1)[1]

    data = await state.get_data()
    gender = data.get("ai_ps_gender") or "male"

    await state.update_data(ai_ps_category=category_id)
    await state.set_state(AiPhotoshootStates.waiting_photos)

    uploaded = data.get("ai_ps_uploaded_file_ids", []) or []
    await callback.message.edit_media(
        media=InputMediaPhoto(media=FSInputFile(REF_PHOTO), caption=_photos_requirements_text(category_id, gender, len(uploaded)), parse_mode="HTML"),
        # caption=_photos_requirements_text(category_id, gender, len(uploaded)),
        reply_markup=kb_photos_wait(len(uploaded)),
        # parse_mode="HTML",
    )
    await callback.answer()


# =====================================================================
# STEP 3: collect photos (single or media-group)
# =====================================================================
@router.message(AiPhotoshootStates.waiting_photos, F.photo)
async def ai_ps_collect_photo(message: Message, state: FSMContext, bot: Bot):
    lock = _get_lock(message.from_user.id)

    async with lock:
        data = await state.get_data()
        chat_id = message.chat.id

        file_id = message.photo[-1].file_id

        uploaded: list[str] = data.get("ai_ps_uploaded_file_ids", []) or []
        uploaded_msg_ids: list[int] = data.get("ai_ps_uploaded_message_ids", []) or []

        # защита от дублей (на всякий)
        if message.message_id in uploaded_msg_ids:
            return

        # ✅ ЛОГИКА: принимаем только 1 фото
        if len(uploaded) >= 1:
            # удаляем лишнее фото пользователя
            await _safe_delete(bot, chat_id, message.message_id)

            # говорим пользователю (коротко и понятно)
            try:
                await message.answer("Для этой фотосессии нужно отправить 1 фото ✅")
            except Exception:
                pass
            return

        # это первое фото -> сохраняем
        uploaded = [file_id]
        uploaded_msg_ids.append(message.message_id)

        await state.update_data(
            ai_ps_uploaded_file_ids=uploaded,
            ai_ps_uploaded_message_ids=uploaded_msg_ids,
        )

        gender = data.get("ai_ps_gender") or "male"
        category_id = data.get("ai_ps_category") or "unknown"

        # удаляем фото пользователя из чата
        await _safe_delete(bot, chat_id, message.message_id)

        screen_message_id = int(data.get("ai_ps_screen_message_id") or message.message_id)

        # обновляем "экран" -> ставим фото пользователя + confirm caption
        try:
            await bot.edit_message_media(
                chat_id=chat_id,
                message_id=screen_message_id,
                media=InputMediaPhoto(
                    media=file_id,  # ✅ подставляем фото пользователя
                    caption=_confirm_text(category_id, gender, 1),
                    parse_mode="HTML",
                ),
                reply_markup=kb_confirm(1),
            )
        except TelegramBadRequest:
            # если нельзя отредактировать — пересоздадим экран
            await _safe_delete(bot, chat_id, screen_message_id)
            new_msg = await bot.send_photo(
                chat_id=chat_id,
                photo=file_id,
                caption=_confirm_text(category_id, gender, 1),
                reply_markup=kb_confirm(1),
                parse_mode="HTML",
            )
            await state.update_data(ai_ps_screen_message_id=new_msg.message_id)
        except Exception:
            pass

        return


# =====================================================================
# Confirm / Cancel
# =====================================================================
@router.callback_query(AiPhotoshootStates.waiting_photos, F.data == "ai_ps_confirm")
async def ai_ps_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession):
    data = await state.get_data()
    chat_id = callback.message.chat.id

    uploaded_file_ids: list[str] = data.get("ai_ps_uploaded_file_ids", []) or []
    uploaded_msg_ids: list[int] = data.get("ai_ps_uploaded_message_ids", []) or []

    if len(uploaded_file_ids) < MIN_PHOTOS:
        await callback.answer(f"Нужно минимум {MIN_PHOTOS} фото. Сейчас: {len(uploaded_file_ids)}", show_alert=True)
        return

    # сохрани параметры для фоновой задачи (потому что state ты сейчас будешь чистить)
    gender = data.get("ai_ps_gender")
    category_key = data.get("ai_ps_category")
    reference_file_ids = list(uploaded_file_ids)

    await callback.answer(
        "Ок! Фотосессия сгенерируется, результаты отправлю в чат ✅",
        show_alert=True,
    )

    # удалить все фото пользователя (сообщения)
    for mid in set(uploaded_msg_ids):
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass

    # ФОНОВЫЙ ЗАПУСК (не await)
    asyncio.create_task(
        _run_photoshoot_background(
            bot=bot,
            chat_id=chat_id,
            kie_api_key=KIE_API_KEY,
            ai_photo_prompts=AI_PHOTO_PROMPTS,
            gender=gender,
            category_key=category_key,
            reference_file_ids=reference_file_ids,
            dev_upload_chat_id=-1005080691714,
        )
    )

    # дальше — как было

    tg_id = callback.from_user.id
    generation_kind = data.get("ai_ps_generation_kind")

    if generation_kind:
        await mark_user_photos_generated(session, tg_id=tg_id, generation_kind=generation_kind)

    await state.set_state(None)
    await state.update_data(
        ai_ps_gender=None,
        ai_ps_category=None,
        ai_ps_uploaded_file_ids=[],
        ai_ps_uploaded_message_ids=[],
        current_screen="start",
    )
    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id="start",
        as_new_message=False,
        push_history=False,
    )


@router.callback_query(AiPhotoshootStates.waiting_photos, F.data == "ai_ps_cancel")
async def ai_ps_cancel(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    chat_id = callback.message.chat.id

    # 1) удалить все фото пользователя (сообщения)
    uploaded_msg_ids: list[int] = data.get("ai_ps_uploaded_message_ids", []) or []
    for mid in set(uploaded_msg_ids):
        await _safe_delete(bot, chat_id, mid)

    # 2) сбросить сценарные данные (не обязательно state.clear, чтобы не ломать навигацию)
    await state.set_state(None)
    await state.update_data(
        ai_ps_gender=None,
        ai_ps_category=None,
        ai_ps_uploaded_file_ids=[],
        ai_ps_uploaded_message_ids=[],
        current_screen="start",
        # ai_ps_screen_message_id не трогаем
    )

    # 4) показать главное меню
    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id="start",
        as_new_message=False,
        push_history=False,
    )

    await callback.answer("Генерация фотосессии отменена 😞", show_alert=True)


# =====================================================================
# Back / Menu
# =====================================================================
@router.callback_query(F.data == "ai_ps_noop")
async def ai_ps_noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "ai_ps_back_to_gender")
async def ai_ps_back_to_gender(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AiPhotoshootStates.waiting_gender)
    await callback.message.edit_caption(
        caption=_intro_gender_text(),
        reply_markup=kb_gender(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "ai_ps_back_to_categories")
async def ai_ps_back_to_categories(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    gender = data.get("ai_ps_gender") or "male"
    await state.set_state(AiPhotoshootStates.waiting_category)
    await callback.message.edit_caption(
        caption=_intro_category_text(gender),
        reply_markup=kb_categories(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "ai_ps_back_to_menu")
async def ai_ps_back_to_menu(callback: CallbackQuery, state: FSMContext, bot: Bot):
    # ВАЖНО: не делаем state.clear() ДО show_screen.
    # state.clear() стирает screen_message_id/текущий экран, и show_screen вынужден
    # отправлять новое сообщение вместо редактирования текущего.

    data = await state.get_data()

    # Это то самое "экранное" сообщение, которое мы редактируем на протяжении сценария
    screen_mid = data.get("ai_ps_screen_message_id") or callback.message.message_id

    # Сбрасываем только сценарные поля, но сохраняем идентификатор экранного сообщения
    await state.set_state(None)
    await state.update_data(
        ai_ps_prev_screen=None,
        ai_ps_gender=None,
        ai_ps_category=None,
        ai_ps_uploaded_file_ids=[],
        ai_ps_uploaded_message_ids=[],
        ai_ps_screen_message_id=screen_mid,
        # На всякий случай сохраняем общий screen_message_id, если show_screen на него опирается
        screen_message_id=screen_mid,
        current_screen="start",
    )

    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id="start",
        as_new_message=False,
        push_history=False,
    )
    await callback.answer()
