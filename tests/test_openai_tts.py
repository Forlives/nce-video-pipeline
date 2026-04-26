from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.openai_tts import OpenAITTSBackend


class TestOpenAITTSBackend:
    @pytest.mark.asyncio
    async def test_synthesize_creates_file(self, tmp_path: Path) -> None:
        backend = OpenAITTSBackend(
            api_key="test-key", base_url="https://fake.api/v1"
        )
        output = tmp_path / "audio" / "test.mp3"

        mock_resp = MagicMock()
        mock_resp.stream_to_file = MagicMock()

        with patch.object(
            backend._client.audio.speech, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_resp
            result = await backend.synthesize("Hello world", "alloy", output)

        assert result == output
        assert output.parent.exists()
        mock_create.assert_called_once_with(
            model="tts-1", voice="alloy", input="Hello world"
        )
        mock_resp.stream_to_file.assert_called_once_with(str(output))

    @pytest.mark.asyncio
    async def test_synthesize_creates_parent_dirs(self, tmp_path: Path) -> None:
        backend = OpenAITTSBackend(
            api_key="test-key", base_url="https://fake.api/v1"
        )
        deep_output = tmp_path / "a" / "b" / "c" / "speech.mp3"

        mock_resp = MagicMock()
        mock_resp.stream_to_file = MagicMock()

        with patch.object(
            backend._client.audio.speech, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_resp
            await backend.synthesize("Test", "nova", deep_output)

        assert deep_output.parent.exists()
