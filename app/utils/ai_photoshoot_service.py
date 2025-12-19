from __future__ import annotations

import os
from typing import Optional

from aiogram import Bot
from aiogram.types import FSInputFile
from aiogram.exceptions import TelegramBadRequest

from app.utils.kie_nano_banana import KieNanoBananaClient


async def telegram_file_url_from_file_id(bot: Bot, file_id: str) -> str:
    tg_file = await bot.get_file(file_id)
    return f"https://api.telegram.org/file/bot{bot.token}/{tg_file.file_path}"


def _hardcoded_me_paths() -> list[str]:
    """
    app/static/me/1.jpg .. 5.jpg
    """
    base = "app/static/me"
    return [os.path.join(base, f"{i}.jpg") for i in range(1, 6)]


async def _telegram_file_url_for_local_photo(
    bot: Bot,
    local_path: str,
    *,
    upload_chat_id: int,
    fallback_chat_id: Optional[int] = None,
) -> str:
    """
    Загружает локальное фото в Telegram и возвращает публичный file URL.
    Если upload_chat_id недоступен — использует fallback_chat_id.
    """
    sent_chat_id = upload_chat_id

    try:
        msg = await bot.send_photo(
            chat_id=upload_chat_id,
            photo=FSInputFile(local_path),
            disable_notification=True,
        )
    except TelegramBadRequest:
        if fallback_chat_id is None:
            raise
        sent_chat_id = fallback_chat_id
        msg = await bot.send_photo(
            chat_id=fallback_chat_id,
            photo=FSInputFile(local_path),
            disable_notification=True,
        )

    file_id = msg.photo[-1].file_id
    file = await bot.get_file(file_id)
    file_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"

    # чистим временное сообщение
    try:
        await bot.delete_message(sent_chat_id, msg.message_id)
    except Exception:
        pass

    return file_url


def _flatten_prompts_for_choice(
    prompts_dict: dict,
    *,
    category_key: str,
    gender: str,  # "male" | "female"
    limit: int = 1,
) -> list[dict]:
    """
    Берём промты из AI_PHOTO_PROMPTS.

    Структура:
    category -> gender -> scenario_key -> { title, prompt }

    Возвращаем список dict'ов с prompt'ами.
    """

    out: list[dict] = []

    category = prompts_dict.get(category_key)
    if not isinstance(category, dict):
        return out

    gender_block = category.get(gender)
    if not isinstance(gender_block, dict):
        return out

    for scenario_key, scenario in gender_block.items():
        if not isinstance(scenario, dict):
            continue

        prompt = scenario.get("prompt")
        if not prompt:
            continue

        out.append(
            {
                "key": scenario_key,
                "title": scenario.get("title"),
                "prompt": prompt,
            }
        )

        if len(out) >= limit:
            break

    return out
# def _flatten_prompts_for_choice(
#     prompts_dict: dict,
#     *,
#     category_key: str,
#     gender: str,  # "male" | "female"
#     limit: int = 5,
# ) -> list[dict]:
#     """
#     Берём промты из структуры AI_PHOTO_PROMPTS.
#     Логика простая: идём по всем подкатегориям внутри category_key и собираем items.
#     """
#     cat = prompts_dict.get(category_key) or {}
#     out: list[dict] = []

#     for _, sub_val in cat.items():
#         if not isinstance(sub_val, dict):
#             continue
#         gender_block = sub_val.get(gender)
#         if isinstance(gender_block, dict):
#             items = gender_block.get("items") or []
#             for it in items:
#                 if isinstance(it, dict) and it.get("prompt"):
#                     out.append(it)
#                     if len(out) >= limit:
#                         return out

#     # если в category_key есть прямой gender (без подкатегорий)
#     gender_block = cat.get(gender)
#     if isinstance(gender_block, dict):
#         for it in (gender_block.get("items") or []):
#             if isinstance(it, dict) and it.get("prompt"):
#                 out.append(it)
#                 if len(out) >= limit:
#                     return out

#     return out[:limit]


async def generate_photoshoot_pack(
    bot: Bot,
    *,
    kie_api_key: str,
    ai_photo_prompts: dict,
    gender: str,                 # "male" | "female"
    category_key: str,           # например "animals"
    reference_file_ids: Optional[list[str]] = None,  # ✅ file_id фото пользователя (лучший вариант)
    public_static_base_url: Optional[str] = None,    # если вдруг хостишь статику сам
    dev_upload_chat_id: int = -1005080691714,        # чат для временной заливки локальных фото
    fallback_chat_id: Optional[int] = None,          # чат пользователя (на случай, если dev_chat недоступен)
) -> list[str]:
    """
    🔬 TEST MODE: генерирует 1 картинку по выбранной категории и полу.

    Приоритет reference-фото:
    1) reference_file_ids (фото, которые прислал пользователь) -> get_file -> file_url
    2) public_static_base_url + app/static/me/1..5.jpg
    3) upload локальных app/static/me/1..5.jpg в Telegram (dev_upload_chat_id/fallback_chat_id)
    """

    print("🧠 [AI] generate_photoshoot_pack START")
    print(f"→ gender={gender}, category={category_key}")

    if not gender or not category_key:
        raise RuntimeError("gender and category_key must be set before generation")

    # 1) берём ТОЛЬКО 1 промт
    items = _flatten_prompts_for_choice(
        ai_photo_prompts,
        category_key=category_key,
        gender=gender,
        limit=1,  # было 1
    )
    if not items:
        raise RuntimeError(f"No prompts for category={category_key}, gender={gender}")

    it = items[0]
    title = it.get("title") or "no-title"
    prompt = it.get("prompt") or ""
    print(f"✅ Prompt selected: {title} (len={len(prompt)})")

    # 2) reference image URLs
    image_urls: list[str] = []

    # 2.1) ПРИОРИТЕТ: фото пользователя (file_id)
    if reference_file_ids:
        print(f"📎 Using user reference_file_ids: {len(reference_file_ids)}")
        for fid in reference_file_ids[:5]:
            url = await telegram_file_url_from_file_id(bot, fid)
            print(f"   → file_id={fid[:18]}... → {url.replace(bot.token, '***TOKEN***')}")
            image_urls.append(url)

    # 2.2) fallback: локальные 1..5.jpg через public_static_base_url
    if not image_urls and public_static_base_url:
        local_paths = _hardcoded_me_paths()
        print("🌍 Using public static URLs for local references")
        image_urls = [f"{public_static_base_url}/{os.path.basename(p)}" for p in local_paths]

    # 2.3) fallback: заливка локальных фото в Telegram, чтобы получить file_url
    if not image_urls:
        local_paths = _hardcoded_me_paths()
        print(f"📸 Local reference photos: {local_paths}")
        print("📤 Uploading local reference images to Telegram")
        for path in local_paths:
            url = await _telegram_file_url_for_local_photo(
                bot,
                path,
                upload_chat_id=dev_upload_chat_id,
                fallback_chat_id=fallback_chat_id,
            )
            print(f"   → {path} → {url.replace(bot.token, '***TOKEN***')}")
            image_urls.append(url)

    if not image_urls:
        raise RuntimeError("No reference images resolved")

    print(f"✅ Reference images ready: {len(image_urls)}")

    # 3) создаём задачу (1 шт)
    client = KieNanoBananaClient(api_key=kie_api_key)
    results: list[str] = []

    for idx, it in enumerate(items, start=1):
        title = it.get("title") or f"prompt-{idx}"
        prompt = it.get("prompt") or ""

        print(f"🎨 [AI] Creating task {idx}/{len(items)}: {title} (len={len(prompt)})")

        task_id = await client.create_task(
            prompt=prompt,
            image_inputs=image_urls,
            aspect_ratio="9:16",
            resolution="1K",
            output_format="png",
            meta={
                "gender": gender,
                "category": category_key,
                "prompt_title": title,
                "idx": idx,
            },
        )

        done = await client.wait_images(
            task_id,
            poll_every_sec=2.0,
            max_wait_sec=360.0,
        )

        if not done.image_urls:
            raise RuntimeError(f"KIE returned empty result for task={task_id}")

        results.append(done.image_urls[0])
        print(f"✅ [AI] Done {idx}/{len(items)} → {done.image_urls[0]}")

    return results
# # app/services/ai_photoshoot_service.py

# from __future__ import annotations

# import os
# from typing import Optional

# from aiogram import Bot
# from aiogram.types import FSInputFile

# from app.utils.kie_nano_banana import KieNanoBananaClient
# from aiogram.exceptions import TelegramBadRequest


# async def telegram_file_url_from_file_id(bot: Bot, file_id: str) -> str:
#     tg_file = await bot.get_file(file_id)
#     return f"https://api.telegram.org/file/bot{bot.token}/{tg_file.file_path}"


# def _hardcoded_me_paths() -> list[str]:
#     """
#     app/static/me/1.jpg .. 5.jpg
#     """
#     base = "app/static/me"
#     return [os.path.join(base, f"{i}.jpg") for i in range(1, 6)]


# async def _telegram_file_url_for_local_photo(
#     bot: Bot,
#     local_path: str,
#     *,
#     upload_chat_id: int,
#     fallback_chat_id: Optional[int] = None,
# ) -> str:
#     """
#     Загружает локальное фото в Telegram и возвращает публичный file URL.
#     Если upload_chat_id недоступен — использует fallback_chat_id.
#     """
#     sent_chat_id = upload_chat_id

#     try:
#         msg = await bot.send_photo(
#             chat_id=upload_chat_id,
#             photo=FSInputFile(local_path),
#             disable_notification=True,
#         )
#     except TelegramBadRequest:
#         if fallback_chat_id is None:
#             raise
#         sent_chat_id = fallback_chat_id
#         msg = await bot.send_photo(
#             chat_id=fallback_chat_id,
#             photo=FSInputFile(local_path),
#             disable_notification=True,
#         )

#     file_id = msg.photo[-1].file_id
#     file = await bot.get_file(file_id)
#     file_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"

#     # чистим временное сообщение
#     try:
#         await bot.delete_message(sent_chat_id, msg.message_id)
#     except Exception:
#         pass

#     return file_url


# def _flatten_prompts_for_choice(
#     prompts_dict: dict,
#     *,
#     category_key: str,
#     gender: str,  # "male" | "female"
#     limit: int = 5,
# ) -> list[dict]:
#     """
#     Берём 5 промтов из структуры AI_PHOTO_PROMPTS.
#     Логика простая: идём по всем подкатегориям внутри category_key и собираем items.
#     """
#     cat = prompts_dict.get(category_key) or {}
#     out: list[dict] = []

#     for sub_key, sub_val in cat.items():
#         if not isinstance(sub_val, dict):
#             continue
#         gender_block = sub_val.get(gender)
#         if isinstance(gender_block, dict):
#             items = gender_block.get("items") or []
#             for it in items:
#                 if isinstance(it, dict) and it.get("prompt"):
#                     out.append(it)
#                     if len(out) >= limit:
#                         return out

#     # если в category_key есть прямой gender (без подкатегорий)
#     gender_block = cat.get(gender)
#     if isinstance(gender_block, dict):
#         for it in (gender_block.get("items") or []):
#             if isinstance(it, dict) and it.get("prompt"):
#                 out.append(it)
#                 if len(out) >= limit:
#                     return out

#     return out[:limit]


# # async def generate_photoshoot_pack(
# #     bot: Bot,
# #     *,
# #     kie_api_key: str,
# #     ai_photo_prompts: dict,
# #     gender: str,            # "male" | "female"
# #     category_key: str,      # например "animals"
# #     public_static_base_url: Optional[str] = None,  # https://site/static/me
# #     dev_upload_chat_id: int = -1005080691714,
# #     fallback_chat_id: Optional[int] = None,        # chat пользователя
# # ) -> list[str]:
# #     """
# #     Генерирует 5 картинок по выбранной категории и полу.
# #     Reference-фото берутся из app/static/me/1..5.jpg
# #     """

# #     # 1️⃣ проверка входных данных
# #     if not gender or not category_key:
# #         raise RuntimeError("gender and category_key must be set before generation")

# #     # 2️⃣ получаем 5 промтов
# #     items = _flatten_prompts_for_choice(
# #         ai_photo_prompts,
# #         category_key=category_key,
# #         gender=gender,
# #         limit=5,
# #     )
# #     if not items:
# #         raise RuntimeError(
# #             f"No prompts for category={category_key}, gender={gender}"
# #         )

# #     # 3️⃣ reference image URLs
# #     local_paths = _hardcoded_me_paths()

# #     if public_static_base_url:
# #         image_urls = [
# #             f"{public_static_base_url}/{os.path.basename(p)}"
# #             for p in local_paths
# #         ]
# #     else:
# #         image_urls = []
# #         for path in local_paths:
# #             image_urls.append(
# #                 await _telegram_file_url_for_local_photo(
# #                     bot,
# #                     path,
# #                     upload_chat_id=dev_upload_chat_id,
# #                     fallback_chat_id=fallback_chat_id,
# #                 )
# #             )

# #     # 4️⃣ создаём задачи генерации
# #     client = KieNanoBananaClient(api_key=kie_api_key)

# #     results: list[str] = []

# #     for it in items:
# #         task_id = await client.create_task(
# #             prompt=it["prompt"],
# #             image_inputs=image_urls,
# #             aspect_ratio="9:16",
# #             resolution="1K",
# #             output_format="png",
# #         )

# #         done = await client.wait_images(
# #             task_id,
# #             poll_every_sec=2.0,
# #             max_wait_sec=180.0,
# #         )

# #         if not done.image_urls:
# #             raise RuntimeError(f"KIE returned empty result for task={task_id}")

# #         results.append(done.image_urls[0])

# #     return results


# async def generate_photoshoot_pack(
#     bot: Bot,
#     *,
#     kie_api_key: str,
#     ai_photo_prompts: dict,
#     gender: str,                 # "male" | "female"
#     category_key: str,           # например "animals"
#     public_static_base_url: Optional[str] = None,
#     dev_upload_chat_id: int = -1005080691714,
#     fallback_chat_id: Optional[int] = None,
# ) -> list[str]:
#     """
#     🔬 TEST MODE
#     Генерирует 1 картинку по выбранной категории и полу.
#     Reference-фото берутся из app/static/me/1..5.jpg
#     """

#     print("🧠 [AI] generate_photoshoot_pack START")
#     print(f"→ gender={gender}, category={category_key}")

#     # 1️⃣ проверка входных данных
#     if not gender or not category_key:
#         raise RuntimeError("gender and category_key must be set before generation")

#     # 2️⃣ берём ТОЛЬКО 1 промт
#     items = _flatten_prompts_for_choice(
#         ai_photo_prompts,
#         category_key=category_key,
#         gender=gender,
#         limit=1,   # ⬅️ ВАЖНО
#     )

#     if not items:
#         raise RuntimeError(
#             f"No prompts for category={category_key}, gender={gender}"
#         )

#     it = items[0]
#     print(f"✅ Prompt selected: {it['title']} (len={len(it['prompt'])})")

#     # 3️⃣ reference image URLs
#     local_paths = _hardcoded_me_paths()
#     print(f"📸 Local reference photos: {local_paths}")

#     image_urls: list[str] = []

#     if public_static_base_url:
#         image_urls = [
#             f"{public_static_base_url}/{os.path.basename(p)}"
#             for p in local_paths
#         ]
#         print("🌍 Using public static URLs")
#     else:
#         print("📤 Uploading reference images to Telegram")
#         for path in local_paths:
#             url = await _telegram_file_url_for_local_photo(
#                 bot,
#                 path,
#                 upload_chat_id=dev_upload_chat_id,
#                 fallback_chat_id=fallback_chat_id,
#             )
#             safe_url = url.replace(bot.token, "***TOKEN***")
#             print(f"   → {path} → {safe_url}")
#             image_urls.append(url)

#     print(f"✅ Reference images ready: {len(image_urls)}")

#     # 4️⃣ создаём ОДНУ задачу
#     client = KieNanoBananaClient(api_key=kie_api_key)

#     print("🎨 [AI] Creating generation task (1 image)")

#     task_id = await client.create_task(
#         prompt=it["prompt"],
#         image_inputs=image_urls,
#         aspect_ratio="9:16",
#         resolution="1K",
#         output_format="png",
#         meta={
#             "gender": gender,
#             "category": category_key,
#             "prompt_title": it["title"],
#         },
#     )

#     print(f"⏳ [AI] Waiting for task {task_id}")

#     done = await client.wait_images(
#         task_id,
#         poll_every_sec=2.0,
#         max_wait_sec=180.0,
#     )

#     if not done.image_urls:
#         raise RuntimeError(f"KIE returned empty result for task={task_id}")

#     print("🎉 [AI] Image generated successfully")
#     print(f"→ {done.image_urls[0]}")

#     return [done.image_urls[0]]
