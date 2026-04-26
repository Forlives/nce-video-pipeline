from __future__ import annotations

import os
from pathlib import Path
from enum import Enum

from pydantic_settings import BaseSettings
from pydantic import Field


class TTSProvider(str, Enum):
    OPENAI = "openai"
    AZURE = "azure"
    EDGE = "edge"


class Settings(BaseSettings):
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API base URL",
    )
    openai_model: str = Field(default="gpt-4o", description="LLM model name")

    tts_provider: TTSProvider = Field(
        default=TTSProvider.OPENAI, description="TTS backend"
    )
    tts_voice: str = Field(default="alloy", description="TTS voice name")

    output_dir: Path = Field(
        default=Path("./output"), description="Generated artefacts output directory"
    )
    assets_dir: Path = Field(
        default=Path("./assets"),
        description="Static assets (background images, BGM, reference avatars)",
    )
    log_level: str = Field(default="INFO", description="Logging level")

    # ---------- Digital Human (InfiniteTalk on remote GPU) ----------
    infinitetalk_api_url: str = Field(
        default="",
        description="InfiniteTalk HTTP API base URL, e.g. http://192.168.1.10:8000. "
        "Empty = disabled (skip digital human, use static background image).",
    )
    infinitetalk_api_key: str = Field(
        default="", description="Optional bearer token for InfiniteTalk auth"
    )
    infinitetalk_resolution: str = Field(
        default="480p", description="Digital human render resolution: 480p / 720p"
    )
    infinitetalk_reference_image: str = Field(
        default="assets/avatar.png",
        description="Default avatar image used when generating digital human videos",
    )
    infinitetalk_timeout: float = Field(
        default=1800.0, description="Max seconds to wait for digital human render"
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset cached settings — useful in tests."""
    global _settings
    _settings = None
