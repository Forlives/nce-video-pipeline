from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

from src.models.script import AdaptedScript

logger = logging.getLogger(__name__)


class TTSBackend(Protocol):
    """Minimal interface for a TTS provider."""

    async def synthesize(self, text: str, voice: str, output_path: Path) -> Path: ...


class TTSService:
    """Generates audio files for each scene of an adapted script."""

    def __init__(self, backend: TTSBackend, voice: str = "alloy") -> None:
        self._backend = backend
        self._voice = voice

    async def generate_audio(
        self, script: AdaptedScript, output_dir: Path
    ) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_paths: list[Path] = []

        for scene in script.scenes:
            filename = f"scene_{scene.scene_number:03d}.mp3"
            out_path = output_dir / filename

            logger.info(
                "Generating audio for scene %d (%d chars)",
                scene.scene_number,
                len(scene.narration_en),
            )
            result = await self._backend.synthesize(
                scene.narration_en, self._voice, out_path
            )
            audio_paths.append(result)

        logger.info(
            "Generated %d audio files for lesson %d",
            len(audio_paths),
            script.lesson_id,
        )
        return audio_paths

    async def generate_single(self, text: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return await self._backend.synthesize(text, self._voice, output_path)
