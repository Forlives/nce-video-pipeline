from __future__ import annotations

import json
import logging
from typing import Protocol

from src.models.lesson import Lesson
from src.models.script import AdaptedScript, ScriptScene

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an expert scriptwriter for educational English-learning short videos.
Given a New Concept English lesson, adapt it into a modern, engaging short-video
script with multiple scenes.  Each scene must include:
- English narration (natural, conversational)
- Chinese translation
- Stage direction for visuals
- Key vocabulary to highlight

Return ONLY valid JSON matching this schema (no markdown fences):
{
  "title": "...",
  "style": "modern_dialogue | story | sitcom",
  "scenes": [
    {
      "scene_number": 1,
      "narration_en": "...",
      "narration_cn": "...",
      "stage_direction": "...",
      "vocabulary_highlight": ["word1"],
      "duration_seconds": 10
    }
  ]
}
"""


class LLMClient(Protocol):
    """Minimal interface for an LLM backend."""

    async def chat(self, system: str, user: str) -> str: ...


class ScriptGenerator:
    """Generates adapted video scripts from NCE lessons via an LLM."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def generate(
        self, lesson: Lesson, style: str = "modern_dialogue"
    ) -> AdaptedScript:
        user_prompt = (
            f"Lesson {lesson.lesson_id}: {lesson.title}\n"
            f"Level: {lesson.level.value}\n"
            f"Style requested: {style}\n\n"
            f"Original text:\n{lesson.text}\n\n"
            f"Key vocabulary: {', '.join(lesson.vocabulary)}\n"
            f"Grammar points: {', '.join(lesson.grammar_points)}"
        )

        raw = await self._llm.chat(SYSTEM_PROMPT, user_prompt)
        return self._parse_response(lesson.lesson_id, raw)

    @staticmethod
    def _parse_response(lesson_id: int, raw: str) -> AdaptedScript:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("LLM returned invalid JSON: %s", text[:200])
            raise ValueError(f"LLM response is not valid JSON: {exc}") from exc

        scenes = [ScriptScene(**s) for s in data.get("scenes", [])]
        script = AdaptedScript(
            lesson_id=lesson_id,
            title=data.get("title", ""),
            style=data.get("style", "modern_dialogue"),
            scenes=scenes,
        )
        script.compute_duration()
        return script
