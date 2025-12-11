# app/router/experts.py

from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    FSInputFile,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
)
from aiogram.exceptions import TelegramBadRequest

from app.lexicon import experts as experts_lexicon
from app.navigation import show_screen

router = Router()

EXPERTS = [
    {"key": "expert_ilya", "photo": "app/static/expert/Илья_Шитов.jpg"},
    {"key": "expert_alexander", "photo": "app/static/expert/Александр_Масленников.jpg"},
    {"key": "expert_eduard", "photo": "app/static/expert/Эдуард_Эргашев.jpg"},
    {"key": "expert_mikhail", "photo": "app/static/expert/МИША.jpg"},
    {"key": "expert_maxim", "photo": "app/static/expert/МАКС.jpg"},
]

TOTAL_EXPERTS = len(EXPERTS)


def build_experts_keyboard(index: int) -> InlineKeyboardMarkup:
    center = f"{index + 1}/{TOTAL_EXPERTS}"
    keyboard = [
        [
            InlineKeyboardButton(text="←", callback_data="experts_prev"),
            InlineKeyboardButton(text=center, callback_data="experts_page_info"),
            InlineKeyboardButton(text="→", callback_data="experts_next"),
        ],
        [
            InlineKeyboardButton(text="Назад", callback_data="experts_back"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.callback_query(F.data == "experts")
async def open_experts(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Вписываемся в концепцию "одного экранного сообщения":
    - previous_screen берём из current_screen
    - попытка отредактировать текущее экранное сообщение в карточку эксперта
    - если редактирование медиа не удалось (там был текст и т.п.) — удаляем и шлём новое фото
    - screen_message_id всегда указывает на карточку эксперта
    """
    data = await state.get_data()
    prev_screen = data.get("current_screen") or "start"
    screen_message_id = data.get("screen_message_id")
    chat_id = callback.message.chat.id

    # первый эксперт по умолчанию
    index = 0
    expert_cfg = EXPERTS[index]
    text_key = expert_cfg["key"]
    text = experts_lexicon.TEXTS[text_key]
    photo_path = expert_cfg["photo"]

    media = InputMediaPhoto(
        media=FSInputFile(photo_path),
        caption=text,
    )

    msg_obj = None

    if screen_message_id:
        # пытаемся превратить текущий "экран" в карточку эксперта
        try:
            msg_obj = await bot.edit_message_media(
                chat_id=chat_id,
                message_id=screen_message_id,
                media=media,
                reply_markup=build_experts_keyboard(index),
            )
        except TelegramBadRequest:
            # не получилось (например, там был чистый текст) — удаляем и создаём новый экран
            try:
                await bot.delete_message(chat_id, screen_message_id)
            except Exception:
                pass

            msg_obj = await callback.message.answer_photo(
                photo=FSInputFile(photo_path),
                caption=text,
                reply_markup=build_experts_keyboard(index),
            )
    else:
        # экранного сообщения ещё нет — просто шлём карточку
        msg_obj = await callback.message.answer_photo(
            photo=FSInputFile(photo_path),
            caption=text,
            reply_markup=build_experts_keyboard(index),
        )

    await state.update_data(
        experts_index=index,
        experts_prev_screen=prev_screen,
        current_screen="experts",
        screen_message_id=msg_obj.message_id,
    )

    await callback.answer()


@router.callback_query(F.data.in_(["experts_prev", "experts_next"]))
async def experts_switch(callback: CallbackQuery, state: FSMContext):
    """
    Листаем внутри одного и того же screen_message_id (карточки эксперта).
    Вписывается в концепцию: мы не создаём новые сообщения, а редактируем текущее.
    """
    data = await state.get_data()
    index = data.get("experts_index", 0)

    if callback.data == "experts_next":
        index = (index + 1) % TOTAL_EXPERTS
    else:
        index = (index - 1) % TOTAL_EXPERTS

    await state.update_data(experts_index=index)

    expert_cfg = EXPERTS[index]
    text_key = expert_cfg["key"]
    text = experts_lexicon.TEXTS[text_key]
    photo = FSInputFile(expert_cfg["photo"])

    media = InputMediaPhoto(
        media=photo,
        caption=text,

    )

    await callback.message.edit_media(
        media=media,
        reply_markup=build_experts_keyboard(index),
    )

    await callback.answer()


@router.callback_query(F.data == "experts_page_info")
async def experts_page_info(callback: CallbackQuery):
    await callback.answer()  # просто ничего не делаем


@router.callback_query(F.data == "experts_back")
async def experts_back(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Кнопка "Назад" в разделе экспертов:
    - НЕ удаляем сообщение
    - просто отдаём его под управление show_screen,
      который заменит фото+caption на текст предыдущего экрана.
    """
    data = await state.get_data()
    prev_screen = data.get("experts_prev_screen") or "academy"

    await show_screen(
        target=callback,
        state=state,
        bot=bot,
        screen_id=prev_screen,
        as_new_message=False,   # редактируем текущее сообщение
        push_history=False,     # это шаг "назад", историю не расширяем
    )

    await callback.answer()
