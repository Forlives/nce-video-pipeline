"""Anthropic Claude 原生 API 客户端 (实现 LLMClient Protocol).

何时使用本模块:
  * 想直接用 Claude 官方 API (https://api.anthropic.com)
  * 不想走 OpenRouter / OneAPI 等 OpenAI 兼容代理

何时**不**使用:
  * 你的 key 是 OpenAI 兼容代理 (OpenRouter / DeepSeek / OneAPI / 火山兼容版)
    -> 这类 key 直接配到 OPENAI_API_KEY + OPENAI_BASE_URL + OPENAI_MODEL 即可
    -> 例: OPENAI_BASE_URL=https://openrouter.ai/api/v1, OPENAI_MODEL=anthropic/claude-3.5-sonnet

要启用本客户端, 在 main.py 的 _build_pipeline 里把:
    llm = OpenAILLMClient(...)
替换为:
    llm = AnthropicLLMClient(api_key=..., model=...)
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class AnthropicLLMClient:
    """直接调用 Anthropic Messages API."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        base_url: str = "https://api.anthropic.com",
        max_tokens: int = 4096,
        timeout: float = 120.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._max_tokens = max_tokens
        self._timeout = timeout

    async def chat(self, system: str, user: str) -> str:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "temperature": 0.7,
        }
        async with httpx.AsyncClient(
            base_url=self._base_url, timeout=self._timeout
        ) as client:
            resp = await client.post("/v1/messages", headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()

        # Anthropic 返回 {"content": [{"type":"text","text":"..."}], ...}
        parts = data.get("content", [])
        text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
        logger.debug("Anthropic response length: %d chars", len(text))
        return text
