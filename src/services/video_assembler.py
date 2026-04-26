from __future__ import annotations

import asyncio
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AssemblyManifest:
    """Describes all artefacts needed to assemble a video.

    背景图与数字人视频二选一:
      * `background_image` 静态图模式 (CPU 即可)
      * `digital_human_video` 数字人模式 (GPU 渲染好的视频, 已对口型)
    """

    project_id: str
    audio_files: list[Path] = field(default_factory=list)
    subtitle_file: Path | None = None
    background_image: Path | None = None
    digital_human_video: Path | None = None
    bgm_file: Path | None = None
    output_path: Path | None = None


class VideoAssembler:
    """Assembles final video from audio, subtitles, and visuals.

    支持两种模式:
      * 静态图 + 多段音频拼接 (CPU 模式)
      * 数字人视频 + 字幕 (GPU 渲染输出后再拼字幕/BGM)

    若 ffmpeg 不在 PATH 中, 或输入文件不存在, 会自动回退到 dry-run
    (只返回输出路径, 不真正生成视频), 用于测试环境与无 ffmpeg 的 CI.
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg") -> None:
        self._ffmpeg = ffmpeg_path

    def _ffmpeg_available(self) -> bool:
        return shutil.which(self._ffmpeg) is not None

    def validate_manifest(self, manifest: AssemblyManifest) -> list[str]:
        errors: list[str] = []
        if not manifest.audio_files and manifest.digital_human_video is None:
            errors.append("No audio files provided")
        if manifest.output_path is None:
            errors.append("Output path is required")
        for af in manifest.audio_files:
            if af.suffix.lower() not in (".mp3", ".wav", ".ogg", ".m4a"):
                errors.append(f"Unsupported audio format: {af.suffix}")
        if manifest.subtitle_file and manifest.subtitle_file.suffix.lower() != ".srt":
            errors.append(
                f"Unsupported subtitle format: {manifest.subtitle_file.suffix}"
            )
        return errors

    def build_ffmpeg_command(self, manifest: AssemblyManifest) -> list[str]:
        errors = self.validate_manifest(manifest)
        if errors:
            raise ValueError(f"Invalid manifest: {'; '.join(errors)}")

        if manifest.digital_human_video is not None:
            return self._build_digital_human_command(manifest)
        return self._build_static_image_command(manifest)

    def _build_static_image_command(self, manifest: AssemblyManifest) -> list[str]:
        """ffmpeg 静态图 + 多段音频 concat + 字幕 + 可选 BGM"""
        cmd = [self._ffmpeg, "-y"]

        # 输入索引 0: 背景图 (loop)
        bg = manifest.background_image
        bg_index: int | None = None
        if bg is not None:
            cmd.extend(["-loop", "1", "-i", str(bg)])
            bg_index = 0

        # 然后输入音频
        audio_start = len(cmd)  # 不重要, 用计数
        first_audio_idx = (1 if bg_index is not None else 0)
        for af in manifest.audio_files:
            cmd.extend(["-i", str(af)])

        # 可选 BGM
        bgm_idx: int | None = None
        if manifest.bgm_file is not None:
            bgm_idx = first_audio_idx + len(manifest.audio_files)
            cmd.extend(["-stream_loop", "-1", "-i", str(manifest.bgm_file)])

        # filter_complex: concat 多段音频, 与 BGM 混音, 视频加字幕
        filter_parts: list[str] = []

        # 1) 拼接旁白
        narration_label = "[narr]"
        if len(manifest.audio_files) == 1:
            filter_parts.append(f"[{first_audio_idx}:a]anull{narration_label}")
        else:
            audio_in = "".join(
                f"[{first_audio_idx + i}:a]" for i in range(len(manifest.audio_files))
            )
            filter_parts.append(
                f"{audio_in}concat=n={len(manifest.audio_files)}:v=0:a=1{narration_label}"
            )

        # 2) 混入 BGM (旁白音量 1.0, BGM 0.15)
        audio_out_label = narration_label
        if bgm_idx is not None:
            filter_parts.append(
                f"{narration_label}volume=1.0[narrV];"
                f"[{bgm_idx}:a]volume=0.15[bgmV];"
                f"[narrV][bgmV]amix=inputs=2:duration=first:dropout_transition=0[aout]"
            )
            audio_out_label = "[aout]"

        # 3) 视频流: 背景图 → 加字幕
        video_out_label: str | None = None
        if bg_index is not None:
            if manifest.subtitle_file is not None:
                # ffmpeg subtitles filter 需要正斜杠 + 转义冒号
                sub_path = str(manifest.subtitle_file).replace("\\", "/").replace(":", "\\:")
                filter_parts.append(
                    f"[{bg_index}:v]subtitles='{sub_path}',scale=1280:720,setsar=1[vout]"
                )
            else:
                filter_parts.append(f"[{bg_index}:v]scale=1280:720,setsar=1[vout]")
            video_out_label = "[vout]"

        cmd.extend(["-filter_complex", ";".join(filter_parts)])

        if video_out_label:
            cmd.extend(["-map", video_out_label])
        cmd.extend(["-map", audio_out_label])

        if video_out_label:
            cmd.extend([
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-pix_fmt", "yuv420p",
                "-r", "25",
            ])
        cmd.extend([
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(manifest.output_path),
        ])
        return cmd

    def _build_digital_human_command(
        self, manifest: AssemblyManifest
    ) -> list[str]:
        """ffmpeg 数字人视频 + 字幕 + 可选 BGM (旁白音轨已在数字人视频中)"""
        cmd = [self._ffmpeg, "-y", "-i", str(manifest.digital_human_video)]

        bgm_idx: int | None = None
        if manifest.bgm_file is not None:
            cmd.extend(["-stream_loop", "-1", "-i", str(manifest.bgm_file)])
            bgm_idx = 1

        filter_parts: list[str] = []

        # 视频流: 加字幕
        if manifest.subtitle_file is not None:
            sub_path = str(manifest.subtitle_file).replace("\\", "/").replace(":", "\\:")
            filter_parts.append(f"[0:v]subtitles='{sub_path}'[vout]")
            video_out_label = "[vout]"
        else:
            video_out_label = "0:v"

        # 音频流: 数字人原音 + 可选 BGM
        if bgm_idx is not None:
            filter_parts.append(
                f"[0:a]volume=1.0[narrV];"
                f"[{bgm_idx}:a]volume=0.12[bgmV];"
                f"[narrV][bgmV]amix=inputs=2:duration=first:dropout_transition=0[aout]"
            )
            audio_out_label = "[aout]"
        else:
            audio_out_label = "0:a"

        if filter_parts:
            cmd.extend(["-filter_complex", ";".join(filter_parts)])

        cmd.extend(["-map", video_out_label, "-map", audio_out_label])
        cmd.extend([
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(manifest.output_path),
        ])
        return cmd

    async def assemble(self, manifest: AssemblyManifest) -> Path:
        """构建视频. 输入文件不存在或 ffmpeg 不可用时, 回退 dry-run 仅返回路径."""
        cmd = self.build_ffmpeg_command(manifest)
        assert manifest.output_path is not None
        manifest.output_path.parent.mkdir(parents=True, exist_ok=True)

        # dry-run 条件: 测试环境/缺 ffmpeg/输入文件不存在
        missing_inputs: list[str] = []
        for af in manifest.audio_files:
            if not af.exists():
                missing_inputs.append(str(af))
        if manifest.digital_human_video and not manifest.digital_human_video.exists():
            missing_inputs.append(str(manifest.digital_human_video))
        if manifest.background_image and not manifest.background_image.exists():
            missing_inputs.append(str(manifest.background_image))

        if missing_inputs or not self._ffmpeg_available():
            logger.warning(
                "Skipping ffmpeg execution (dry-run). missing_inputs=%s ffmpeg_available=%s",
                missing_inputs,
                self._ffmpeg_available(),
            )
            logger.info("FFmpeg command (would-run): %s", " ".join(cmd))
            return manifest.output_path

        logger.info("Running ffmpeg: %s", " ".join(cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace")
            logger.error("ffmpeg failed (code=%s): %s", proc.returncode, err[-2000:])
            raise RuntimeError(f"ffmpeg exited with {proc.returncode}: {err[-500:]}")

        logger.info("Video assembled: %s", manifest.output_path)
        return manifest.output_path
