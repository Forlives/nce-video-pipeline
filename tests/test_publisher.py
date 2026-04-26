from __future__ import annotations

from pathlib import Path

import pytest

from src.services.publisher import Publisher, Platform, PublishResult


class TestPublisher:
    def test_no_adapters_initially(self) -> None:
        pub = Publisher()
        assert pub.supported_platforms() == []

    def test_register_adapter(self) -> None:
        pub = Publisher()
        pub.register_adapter(Platform.BILIBILI, object())
        assert Platform.BILIBILI in pub.supported_platforms()

    @pytest.mark.asyncio
    async def test_publish_no_adapter_returns_error(
        self, tmp_path: Path
    ) -> None:
        pub = Publisher()
        results = await pub.publish(
            video_path=tmp_path / "video.mp4",
            title="Test",
            description="Desc",
            platforms=[Platform.DOUYIN],
        )

        assert len(results) == 1
        assert results[0].success is False
        assert "No adapter registered" in (results[0].error or "")

    @pytest.mark.asyncio
    async def test_publish_with_adapter_succeeds(
        self, tmp_path: Path
    ) -> None:
        pub = Publisher()
        pub.register_adapter(Platform.BILIBILI, object())

        results = await pub.publish(
            video_path=tmp_path / "video.mp4",
            title="Test",
            description="Desc",
            platforms=[Platform.BILIBILI],
        )

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].url is not None

    @pytest.mark.asyncio
    async def test_publish_mixed_platforms(self, tmp_path: Path) -> None:
        pub = Publisher()
        pub.register_adapter(Platform.YOUTUBE, object())

        results = await pub.publish(
            video_path=tmp_path / "video.mp4",
            title="Test",
            description="Desc",
            platforms=[Platform.YOUTUBE, Platform.TIKTOK],
        )

        assert len(results) == 2
        youtube_result = next(r for r in results if r.platform == Platform.YOUTUBE)
        tiktok_result = next(r for r in results if r.platform == Platform.TIKTOK)

        assert youtube_result.success is True
        assert tiktok_result.success is False

    @pytest.mark.asyncio
    async def test_publish_empty_platforms(self, tmp_path: Path) -> None:
        pub = Publisher()
        results = await pub.publish(
            video_path=tmp_path / "video.mp4",
            title="Test",
            description="Desc",
            platforms=[],
        )

        assert results == []
