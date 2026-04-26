from __future__ import annotations

from pathlib import Path

import pytest

from src.services.digital_human_service import (
    DigitalHumanConfig,
    DigitalHumanError,
    DigitalHumanService,
)


class TestDigitalHumanService:
    def test_disabled_when_url_empty(self) -> None:
        svc = DigitalHumanService(DigitalHumanConfig(api_url=""))
        assert svc.is_enabled is False

    def test_enabled_when_url_set(self) -> None:
        svc = DigitalHumanService(DigitalHumanConfig(api_url="http://localhost:8000"))
        assert svc.is_enabled is True

    @pytest.mark.asyncio
    async def test_generate_disabled_raises(self, tmp_path: Path) -> None:
        svc = DigitalHumanService(DigitalHumanConfig(api_url=""))
        with pytest.raises(DigitalHumanError):
            await svc.generate(
                reference_image=tmp_path / "a.png",
                audio_file=tmp_path / "a.mp3",
                output_path=tmp_path / "out.mp4",
            )

    @pytest.mark.asyncio
    async def test_generate_missing_reference_raises(self, tmp_path: Path) -> None:
        svc = DigitalHumanService(
            DigitalHumanConfig(api_url="http://localhost:8000")
        )
        with pytest.raises(FileNotFoundError):
            await svc.generate(
                reference_image=tmp_path / "missing.png",
                audio_file=tmp_path / "a.mp3",
                output_path=tmp_path / "out.mp4",
            )

    @pytest.mark.asyncio
    async def test_generate_missing_audio_raises(self, tmp_path: Path) -> None:
        ref = tmp_path / "ref.png"
        ref.write_bytes(b"\x89PNG\r\n\x1a\n")  # PNG header stub
        svc = DigitalHumanService(
            DigitalHumanConfig(api_url="http://localhost:8000")
        )
        with pytest.raises(FileNotFoundError):
            await svc.generate(
                reference_image=ref,
                audio_file=tmp_path / "missing.mp3",
                output_path=tmp_path / "out.mp4",
            )

    def test_headers_with_api_key(self) -> None:
        svc = DigitalHumanService(
            DigitalHumanConfig(api_url="http://x", api_key="secret")
        )
        h = svc._headers()  # type: ignore[attr-defined]
        assert h["Authorization"] == "Bearer secret"

    def test_headers_without_api_key(self) -> None:
        svc = DigitalHumanService(DigitalHumanConfig(api_url="http://x"))
        assert svc._headers() == {}  # type: ignore[attr-defined]
