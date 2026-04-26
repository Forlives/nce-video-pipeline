from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.openai_llm import OpenAILLMClient


class TestOpenAILLMClient:
    @pytest.mark.asyncio
    async def test_chat_returns_content(self) -> None:
        client = OpenAILLMClient(
            api_key="test-key", base_url="https://fake.api/v1", model="gpt-test"
        )

        mock_choice = MagicMock()
        mock_choice.message.content = '{"title": "test"}'
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]

        with patch.object(
            client._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_resp
            result = await client.chat("system prompt", "user prompt")

        assert result == '{"title": "test"}'
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["model"] == "gpt-test"
        assert len(call_kwargs["messages"]) == 2

    @pytest.mark.asyncio
    async def test_chat_handles_none_content(self) -> None:
        client = OpenAILLMClient(
            api_key="test-key", base_url="https://fake.api/v1", model="gpt-test"
        )

        mock_choice = MagicMock()
        mock_choice.message.content = None
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]

        with patch.object(
            client._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_resp
            result = await client.chat("sys", "usr")

        assert result == ""
