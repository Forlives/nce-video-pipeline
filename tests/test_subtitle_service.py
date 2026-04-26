from __future__ import annotations

from pathlib import Path

import pytest

from src.models.script import AdaptedScript, ScriptScene
from src.services.subtitle_service import SubtitleService


class TestSubtitleService:
    def test_format_timestamp(self) -> None:
        svc = SubtitleService()
        assert svc._format_timestamp(0.0) == "00:00:00,000"
        assert svc._format_timestamp(61.5) == "00:01:01,500"
        assert svc._format_timestamp(3661.123) == "01:01:01,123"

    def test_generate_srt(
        self, sample_script: AdaptedScript, tmp_output: Path
    ) -> None:
        svc = SubtitleService()
        out = tmp_output / "test.srt"
        result = svc.generate_srt(sample_script, out)

        assert result.exists()
        content = result.read_text(encoding="utf-8")

        assert "00:00:00,000 --> 00:00:08,000" in content
        assert "Excuse me, is this your bag?" in content
        assert "打扰一下，这是你的包吗？" in content

    def test_generate_srt_sequential_timing(self, tmp_output: Path) -> None:
        scenes = [
            ScriptScene(
                scene_number=1,
                narration_en="First",
                duration_seconds=10.0,
            ),
            ScriptScene(
                scene_number=2,
                narration_en="Second",
                duration_seconds=5.0,
            ),
        ]
        script = AdaptedScript(lesson_id=1, title="Test", scenes=scenes)

        svc = SubtitleService()
        out = tmp_output / "timing.srt"
        svc.generate_srt(script, out)
        content = out.read_text(encoding="utf-8")

        assert "00:00:00,000 --> 00:00:10,000" in content
        assert "00:00:10,000 --> 00:00:15,000" in content

    def test_generate_bilingual_srt_includes_vocab(
        self, sample_script: AdaptedScript, tmp_output: Path
    ) -> None:
        svc = SubtitleService()
        out = tmp_output / "bilingual.srt"
        result = svc.generate_bilingual_srt(sample_script, out)

        content = result.read_text(encoding="utf-8")
        assert "[Key: excuse, bag]" in content
        assert "[Key: thank you]" in content

    def test_empty_script_produces_empty_srt(self, tmp_output: Path) -> None:
        script = AdaptedScript(lesson_id=1, title="Empty")
        svc = SubtitleService()
        out = tmp_output / "empty.srt"
        svc.generate_srt(script, out)

        content = out.read_text(encoding="utf-8")
        assert content.strip() == ""

    def test_srt_creates_parent_dirs(self, tmp_path: Path) -> None:
        script = AdaptedScript(
            lesson_id=1,
            title="Test",
            scenes=[ScriptScene(scene_number=1, narration_en="Hi")],
        )
        svc = SubtitleService()
        deep_path = tmp_path / "a" / "b" / "c" / "test.srt"
        svc.generate_srt(script, deep_path)

        assert deep_path.exists()
