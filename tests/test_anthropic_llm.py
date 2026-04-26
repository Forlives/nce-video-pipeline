from __future__ import annotations

import pytest
import respx
from httpx import Response

from src.services.anthropic_llm import AnthropicLLMClient


class TestAnthropicLLMClient:
    @pytest.mark.asyncio
    @respx.mock
    async def test_chat_returns_text(self) -> None:
        respx.post("https://api.anthropic.com/v1/messages").mock(
            return_value=Response(
                200,
                json={
                    "id": "msg_x",
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Hello from Claude"}],
                },
            )
        )

        client = AnthropicLLMClient(api_key="sk-ant-xxx", model="claude-3-5-sonnet-20241022")
        text = await client.chat("system", "user")
        assert text == "Hello from Claude"

    @pytest.mark.asyncio
    @respx.mock
    async def test_chat_concatenates_multiple_text_parts(self) -> None:
        respx.post("https://api.anthropic.com/v1/messages").mock(
            return_value=Response(
                200,
                json={
                    "content": [
                        {"type": "text", "text": "Part 1 "},
                        {"type": "text", "text": "Part 2"},
                        {"type": "tool_use", "name": "ignored"},
                    ],
                },
            )
        )
        client = AnthropicLLMClient(api_key="sk-ant-xxx")
        text = await client.chat("system", "user")
        assert text == "Part 1 Part 2"

    @pytest.mark.asyncio
    @respx.mock
    async def test_chat_raises_on_http_error(self) -> None:
        respx.post("https://api.anthropic.com/v1/messages").mock(
            return_value=Response(401, json={"error": {"message": "invalid key"}}),
        )
        client = AnthropicLLMClient(api_key="sk-bad")
        with pytest.raises(Exception):
            await client.chat("s", "u")
