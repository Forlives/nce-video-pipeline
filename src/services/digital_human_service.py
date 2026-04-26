"""InfiniteTalk 数字人 HTTP 客户端.

设计原则:
* 此模块不依赖任何 GPU 库, 只是 HTTP 调用.
* 假设 InfiniteTalk 服务以 HTTP API 形式部署在 GPU 服务器(如 RTX 3090 Ti),
  约定接口见 docs/INFINITETALK_DEPLOY.md.
* 接口约定:
    POST /api/digital-human/generate
        multipart 上传 reference_image (jpg/png) + audio (mp3/wav)
        参数: resolution=480p|720p, mode=image2video|video2video
        返回: { "task_id": "..." }
    GET  /api/digital-human/status/{task_id}
        返回: { "status": "pending|running|done|failed", "progress": 0-100, "video_url": "...", "error": "..." }
    GET  /api/digital-human/download/{task_id}
        返回 mp4 二进制
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class DigitalHumanConfig:
    api_url: str
    timeout: float = 1800.0  # 默认最长等 30 分钟
    poll_interval: float = 5.0
    api_key: Optional[str] = None  # 可选: 自定义 token, 通过 Authorization: Bearer
    resolution: str = "480p"  # 480p / 720p
    mode: str = "image2video"  # image2video / video2video


class DigitalHumanError(RuntimeError):
    """InfiniteTalk 任务失败 / 超时."""


class DigitalHumanService:
    """通过 HTTP 调用部署在 GPU 服务器上的 InfiniteTalk."""

    def __init__(self, config: DigitalHumanConfig) -> None:
        self._config = config

    @property
    def is_enabled(self) -> bool:
        return bool(self._config.api_url)

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {}
        if self._config.api_key:
            h["Authorization"] = f"Bearer {self._config.api_key}"
        return h

    async def generate(
        self,
        reference_image: Path,
        audio_file: Path,
        output_path: Path,
    ) -> Path:
        """生成数字人视频. 上传参考图与音频, 等待完成, 下载到 output_path."""
        if not self.is_enabled:
            raise DigitalHumanError("DigitalHumanService disabled (api_url empty)")

        if not reference_image.exists():
            raise FileNotFoundError(f"reference image not found: {reference_image}")
        if not audio_file.exists():
            raise FileNotFoundError(f"audio file not found: {audio_file}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(
            base_url=self._config.api_url.rstrip("/"),
            timeout=httpx.Timeout(self._config.timeout, connect=30.0),
            headers=self._headers(),
        ) as client:
            task_id = await self._submit(client, reference_image, audio_file)
            logger.info("InfiniteTalk task submitted: %s", task_id)

            await self._wait_until_done(client, task_id)
            await self._download(client, task_id, output_path)

        logger.info("Digital human video saved: %s", output_path)
        return output_path

    async def _submit(
        self, client: httpx.AsyncClient, reference_image: Path, audio_file: Path
    ) -> str:
        files = {
            "reference_image": (reference_image.name, reference_image.read_bytes()),
            "audio": (audio_file.name, audio_file.read_bytes()),
        }
        data = {
            "resolution": self._config.resolution,
            "mode": self._config.mode,
        }
        resp = await client.post(
            "/api/digital-human/generate", files=files, data=data
        )
        resp.raise_for_status()
        body = resp.json()
        task_id = body.get("task_id")
        if not task_id:
            raise DigitalHumanError(f"submit returned no task_id: {body}")
        return str(task_id)

    async def _wait_until_done(
        self, client: httpx.AsyncClient, task_id: str
    ) -> None:
        deadline = asyncio.get_event_loop().time() + self._config.timeout
        last_progress = -1
        while True:
            if asyncio.get_event_loop().time() > deadline:
                raise DigitalHumanError(f"task {task_id} timed out")

            resp = await client.get(f"/api/digital-human/status/{task_id}")
            resp.raise_for_status()
            body = resp.json()
            status = (body.get("status") or "").lower()
            progress = int(body.get("progress", 0))

            if progress != last_progress:
                logger.info(
                    "InfiniteTalk %s: %s %s%%", task_id, status, progress
                )
                last_progress = progress

            if status == "done":
                return
            if status == "failed":
                raise DigitalHumanError(
                    f"task {task_id} failed: {body.get('error') or body}"
                )

            await asyncio.sleep(self._config.poll_interval)

    async def _download(
        self, client: httpx.AsyncClient, task_id: str, output_path: Path
    ) -> None:
        async with client.stream(
            "GET", f"/api/digital-human/download/{task_id}"
        ) as resp:
            resp.raise_for_status()
            with output_path.open("wb") as f:
                async for chunk in resp.aiter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
