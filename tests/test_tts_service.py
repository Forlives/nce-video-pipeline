from __future__ import annotations

from pathlib import Path

import pytest

from src.models.script import AdaptedScript
from src.services.tts_service import TTSService


class FakeTTSBackend:
    """Writes a stub file instead of calling a real TTS API."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Path]] = []

    async def synthesize(self, text: str, voice: str, output_path: Path) -> Path:
        self.calls.append((text, voice, output_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-audio-data")
        return output_path


class TestTTSService:
    @pytest.mark.asyncio
    async def test_generate_audio_creates_files(
        self, sample_script: AdaptedScript, tmp_output: Path
    ) -> None:
        backend = FakeTTSBackend()
        svc = TTSService(backend, voice="nova")

        paths = await svc.generate_audio(sample_script, tmp_output / "audio")

        assert len(paths) == 3
        assert all(p.exists() for p in paths)
        assert backend.calls[0][1] == "nova"

    @pytest.mark.asyncio
    async def test_generate_audio_filenames(
        self, sample_script: AdaptedScript, tmp_output: Path
    ) -> None:
        backend = FakeTTSBackend()
        svc = TTSService(backend)

        paths = await svc.generate_audio(sample_script, tmp_output / "audio")
        names = [p.name for p in paths]

        assert names == ["scene_001.mp3", "scene_002.mp3", "scene_003.mp3"]

    @pytest.mark.asyncio
    async def test_generate_single(self, tmp_output: Path) -> None:
        backend = FakeTTSBackend()
        svc = TTSService(backend)

        out = tmp_output / "single.mp3"
        result = await svc.generate_single("Hello world", out)

        assert result == out
        assert result.exists()
        assert len(backend.calls) == 1

    @pytest.mark.asyncio
    async def test_empty_script(self, tmp_output: Path) -> None:
        from src.models.script import AdaptedScript

        empty = AdaptedScript(lesson_id=99, title="Empty")
        backend = FakeTTSBackend()
        svc = TTSService(backend)

        paths = await svc.generate_audio(empty, tmp_output / "audio")

        assert paths == []
        assert backend.calls == []
