from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class Platform(str, Enum):
    DOUYIN = "douyin"
    BILIBILI = "bilibili"
    XIAOHONGSHU = "xiaohongshu"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"


@dataclass
class PublishResult:
    platform: Platform
    success: bool
    url: str | None = None
    error: str | None = None


class Publisher:
    """Publishes videos to social media platforms.

    Each platform would have its own API adapter in production.
    This implementation provides the routing logic and a stub adapter.
    """

    def __init__(self) -> None:
        self._adapters: dict[Platform, object] = {}

    def register_adapter(self, platform: Platform, adapter: object) -> None:
        self._adapters[platform] = adapter

    def supported_platforms(self) -> list[Platform]:
        return list(self._adapters.keys())

    async def publish(
        self,
        video_path: Path,
        title: str,
        description: str,
        platforms: list[Platform],
        tags: list[str] | None = None,
    ) -> list[PublishResult]:
        results: list[PublishResult] = []

        for platform in platforms:
            if platform not in self._adapters:
                results.append(
                    PublishResult(
                        platform=platform,
                        success=False,
                        error=f"No adapter registered for {platform.value}",
                    )
                )
                continue

            try:
                logger.info("Publishing to %s: %s", platform.value, title)
                # Stub: in production, call platform-specific upload API
                results.append(
                    PublishResult(
                        platform=platform,
                        success=True,
                        url=f"https://{platform.value}.com/video/stub-id",
                    )
                )
            except Exception as exc:
                logger.error("Failed to publish to %s: %s", platform.value, exc)
                results.append(
                    PublishResult(
                        platform=platform, success=False, error=str(exc)
                    )
                )

        return results
