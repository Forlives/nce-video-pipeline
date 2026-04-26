from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.routes import _run_pipeline_task, _projects, ProjectRecord
from src.models.lesson import Lesson
from src.models.video import VideoProject, VideoStatus


@pytest.fixture(autouse=True)
def _clear():
    _projects.clear()
    yield
    _projects.clear()


def _make_request(pipeline_mock: object) -> MagicMock:
    req = MagicMock()
    req.app.state.pipeline = pipeline_mock
    return req


def _seed_project(project_id: str, lesson_id: int = 1) -> ProjectRecord:
    record = ProjectRecord(
        project_id=project_id,
        lesson_id=lesson_id,
        title="Test",
    )
    _projects[project_id] = record
    return record


class TestRunPipelineTask:
    @pytest.mark.asyncio
    async def test_successful_run_updates_project(self) -> None:
        _seed_project("test123")

        mock_project = VideoProject(project_id="test123", lesson_id=1)
        mock_project.advance(VideoStatus.ASSEMBLED)

        pipeline = MagicMock()
        pipeline.run = AsyncMock(return_value=mock_project)
        request = _make_request(pipeline)

        lesson = Lesson(lesson_id=1, title="Test", text="Some text")
        await _run_pipeline_task(request, "test123", lesson, "modern_dialogue", [])

        assert _projects["test123"].status == VideoStatus.ASSEMBLED
        assert _projects["test123"].error_message is None

    @pytest.mark.asyncio
    async def test_failed_run_marks_project_failed(self) -> None:
        _seed_project("fail456", lesson_id=2)

        pipeline = MagicMock()
        pipeline.run = AsyncMock(side_effect=RuntimeError("LLM timeout"))
        request = _make_request(pipeline)

        lesson = Lesson(lesson_id=2, title="Fail", text="text")
        await _run_pipeline_task(request, "fail456", lesson, "story", [])

        assert _projects["fail456"].status == VideoStatus.FAILED
        assert "LLM timeout" in (_projects["fail456"].error_message or "")

    @pytest.mark.asyncio
    async def test_valid_platforms_passed_to_pipeline(self) -> None:
        _seed_project("plat789", lesson_id=3)

        mock_project = VideoProject(project_id="plat789", lesson_id=3)
        mock_project.advance(VideoStatus.PUBLISHED)

        pipeline = MagicMock()
        pipeline.run = AsyncMock(return_value=mock_project)
        request = _make_request(pipeline)

        lesson = Lesson(lesson_id=3, title="Plat", text="text")
        await _run_pipeline_task(
            request, "plat789", lesson, "modern_dialogue", ["bilibili", "youtube"]
        )

        call_kwargs = pipeline.run.call_args[1]
        from src.services.publisher import Platform

        assert Platform.BILIBILI in call_kwargs["platforms"]
        assert Platform.YOUTUBE in call_kwargs["platforms"]

    @pytest.mark.asyncio
    async def test_empty_platforms_passes_none(self) -> None:
        _seed_project("empty000", lesson_id=4)

        mock_project = VideoProject(project_id="empty000", lesson_id=4)
        mock_project.advance(VideoStatus.ASSEMBLED)

        pipeline = MagicMock()
        pipeline.run = AsyncMock(return_value=mock_project)
        request = _make_request(pipeline)

        lesson = Lesson(lesson_id=4, title="Empty", text="text")
        await _run_pipeline_task(request, "empty000", lesson, "story", [])

        call_kwargs = pipeline.run.call_args[1]
        assert call_kwargs["platforms"] is None

    @pytest.mark.asyncio
    async def test_missing_project_is_noop(self) -> None:
        pipeline = MagicMock()
        pipeline.run = AsyncMock()
        request = _make_request(pipeline)

        lesson = Lesson(lesson_id=1, title="Ghost", text="text")
        await _run_pipeline_task(request, "nonexistent", lesson, "story", [])

        pipeline.run.assert_not_called()
