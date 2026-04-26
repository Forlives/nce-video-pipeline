"""批量生成 NCE 视频.

用法:
    python -m scripts.generate_all                # 生成 data/lessons/ 下所有课
    python -m scripts.generate_all --range 1-10   # 只生成 lesson_01 到 lesson_10
    python -m scripts.generate_all --style story  # 指定风格
    python -m scripts.generate_all --concurrency 3  # 并发数
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path

from config.settings import get_settings
from src.main import _build_pipeline
from src.models.lesson import Lesson

logger = logging.getLogger(__name__)


def parse_range(rng: str | None) -> tuple[int, int] | None:
    if not rng:
        return None
    parts = rng.split("-")
    if len(parts) != 2:
        raise ValueError(f"Invalid --range '{rng}', expected like 1-10")
    return int(parts[0]), int(parts[1])


def load_lessons(lessons_dir: Path, rng: tuple[int, int] | None) -> list[Lesson]:
    lessons: list[Lesson] = []
    for fp in sorted(lessons_dir.glob("lesson_*.json")):
        data = json.loads(fp.read_text(encoding="utf-8"))
        lesson = Lesson(**data)
        if rng is not None and not (rng[0] <= lesson.lesson_id <= rng[1]):
            continue
        lessons.append(lesson)
    return lessons


async def run_one(pipeline, lesson: Lesson, style: str) -> None:
    logger.info("[generate_all] Lesson %s: %s", lesson.lesson_id, lesson.title)
    project = await pipeline.run(lesson, style=style)
    if project.video_path:
        logger.info(
            "[generate_all] OK lesson=%s status=%s video=%s",
            lesson.lesson_id,
            project.status.value,
            project.video_path,
        )
    else:
        logger.error(
            "[generate_all] FAILED lesson=%s status=%s err=%s",
            lesson.lesson_id,
            project.status.value,
            project.error_message,
        )


async def main(args: argparse.Namespace) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    settings = get_settings()
    lessons_dir = Path(args.lessons_dir or "data/lessons")
    lessons = load_lessons(lessons_dir, parse_range(args.range))
    if not lessons:
        logger.error("No lessons found in %s", lessons_dir)
        return
    logger.info("Found %d lessons (output_dir=%s)", len(lessons), settings.output_dir)

    pipeline = _build_pipeline()
    sem = asyncio.Semaphore(max(1, args.concurrency))

    async def worker(lesson: Lesson) -> None:
        async with sem:
            try:
                await run_one(pipeline, lesson, args.style)
            except Exception as exc:
                logger.exception("Lesson %s crashed: %s", lesson.lesson_id, exc)

    await asyncio.gather(*[worker(l) for l in lessons])
    logger.info("[generate_all] All done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch generate NCE videos")
    parser.add_argument("--range", type=str, help="Lesson id range, e.g. 1-10")
    parser.add_argument(
        "--style",
        type=str,
        default="modern_dialogue",
        choices=["modern_dialogue", "story", "sitcom"],
    )
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument(
        "--lessons-dir",
        type=str,
        default="data/lessons",
        help="Directory containing lesson_*.json files",
    )
    asyncio.run(main(parser.parse_args()))
