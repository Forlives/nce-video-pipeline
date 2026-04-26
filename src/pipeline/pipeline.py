from __future__ import annotations

import logging
import uuid
from pathlib import Path

from src.models.lesson import Lesson
from src.models.script import AdaptedScript
from src.models.video import VideoProject, VideoStatus
from src.services.digital_human_service import DigitalHumanError, DigitalHumanService
from src.services.script_generator import ScriptGenerator
from src.services.tts_service import TTSService
from src.services.subtitle_service import SubtitleService
from src.services.video_assembler import VideoAssembler, AssemblyManifest
from src.services.publisher import Publisher, Platform

logger = logging.getLogger(__name__)


class VideoPipeline:
    """Orchestrates the full content-production pipeline:
    Lesson → Script → Audio → Subtitles → (DigitalHuman) → Video → Publish

    Digital Human step is optional: enabled only when DigitalHumanService.is_enabled.
    """

    def __init__(
        self,
        script_gen: ScriptGenerator,
        tts: TTSService,
        subtitle: SubtitleService,
        assembler: VideoAssembler,
        publisher: Publisher,
        output_dir: Path,
        digital_human: DigitalHumanService | None = None,
        digital_human_reference: Path | None = None,
        background_image: Path | None = None,
        bgm_file: Path | None = None,
    ) -> None:
        self._script_gen = script_gen
        self._tts = tts
        self._subtitle = subtitle
        self._assembler = assembler
        self._publisher = publisher
        self._output_dir = output_dir
        self._digital_human = digital_human
        self._digital_human_reference = digital_human_reference
        self._background_image = background_image
        self._bgm_file = bgm_file

    def _project_dir(self, project_id: str) -> Path:
        d = self._output_dir / project_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    async def run(
        self,
        lesson: Lesson,
        style: str = "modern_dialogue",
        platforms: list[Platform] | None = None,
    ) -> VideoProject:
        project_id = uuid.uuid4().hex[:12]
        project = VideoProject(project_id=project_id, lesson_id=lesson.lesson_id)
        proj_dir = self._project_dir(project_id)

        try:
            script = await self._step_script(project, lesson, style, proj_dir)
            audio_paths = await self._step_audio(project, script, proj_dir)
            srt_path = self._step_subtitles(project, script, proj_dir)

            digital_human_video = await self._step_digital_human(
                project, audio_paths, proj_dir
            )

            video_path = await self._step_assemble(
                project, audio_paths, srt_path, digital_human_video, proj_dir
            )

            if platforms:
                await self._step_publish(project, video_path, script.title, platforms)

        except Exception as exc:
            logger.error("Pipeline failed for project %s: %s", project_id, exc)
            project.fail(str(exc))

        return project

    async def _step_script(
        self, project: VideoProject, lesson: Lesson, style: str, proj_dir: Path
    ) -> AdaptedScript:
        logger.info("[%s] Generating script…", project.project_id)
        script = await self._script_gen.generate(lesson, style)
        script_path = proj_dir / "script.json"
        script_path.write_text(script.model_dump_json(indent=2), encoding="utf-8")
        project.advance(VideoStatus.SCRIPT_READY, script_path=script_path)
        return script

    async def _step_audio(
        self, project: VideoProject, script: AdaptedScript, proj_dir: Path
    ) -> list[Path]:
        logger.info("[%s] Generating audio…", project.project_id)
        audio_dir = proj_dir / "audio"
        audio_paths = await self._tts.generate_audio(script, audio_dir)
        project.advance(VideoStatus.AUDIO_READY, audio_path=audio_dir)
        return audio_paths

    def _step_subtitles(
        self, project: VideoProject, script: AdaptedScript, proj_dir: Path
    ) -> Path:
        logger.info("[%s] Generating subtitles…", project.project_id)
        srt_path = proj_dir / "subtitles.srt"
        self._subtitle.generate_bilingual_srt(script, srt_path)
        project.advance(VideoStatus.SUBTITLES_READY, subtitle_path=srt_path)
        return srt_path

    async def _step_digital_human(
        self,
        project: VideoProject,
        audio_paths: list[Path],
        proj_dir: Path,
    ) -> Path | None:
        """可选: 生成数字人视频. 服务未配置时直接跳过, 返回 None."""
        if self._digital_human is None or not self._digital_human.is_enabled:
            logger.info(
                "[%s] Digital human disabled, will use static background image",
                project.project_id,
            )
            return None
        if self._digital_human_reference is None:
            logger.warning(
                "[%s] No digital_human_reference configured, skipping",
                project.project_id,
            )
            return None
        if not audio_paths:
            return None

        logger.info("[%s] Rendering digital human via InfiniteTalk…", project.project_id)
        # 先把多段 audio 拼成一个完整的旁白音轨, 然后送给 InfiniteTalk
        merged_audio = proj_dir / "audio_merged.mp3"
        await self._merge_audio(audio_paths, merged_audio)

        out_video = proj_dir / "digital_human.mp4"
        try:
            await self._digital_human.generate(
                reference_image=self._digital_human_reference,
                audio_file=merged_audio,
                output_path=out_video,
            )
        except DigitalHumanError as exc:
            logger.warning(
                "[%s] Digital human generation failed (%s), falling back to static image",
                project.project_id,
                exc,
            )
            return None
        return out_video

    @staticmethod
    async def _merge_audio(audio_paths: list[Path], output: Path) -> Path:
        """拼接多段 audio 为单文件 (按字节顺序拼接 mp3 帧, 工程上够用)."""
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("wb") as out:
            for af in audio_paths:
                if af.exists():
                    out.write(af.read_bytes())
        return output

    async def _step_assemble(
        self,
        project: VideoProject,
        audio_paths: list[Path],
        srt_path: Path,
        digital_human_video: Path | None,
        proj_dir: Path,
    ) -> Path:
        logger.info("[%s] Assembling video…", project.project_id)
        output = proj_dir / "final.mp4"
        manifest = AssemblyManifest(
            project_id=project.project_id,
            audio_files=audio_paths,
            subtitle_file=srt_path,
            background_image=self._background_image,
            digital_human_video=digital_human_video,
            bgm_file=self._bgm_file,
            output_path=output,
        )
        video_path = await self._assembler.assemble(manifest)
        project.advance(VideoStatus.ASSEMBLED, video_path=video_path)
        return video_path

    async def _step_publish(
        self,
        project: VideoProject,
        video_path: Path,
        title: str,
        platforms: list[Platform],
    ) -> None:
        logger.info("[%s] Publishing to %s…", project.project_id, platforms)
        results = await self._publisher.publish(
            video_path=video_path,
            title=title,
            description=f"NCE Lesson {project.lesson_id} — Adapted Video",
            platforms=platforms,
        )
        all_ok = all(r.success for r in results)
        if all_ok:
            project.advance(VideoStatus.PUBLISHED)
        else:
            failed = [r for r in results if not r.success]
            project.fail(
                f"Publishing failed on: {[f.platform.value for f in failed]}"
            )
