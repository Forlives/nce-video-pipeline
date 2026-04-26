from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings
from src.api.routes import router
from src.pipeline.pipeline import VideoPipeline
from src.services.digital_human_service import DigitalHumanConfig, DigitalHumanService
from src.services.openai_llm import OpenAILLMClient
from src.services.openai_tts import OpenAITTSBackend
from src.services.script_generator import ScriptGenerator
from src.services.tts_service import TTSService
from src.services.subtitle_service import SubtitleService
from src.services.video_assembler import VideoAssembler
from src.services.publisher import Publisher

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        force=True,
    )


def _build_pipeline() -> VideoPipeline:
    settings = get_settings()
    llm = OpenAILLMClient(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.openai_model,
    )
    tts_backend = OpenAITTSBackend(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    digital_human: DigitalHumanService | None = None
    digital_human_reference = None
    if settings.infinitetalk_api_url:
        digital_human = DigitalHumanService(
            DigitalHumanConfig(
                api_url=settings.infinitetalk_api_url,
                api_key=settings.infinitetalk_api_key or None,
                resolution=settings.infinitetalk_resolution,
                timeout=settings.infinitetalk_timeout,
            )
        )
        ref_path = settings.assets_dir / Path(
            settings.infinitetalk_reference_image
        ).name
        if not ref_path.exists():
            ref_path = Path(settings.infinitetalk_reference_image)
        digital_human_reference = ref_path

    bg_image = settings.assets_dir / "background.png"
    bgm_file = settings.assets_dir / "bgm.mp3"

    return VideoPipeline(
        script_gen=ScriptGenerator(llm),
        tts=TTSService(tts_backend, voice=settings.tts_voice),
        subtitle=SubtitleService(),
        assembler=VideoAssembler(),
        publisher=Publisher(),
        output_dir=settings.output_dir,
        digital_human=digital_human,
        digital_human_reference=digital_human_reference,
        background_image=bg_image if bg_image.exists() else None,
        bgm_file=bgm_file if bgm_file.exists() else None,
    )


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    _configure_logging()
    application.state.pipeline = _build_pipeline()
    logger.info("NCE Video Pipeline started")
    yield
    logger.info("NCE Video Pipeline shutting down")


app = FastAPI(
    title="NCE Video Pipeline",
    description="AI-powered New Concept English video production pipeline",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
