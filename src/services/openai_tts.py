from __future__ import annotations

import logging
from pathlib import Path

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class OpenAITTSBackend:
    """Concrete TTSBackend backed by the OpenAI TTS API."""

    def __init__(self, api_key: str, base_url: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def synthesize(self, text: str, voice: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        resp = await self._client.audio.speech.create(
            model="tts-1",
            voice=voice,  # type: ignore[arg-type]
            input=text,
        )
        resp.stream_to_file(str(output_path))
        logger.info("Synthesized %d chars → %s", len(text), output_path.name)
        return output_path
