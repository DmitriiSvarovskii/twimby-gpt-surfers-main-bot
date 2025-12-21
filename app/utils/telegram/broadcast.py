from aiogram import types
import asyncio
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest, TelegramRetryAfter
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from app.config import settings
from app.services.mailling.mail import mark_blocked
from app.keyboard.start import kb_after_photos


async def broadcast_job(
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    admin_tg_id: int,
    recipients: list[int],
    payload: dict,
) -> None:
    sent = 0
    blocked = 0
    failed = 0

    for tg_id in recipients:
        try:
            await send_payload(bot, tg_id, payload)
            sent += 1
            await asyncio.sleep(settings.BROADCAST_GLOBAL_DELAY)

        except TelegramRetryAfter as e:
            await asyncio.sleep(float(e.retry_after) + 0.5)

        except TelegramForbiddenError:
            blocked += 1
            async with session_factory() as s:
                await mark_blocked(s, tg_id)

        except TelegramBadRequest as e:
            failed += 1
            print(f"[broadcast] bad_request tg_id={tg_id} payload_type={payload.get('type')} err={e}")

        except Exception as e:
            failed += 1
            print(f"[broadcast] unknown tg_id={tg_id} payload_type={payload.get('type')} err={e}")

    await bot.send_message(
        chat_id=admin_tg_id,
        text=(
            "📣 Рассылка завершена.\n"
            f"✅ Отправлено: {sent}\n"
            f"⛔️ Заблокировали бота: {blocked}\n"
            f"⚠️ Ошибок: {failed}"
        ),
        reply_markup=kb_after_photos(),
    )


def serialize_message(m: types.Message) -> dict:
    # текст
    if m.text:
        return {
            "type": "text",
            "text": m.text,
            "entities": m.entities,   # важно для ссылок/жирного и т.п.
        }

    # подпись (caption) + сущности подписи
    caption = m.caption or None
    caption_entities = m.caption_entities or None

    # медиа по file_id
    if m.photo:
        return {"type": "photo", "file_id": m.photo[-1].file_id, "caption": caption, "caption_entities": caption_entities}
    if m.video:
        return {"type": "video", "file_id": m.video.file_id, "caption": caption, "caption_entities": caption_entities}
    if m.document:
        return {"type": "document", "file_id": m.document.file_id, "caption": caption, "caption_entities": caption_entities}
    if m.audio:
        return {"type": "audio", "file_id": m.audio.file_id, "caption": caption, "caption_entities": caption_entities}
    if m.voice:
        return {"type": "voice", "file_id": m.voice.file_id, "caption": caption, "caption_entities": caption_entities}
    if m.animation:
        return {"type": "animation", "file_id": m.animation.file_id, "caption": caption, "caption_entities": caption_entities}
    if m.sticker:
        return {"type": "sticker", "file_id": m.sticker.file_id}
    if m.video_note:
        return {
            "type": "video_note",
            "file_id": m.video_note.file_id,
        }

    # если прилетело что-то “неподдерживаемое”
    return {"type": "unsupported"}


async def send_payload(bot, chat_id: int, payload: dict):
    t = payload["type"]

    if t == "text":
        return await bot.send_message(chat_id, payload["text"], entities=payload.get("entities"))

    kw = {}
    if payload.get("caption") is not None:
        kw["caption"] = payload["caption"]
    if payload.get("caption_entities") is not None:
        kw["caption_entities"] = payload["caption_entities"]

    if t == "photo":
        return await bot.send_photo(chat_id, payload["file_id"], **kw)
    if t == "video":
        return await bot.send_video(chat_id, payload["file_id"], **kw)
    if t == "document":
        return await bot.send_document(chat_id, payload["file_id"], **kw)
    if t == "audio":
        return await bot.send_audio(chat_id, payload["file_id"], **kw)
    if t == "voice":
        return await bot.send_voice(chat_id, payload["file_id"], **kw)
    if t == "animation":
        return await bot.send_animation(chat_id, payload["file_id"], **kw)
    if t == "sticker":
        return await bot.send_sticker(chat_id, payload["file_id"])
    if t == "video_note":
        return await bot.send_video_note(chat_id, payload["file_id"])
    raise ValueError(f"Unsupported payload type: {t}")
