# app/utils/kie_nano_banana.py
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Optional, List, Callable, Any

import aiohttp


@dataclass
class KieTaskResult:
    task_id: str
    state: str                     # waiting | queuing | generating | success | fail
    image_urls: List[str]
    fail_msg: str = ""
    raw: dict | None = None         # сырой ответ для дебага


class KieNanoBananaClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.kie.ai",
        *,
        debug: bool = False,
        logger: Optional[Callable[[str], Any]] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.debug = debug
        self.log = logger or (print if debug else (lambda *_args, **_kw: None))

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _ts(self) -> str:
        return time.strftime("%H:%M:%S")

    def _d(self, msg: str) -> None:
        # единый формат логов
        self.log(f"[KIE {self._ts()}] {msg}")

    async def create_task(
        self,
        *,
        prompt: str,
        image_inputs: list[str],
        aspect_ratio: str = "9:16",
        resolution: str = "1K",
        output_format: str = "png",
        callBackUrl: Optional[str] = None,
        model: str = "nano-banana-pro",
        meta: Optional[dict] = None,   # для контекста в логах
    ) -> str:
        url = f"{self.base_url}/api/v1/jobs/createTask"
        payload = {
            "model": model,
            "input": {
                "prompt": prompt,
                "image_input": image_inputs,
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
                "output_format": output_format,
            },
        }
        if callBackUrl:
            payload["callBackUrl"] = callBackUrl

        m = meta or {}
        self._d(
            "createTask → POST "
            f"url={url} model={model} aspect={aspect_ratio} res={resolution} fmt={output_format} "
            f"refs={len(image_inputs)} prompt_len={len(prompt)} meta={m}"
        )

        async with aiohttp.ClientSession(headers=self._headers) as session:
            async with session.post(url, json=payload) as resp:
                body = await resp.json(content_type=None)

                self._d(f"createTask ← http={resp.status} body_code={body.get('code')} msg={body.get('msg')}")
                if self.debug:
                    # осторожно: prompt не печатаем целиком
                    self._d(f"createTask body.data={body.get('data')}")

                if resp.status != 200:
                    raise RuntimeError(f"KIE createTask failed: http={resp.status}, body={body}")
                if body.get("code") != 200:
                    raise RuntimeError(f"KIE createTask failed: body={body}")

                task_id = body["data"]["taskId"]
                self._d(f"createTask OK task_id={task_id}")
                return task_id

    async def get_task(self, task_id: str) -> KieTaskResult:
        # правильный endpoint
        url = f"{self.base_url}/api/v1/jobs/recordInfo"
        params = {"taskId": task_id}

        self._d(f"recordInfo → GET url={url} taskId={task_id}")

        async with aiohttp.ClientSession(headers=self._headers) as session:
            async with session.get(url, params=params) as resp:
                body = await resp.json(content_type=None)

                self._d(f"recordInfo ← http={resp.status} body_code={body.get('code')} msg={body.get('msg')}")
                if self.debug:
                    self._d(f"recordInfo body.data(keys)={list((body.get('data') or {}).keys())}")

                if resp.status != 200:
                    raise RuntimeError(f"KIE recordInfo failed: http={resp.status}, body={body}")
                if body.get("code") != 200:
                    raise RuntimeError(f"KIE recordInfo failed: body={body}")

                d = body.get("data") or {}
                state = (d.get("state") or "").strip()
                fail_msg = d.get("failMsg") or ""

                image_urls: list[str] = []
                result_json = d.get("resultJson") or ""

                if state == "success":
                    self._d("recordInfo state=success → parsing resultJson")
                    if result_json:
                        try:
                            parsed = json.loads(result_json)
                            image_urls = parsed.get("resultUrls") or []
                            self._d(f"resultJson parsed urls={len(image_urls)}")
                            if self.debug and image_urls:
                                self._d(f"first_url={image_urls[0]}")
                        except Exception as e:
                            self._d(f"resultJson parse ERROR: {e}")
                            image_urls = []
                    else:
                        self._d("resultJson is empty on success (unexpected)")

                elif state == "fail":
                    self._d(f"recordInfo state=fail failMsg={fail_msg}")

                else:
                    self._d(f"recordInfo state={state}")

                return KieTaskResult(
                    task_id=task_id,
                    state=state,
                    image_urls=image_urls,
                    fail_msg=fail_msg,
                    raw=body if self.debug else None,
                )

    async def wait_images(
        self,
        task_id: str,
        *,
        poll_every_sec: float = 2.0,
        max_wait_sec: float = 600.0,
    ) -> KieTaskResult:
        self._d(f"wait_images start task={task_id} poll={poll_every_sec}s timeout={max_wait_sec}s")

        deadline = asyncio.get_event_loop().time() + max_wait_sec
        last: Optional[KieTaskResult] = None
        polls = 0

        while asyncio.get_event_loop().time() < deadline:
            polls += 1
            self._d(f"wait_images poll#{polls}")
            last = await self.get_task(task_id)

            if last.state == "success":
                self._d(f"wait_images DONE success task={task_id} urls={len(last.image_urls)} polls={polls}")
                return last

            if last.state == "fail":
                self._d(f"wait_images DONE fail task={task_id} msg={last.fail_msg}")
                raise RuntimeError(f"KIE task failed: task={task_id}, msg={last.fail_msg}")

            await asyncio.sleep(poll_every_sec)

        self._d(f"wait_images TIMEOUT task={task_id} last_state={getattr(last, 'state', None)} polls={polls}")
        raise TimeoutError(f"KIE task timeout: task={task_id}, last_state={getattr(last, 'state', None)}")
