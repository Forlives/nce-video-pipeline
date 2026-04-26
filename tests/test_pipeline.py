from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.models.lesson import Lesson
from src.models.script import AdaptedScript
from src.models.video import VideoStatus
from src.pipeline.pipeline import VideoPipeline
from src.services.publisher import Platform, Publisher
from src.services.script_generator import ScriptGenerator
from src.services.subtitle_service import SubtitleService
from src.services.tts_service import TTSService
from src.services.video_assembler import VideoAssembler


class FakeLLM:
    def __init__(self, script_json: str) -> None:
        self._resp = script_json

    async def chat(self, system: str, user: str) -> str:
        return self._resp


class FakeTTSBackend:
    async def synthesize(self, text: str, voice: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"audio")
        return output_path


def _build_pipeline(
    tmp_path: Path,
    script_json: str,
    register_platforms: list[Platform] | None = None,
) -> VideoPipeline:
    llm = FakeLLM(script_json)
    gen = ScriptGenerator(llm)
    tts = TTSService(FakeTTSBackend())
    sub = SubtitleService()
    asm = VideoAssembler()
    pub = Publisher()
    if register_platforms:
        for p in register_platforms:
            pub.register_adapter(p, object())
    return VideoPipeline(gen, tts, sub, asm, pub, tmp_path / "output")


class TestPipeline:
    @pytest.mark.asyncio
    async def test_full_pipeline_no_publish(
        self, sample_lesson: Lesson, sample_script_json: str, tmp_path: Path
    ) -> None:
        pipeline = _build_pipeline(tmp_path, sample_script_json)
        project = await pipeline.run(sample_lesson)

        assert project.status == VideoStatus.ASSEMBLED
        assert project.script_path is not None
        assert project.audio_path is not None
        assert project.subtitle_path is not None
        assert project.video_path is not None
        assert project.error_message is None

    @pytest.mark.asyncio
    async def test_full_pipeline_with_publish(
        self, sample_lesson: Lesson, sample_script_json: str, tmp_path: Path
    ) -> None:
        pipeline = _build_pipeline(
            tmp_path,
            sample_script_json,
            register_platforms=[Platform.BILIBILI],
        )
        project = await pipeline.run(
            sample_lesson, platforms=[Platform.BILIBILI]
        )

        assert project.status == VideoStatus.PUBLISHED

    @pytest.mark.asyncio
    async def test_pipeline_publish_failure(
        self, sample_lesson: Lesson, sample_script_json: str, tmp_path: Path
    ) -> None:
        pipeline = _build_pipeline(tmp_path, sample_script_json)
        project = await pipeline.run(
            sample_lesson, platforms=[Platform.DOUYIN]
        )

        assert project.status == VideoStatus.FAILED
        assert "Publishing failed" in (project.error_message or "")

    @pytest.mark.asyncio
    async def test_pipeline_script_failure(
        self, sample_lesson: Lesson, tmp_path: Path
    ) -> None:
        pipeline = _build_pipeline(tmp_path, "NOT JSON")
        project = await pipeline.run(sample_lesson)

        assert project.status == VideoStatus.FAILED
        assert project.error_message is not None

    @pytest.mark.asyncio
    async def test_pipeline_creates_artefact_directory(
        self, sample_lesson: Lesson, sample_script_json: str, tmp_path: Path
    ) -> None:
        pipeline = _build_pipeline(tmp_path, sample_script_json)
        project = await pipeline.run(sample_lesson)

        proj_dir = tmp_path / "output" / project.project_id
        assert proj_dir.exists()
        assert (proj_dir / "script.json").exists()
        assert (proj_dir / "subtitles.srt").exists()
