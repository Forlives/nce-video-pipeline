from __future__ import annotations

from pathlib import Path

import pytest

from src.services.video_assembler import VideoAssembler, AssemblyManifest


class TestVideoAssembler:
    def test_validate_valid_manifest(self, tmp_path: Path) -> None:
        manifest = AssemblyManifest(
            project_id="test",
            audio_files=[tmp_path / "a.mp3"],
            output_path=tmp_path / "out.mp4",
        )
        assembler = VideoAssembler()
        errors = assembler.validate_manifest(manifest)

        assert errors == []

    def test_validate_no_audio(self, tmp_path: Path) -> None:
        manifest = AssemblyManifest(
            project_id="test",
            audio_files=[],
            output_path=tmp_path / "out.mp4",
        )
        assembler = VideoAssembler()
        errors = assembler.validate_manifest(manifest)

        assert "No audio files provided" in errors

    def test_validate_no_output(self, tmp_path: Path) -> None:
        manifest = AssemblyManifest(
            project_id="test",
            audio_files=[tmp_path / "a.mp3"],
        )
        assembler = VideoAssembler()
        errors = assembler.validate_manifest(manifest)

        assert "Output path is required" in errors

    def test_validate_bad_audio_format(self, tmp_path: Path) -> None:
        manifest = AssemblyManifest(
            project_id="test",
            audio_files=[tmp_path / "a.txt"],
            output_path=tmp_path / "out.mp4",
        )
        assembler = VideoAssembler()
        errors = assembler.validate_manifest(manifest)

        assert any("Unsupported audio format" in e for e in errors)

    def test_validate_bad_subtitle_format(self, tmp_path: Path) -> None:
        manifest = AssemblyManifest(
            project_id="test",
            audio_files=[tmp_path / "a.mp3"],
            subtitle_file=tmp_path / "subs.txt",
            output_path=tmp_path / "out.mp4",
        )
        assembler = VideoAssembler()
        errors = assembler.validate_manifest(manifest)

        assert any("Unsupported subtitle format" in e for e in errors)

    def test_build_command_single_audio(self, tmp_path: Path) -> None:
        manifest = AssemblyManifest(
            project_id="test",
            audio_files=[tmp_path / "a.mp3"],
            output_path=tmp_path / "out.mp4",
        )
        assembler = VideoAssembler()
        cmd = assembler.build_ffmpeg_command(manifest)

        assert cmd[0] == "ffmpeg"
        assert "-y" in cmd
        assert str(tmp_path / "a.mp3") in cmd

    def test_build_command_multiple_audio_concat(self, tmp_path: Path) -> None:
        manifest = AssemblyManifest(
            project_id="test",
            audio_files=[tmp_path / "a.mp3", tmp_path / "b.mp3"],
            output_path=tmp_path / "out.mp4",
        )
        assembler = VideoAssembler()
        cmd = assembler.build_ffmpeg_command(manifest)

        assert "-filter_complex" in cmd
        assert any("concat" in c for c in cmd)

    def test_build_command_with_subtitles(self, tmp_path: Path) -> None:
        # Subtitles only render when there's a video stream (background image
        # or digital human video). Plain audio-only assembly skips subtitles.
        manifest = AssemblyManifest(
            project_id="test",
            audio_files=[tmp_path / "a.mp3"],
            subtitle_file=tmp_path / "subs.srt",
            background_image=tmp_path / "bg.png",
            output_path=tmp_path / "out.mp4",
        )
        assembler = VideoAssembler()
        cmd = assembler.build_ffmpeg_command(manifest)

        assert "-filter_complex" in cmd
        assert any("subtitles=" in c for c in cmd)

    def test_build_command_with_background(self, tmp_path: Path) -> None:
        manifest = AssemblyManifest(
            project_id="test",
            audio_files=[tmp_path / "a.mp3"],
            background_image=tmp_path / "bg.png",
            output_path=tmp_path / "out.mp4",
        )
        assembler = VideoAssembler()
        cmd = assembler.build_ffmpeg_command(manifest)

        assert "-loop" in cmd

    def test_build_command_invalid_raises(self, tmp_path: Path) -> None:
        manifest = AssemblyManifest(project_id="test")
        assembler = VideoAssembler()

        with pytest.raises(ValueError, match="Invalid manifest"):
            assembler.build_ffmpeg_command(manifest)

    @pytest.mark.asyncio
    async def test_assemble_returns_path(self, tmp_path: Path) -> None:
        manifest = AssemblyManifest(
            project_id="test",
            audio_files=[tmp_path / "a.mp3"],
            output_path=tmp_path / "out.mp4",
        )
        assembler = VideoAssembler()
        result = await assembler.assemble(manifest)

        assert result == tmp_path / "out.mp4"
