from __future__ import annotations

import json

import pytest

from src.models.lesson import Lesson
from src.models.script import AdaptedScript
from src.services.script_generator import ScriptGenerator


class FakeLLM:
    """Returns pre-canned JSON for testing."""

    def __init__(self, response: str) -> None:
        self._response = response

    async def chat(self, system: str, user: str) -> str:
        return self._response


class TestScriptGenerator:
    @pytest.mark.asyncio
    async def test_generate_valid_json(
        self, sample_lesson: Lesson, sample_script_json: str
    ) -> None:
        llm = FakeLLM(sample_script_json)
        gen = ScriptGenerator(llm)
        result = await gen.generate(sample_lesson)

        assert isinstance(result, AdaptedScript)
        assert result.lesson_id == 1
        assert len(result.scenes) == 3
        assert result.total_duration_seconds > 0

    @pytest.mark.asyncio
    async def test_generate_strips_markdown_fences(
        self, sample_lesson: Lesson, sample_script_json: str
    ) -> None:
        wrapped = f"```json\n{sample_script_json}\n```"
        llm = FakeLLM(wrapped)
        gen = ScriptGenerator(llm)
        result = await gen.generate(sample_lesson)

        assert len(result.scenes) == 3

    @pytest.mark.asyncio
    async def test_generate_invalid_json_raises(
        self, sample_lesson: Lesson
    ) -> None:
        llm = FakeLLM("this is not json at all")
        gen = ScriptGenerator(llm)

        with pytest.raises(ValueError, match="not valid JSON"):
            await gen.generate(sample_lesson)

    @pytest.mark.asyncio
    async def test_generate_empty_scenes(self, sample_lesson: Lesson) -> None:
        llm = FakeLLM(json.dumps({"title": "Empty", "style": "story", "scenes": []}))
        gen = ScriptGenerator(llm)
        result = await gen.generate(sample_lesson)

        assert result.scenes == []
        assert result.total_duration_seconds == 0.0

    @pytest.mark.asyncio
    async def test_generate_preserves_style(self, sample_lesson: Lesson) -> None:
        data = {
            "title": "Sitcom",
            "style": "sitcom",
            "scenes": [
                {
                    "scene_number": 1,
                    "narration_en": "Hello!",
                    "duration_seconds": 5,
                }
            ],
        }
        llm = FakeLLM(json.dumps(data))
        gen = ScriptGenerator(llm)
        result = await gen.generate(sample_lesson, style="sitcom")

        assert result.style == "sitcom"
