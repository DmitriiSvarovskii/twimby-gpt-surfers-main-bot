from aiogram.types import (
    InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAudio
)
from aiogram.types import InputMediaPhoto, InputMediaVideo
from aiogram.types import MessageEntity
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


def _dump_entities(entities: list[types.MessageEntity] | None):
    if not entities:
        return None
    return [e.model_dump() for e in entities]


def serialize_message(m: types.Message) -> dict:
    # текст
    if m.text:
        return {
            "type": "text",
            "text": m.text,
            "entities": _dump_entities(m.entities),
        }

    caption = m.caption or None
    caption_entities = _dump_entities(m.caption_entities)

    # общие флаги для медиа
    has_spoiler = bool(getattr(m, "has_media_spoiler", False))
    show_caption_above = getattr(m, "show_caption_above_media", None)

    if m.photo:
        return {
            "type": "photo",
            "file_id": m.photo[-1].file_id,
            "caption": caption,
            "caption_entities": caption_entities,
            "has_spoiler": has_spoiler,
            "show_caption_above_media": show_caption_above,
        }

    if m.video:
        return {
            "type": "video",
            "file_id": m.video.file_id,
            "caption": caption,
            "caption_entities": caption_entities,
            "has_spoiler": has_spoiler,
            "show_caption_above_media": show_caption_above,
        }

    if m.document:
        return {
            "type": "document",
            "file_id": m.document.file_id,
            "caption": caption,
            "caption_entities": caption_entities,
            "has_spoiler": has_spoiler,
            "show_caption_above_media": show_caption_above,
        }

    if m.audio:
        return {"type": "audio", "file_id": m.audio.file_id, "caption": caption, "caption_entities": caption_entities}

    if m.voice:
        return {"type": "voice", "file_id": m.voice.file_id, "caption": caption, "caption_entities": caption_entities}

    if m.animation:
        return {
            "type": "animation",
            "file_id": m.animation.file_id,
            "caption": caption,
            "caption_entities": caption_entities,
            "has_spoiler": has_spoiler,
            "show_caption_above_media": show_caption_above,
        }

    if m.sticker:
        return {"type": "sticker", "file_id": m.sticker.file_id}

    if m.video_note:
        return {"type": "video_note", "file_id": m.video_note.file_id}

    return {"type": "unsupported"}


def serialize_media_group_item(m: types.Message) -> dict:
    # фото
    if m.photo:
        return {
            "type": "photo",
            "file_id": m.photo[-1].file_id,
            "has_spoiler": bool(getattr(m, "has_media_spoiler", False)),
        }

    # видео
    if m.video:
        return {
            "type": "video",
            "file_id": m.video.file_id,
            "has_spoiler": bool(getattr(m, "has_media_spoiler", False)),
        }

    # документ (PDF сюда тоже попадает)
    if m.document:
        return {
            "type": "document",
            "file_id": m.document.file_id,
            # spoiler для document НЕ существует
        }

    # аудио (если надо)
    if m.audio:
        return {
            "type": "audio",
            "file_id": m.audio.file_id,
        }

    return {"type": "unsupported"}
# def serialize_media_group_item(m: types.Message) -> dict:
#     has_spoiler = bool(getattr(m, "has_media_spoiler", False))

#     if m.photo:
#         return {"type": "photo", "file_id": m.photo[-1].file_id, "has_spoiler": has_spoiler}
#     if m.video:
#         return {"type": "video", "file_id": m.video.file_id, "has_spoiler": has_spoiler}

#     return {"type": "unsupported"}


def _load_entities(entities: list[dict] | None):
    if not entities:
        return None
    return [MessageEntity(**e) for e in entities]


# async def send_payload(bot: Bot, chat_id: int, payload: dict):
#     t = payload["type"]

#     if t == "text":
#         return await bot.send_message(
#             chat_id,
#             payload["text"],
#             entities=_load_entities(payload.get("entities")),
#             parse_mode=None,
#         )

#     # ✅ альбом
#     if t == "media_group":
#         caption = payload.get("caption")
#         caption_entities = _load_entities(payload.get("caption_entities"))

#         media = []
#         for i, it in enumerate(payload["items"]):
#             it_type = it["type"]
#             file_id = it["file_id"]
#             has_spoiler = bool(it.get("has_spoiler", False))

#             # caption + entities только на первом элементе
#             c = caption if i == 0 else None
#             ce = caption_entities if i == 0 else None

#             if it_type == "photo":
#                 media.append(InputMediaPhoto(media=file_id, caption=c, caption_entities=ce, has_spoiler=has_spoiler))
#             elif it_type == "video":
#                 media.append(InputMediaVideo(media=file_id, caption=c, caption_entities=ce, has_spoiler=has_spoiler))
#             else:
#                 raise ValueError(f"Unsupported media_group item type: {it_type}")

#         # show_caption_above_media у send_media_group нет — Telegram не даёт это для альбомов стабильно
#         return await bot.send_media_group(chat_id=chat_id, media=media)

#     # ✅ одиночные медиа
#     kw = {"parse_mode": None}

#     if payload.get("caption") is not None:
#         kw["caption"] = payload["caption"]
#     if payload.get("caption_entities") is not None:
#         kw["caption_entities"] = _load_entities(payload["caption_entities"])

#     if payload.get("has_spoiler") is not None:
#         kw["has_spoiler"] = bool(payload["has_spoiler"])

#     if payload.get("show_caption_above_media") is not None:
#         kw["show_caption_above_media"] = payload["show_caption_above_media"]

#     if t == "photo":
#         return await bot.send_photo(chat_id, payload["file_id"], **kw)
#     if t == "video":
#         return await bot.send_video(chat_id, payload["file_id"], **kw)
#     if t == "document":
#         return await bot.send_document(chat_id, payload["file_id"], **kw)
#     if t == "audio":
#         return await bot.send_audio(chat_id, payload["file_id"], **kw)
#     if t == "voice":
#         return await bot.send_voice(chat_id, payload["file_id"], **kw)
#     if t == "animation":
#         return await bot.send_animation(chat_id, payload["file_id"], **kw)
#     if t == "sticker":
#         return await bot.send_sticker(chat_id, payload["file_id"])
#     if t == "video_note":
#         return await bot.send_video_note(chat_id, payload["file_id"])

#     raise ValueError(f"Unsupported payload type: {t}")


async def send_payload(bot: Bot, chat_id: int, payload: dict):
    t = payload["type"]

    # ✅ текст
    if t == "text":
        return await bot.send_message(
            chat_id,
            payload["text"],
            entities=_load_entities(payload.get("entities")),
            parse_mode=None,
        )

    # ✅ batch: последовательная отправка нескольких файлов (PDF/документы/что угодно)
    # if t == "batch":
    #     last_msg = None
    #     for i, it in enumerate(payload["items"]):
    #         it_type = it["type"]
    #         file_id = it["file_id"]

    #         kw = {"parse_mode": None}

    #         if it.get("caption") is not None:
    #             kw["caption"] = it["caption"]
    #         if it.get("caption_entities") is not None:
    #             kw["caption_entities"] = _load_entities(it["caption_entities"])

    #         # ⛔️ НЕ добавляем has_spoiler по умолчанию

    #         if it_type in ("photo", "video"):
    #             if it.get("has_spoiler") is not None:
    #                 kw["has_spoiler"] = bool(it["has_spoiler"])

    #         if it_type == "document":
    #             last_msg = await bot.send_document(chat_id, file_id, **kw)

    #         elif it_type == "photo":
    #             last_msg = await bot.send_photo(chat_id, file_id, **kw)

    #         elif it_type == "video":
    #             last_msg = await bot.send_video(chat_id, file_id, **kw)

    #         else:
    #             raise ValueError(f"Unsupported batch item type: {it_type}")

    #         await asyncio.sleep(settings.BROADCAST_GLOBAL_DELAY)

    #     return last_msg

    # ✅ media_group: только фото/видео
    if t == "media_group":
        caption = payload.get("caption")
        caption_entities = _load_entities(payload.get("caption_entities"))

        media = []
        for i, it in enumerate(payload["items"]):
            it_type = it["type"]
            file_id = it["file_id"]

            # caption + entities только на первом элементе
            c = caption if i == 0 else None
            ce = caption_entities if i == 0 else None

            # ВАЖНО: если передаём entities — parse_mode должен быть None (а не Default)
            pm = None if i == 0 else None

            if it_type == "photo":
                media.append(
                    InputMediaPhoto(
                        media=file_id,
                        caption=c,
                        caption_entities=ce,
                        parse_mode=pm,
                        has_spoiler=bool(it.get("has_spoiler", False)),
                    )
                )
            elif it_type == "video":
                media.append(
                    InputMediaVideo(
                        media=file_id,
                        caption=c,
                        caption_entities=ce,
                        parse_mode=pm,
                        has_spoiler=bool(it.get("has_spoiler", False)),
                    )
                )
            elif it_type == "document":
                media.append(
                    InputMediaDocument(
                        media=file_id,
                        caption=c,
                        caption_entities=ce,
                        parse_mode=pm,
                        # у document нет has_spoiler
                    )
                )
            elif it_type == "audio":
                media.append(
                    InputMediaAudio(
                        media=file_id,
                        caption=c,
                        caption_entities=ce,
                        parse_mode=pm,
                    )
                )
            else:
                raise ValueError(f"Unsupported media_group item type: {it_type}")

        return await bot.send_media_group(chat_id=chat_id, media=media)

    # ✅ одиночные медиа
    kw = {"parse_mode": None}

    if payload.get("caption") is not None:
        kw["caption"] = payload["caption"]
    if payload.get("caption_entities") is not None:
        kw["caption_entities"] = _load_entities(payload["caption_entities"])

    if payload.get("has_spoiler") is not None:
        kw["has_spoiler"] = bool(payload["has_spoiler"])

    if payload.get("show_caption_above_media") is not None:
        kw["show_caption_above_media"] = payload["show_caption_above_media"]

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
