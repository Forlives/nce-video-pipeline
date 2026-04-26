from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models.lesson import Lesson, LessonLevel
from src.models.script import AdaptedScript, ScriptScene
from src.models.video import VideoProject, VideoStatus


class TestLesson:
    def test_valid_lesson(self, sample_lesson: Lesson) -> None:
        assert sample_lesson.lesson_id == 1
        assert sample_lesson.title == "Excuse me!"
        assert sample_lesson.level == LessonLevel.BEGINNER
        assert len(sample_lesson.vocabulary) == 4

    def test_lesson_requires_positive_id(self) -> None:
        with pytest.raises(ValidationError):
            Lesson(lesson_id=0, title="Bad", text="text")

    def test_lesson_requires_title(self) -> None:
        with pytest.raises(ValidationError):
            Lesson(lesson_id=1, title="", text="text")

    def test_lesson_requires_text(self) -> None:
        with pytest.raises(ValidationError):
            Lesson(lesson_id=1, title="Title", text="")

    def test_lesson_default_level(self) -> None:
        lesson = Lesson(lesson_id=1, title="T", text="Some text")
        assert lesson.level == LessonLevel.BEGINNER

    def test_lesson_all_levels(self) -> None:
        for level in LessonLevel:
            lesson = Lesson(lesson_id=1, title="T", text="text", level=level)
            assert lesson.level == level


class TestScriptScene:
    def test_valid_scene(self) -> None:
        scene = ScriptScene(scene_number=1, narration_en="Hello")
        assert scene.scene_number == 1
        assert scene.duration_seconds == 10.0

    def test_scene_number_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            ScriptScene(scene_number=0, narration_en="Hello")

    def test_scene_requires_narration(self) -> None:
        with pytest.raises(ValidationError):
            ScriptScene(scene_number=1, narration_en="")

    def test_scene_defaults(self) -> None:
        scene = ScriptScene(scene_number=1, narration_en="Hi")
        assert scene.narration_cn == ""
        assert scene.stage_direction == ""
        assert scene.vocabulary_highlight == []
        assert scene.duration_seconds == 10.0


class TestAdaptedScript:
    def test_compute_duration(self, sample_script: AdaptedScript) -> None:
        assert sample_script.total_duration_seconds == 21.0

    def test_empty_script_duration(self) -> None:
        script = AdaptedScript(lesson_id=1, title="Empty")
        assert script.compute_duration() == 0.0

    def test_single_scene(self) -> None:
        scene = ScriptScene(
            scene_number=1, narration_en="Hi", duration_seconds=5.0
        )
        script = AdaptedScript(lesson_id=1, title="Single", scenes=[scene])
        assert script.compute_duration() == 5.0


class TestVideoProject:
    def test_initial_status(self) -> None:
        vp = VideoProject(project_id="abc123", lesson_id=1)
        assert vp.status == VideoStatus.PENDING
        assert vp.error_message is None

    def test_advance(self) -> None:
        vp = VideoProject(project_id="abc123", lesson_id=1)
        vp.advance(VideoStatus.SCRIPT_READY)
        assert vp.status == VideoStatus.SCRIPT_READY

    def test_advance_with_kwargs(self, tmp_path) -> None:
        vp = VideoProject(project_id="abc123", lesson_id=1)
        p = tmp_path / "script.json"
        vp.advance(VideoStatus.SCRIPT_READY, script_path=p)
        assert vp.script_path == p

    def test_fail(self) -> None:
        vp = VideoProject(project_id="abc123", lesson_id=1)
        vp.fail("Something broke")
        assert vp.status == VideoStatus.FAILED
        assert vp.error_message == "Something broke"

    def test_advance_ignores_unknown_kwargs(self) -> None:
        vp = VideoProject(project_id="abc123", lesson_id=1)
        vp.advance(VideoStatus.AUDIO_READY, nonexistent_field="value")
        assert vp.status == VideoStatus.AUDIO_READY
