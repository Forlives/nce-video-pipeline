from __future__ import annotations

import logging
from pathlib import Path

from src.models.script import AdaptedScript

logger = logging.getLogger(__name__)


class SubtitleService:
    """Generates SRT subtitle files from an adapted script."""

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def generate_srt(self, script: AdaptedScript, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        current_time = 0.0

        for scene in script.scenes:
            start = self._format_timestamp(current_time)
            end = self._format_timestamp(current_time + scene.duration_seconds)

            lines.append(str(scene.scene_number))
            lines.append(f"{start} --> {end}")
            lines.append(scene.narration_en)
            if scene.narration_cn:
                lines.append(scene.narration_cn)
            lines.append("")

            current_time += scene.duration_seconds

        output_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Generated SRT with %d cues at %s", len(script.scenes), output_path)
        return output_path

    def generate_bilingual_srt(
        self, script: AdaptedScript, output_path: Path
    ) -> Path:
        """Generate SRT with vocabulary highlights appended."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        current_time = 0.0

        for scene in script.scenes:
            start = self._format_timestamp(current_time)
            end = self._format_timestamp(current_time + scene.duration_seconds)

            lines.append(str(scene.scene_number))
            lines.append(f"{start} --> {end}")
            lines.append(scene.narration_en)
            if scene.narration_cn:
                lines.append(scene.narration_cn)
            if scene.vocabulary_highlight:
                lines.append(f"[Key: {', '.join(scene.vocabulary_highlight)}]")
            lines.append("")

            current_time += scene.duration_seconds

        output_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(
            "Generated bilingual SRT with %d cues at %s",
            len(script.scenes),
            output_path,
        )
        return output_path
