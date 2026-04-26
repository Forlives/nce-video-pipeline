from __future__ import annotations

import logging

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class OpenAILLMClient:
    """Concrete LLMClient backed by the OpenAI chat completions API."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def chat(self, system: str, user: str) -> str:
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
        )
        content = resp.choices[0].message.content or ""
        logger.debug("LLM response length: %d chars", len(content))
        return content
