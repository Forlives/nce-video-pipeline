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
    # ---------- LLM (脚本改编, 兼容 OpenAI / Claude / OneAPI / OpenRouter / DeepSeek) ----------
    openai_api_key: str = Field(default="", description="LLM API key (OpenAI / 第三方 OpenAI-兼容)")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="LLM base URL. 例: OpenRouter=https://openrouter.ai/api/v1, "
        "DeepSeek=https://api.deepseek.com/v1, 自建OneAPI=https://your.domain/v1",
    )
    openai_model: str = Field(
        default="gpt-4o",
        description="LLM 模型名. 例: gpt-4o / anthropic/claude-3.5-sonnet / "
        "deepseek-chat / deepseek-reasoner",
    )

    # ---------- TTS (旁白配音, 独立 key/base_url 支持 OpenAI / Azure / 第三方) ----------
    tts_provider: TTSProvider = Field(
        default=TTSProvider.OPENAI, description="TTS backend"
    )
    tts_voice: str = Field(default="alloy", description="TTS voice name")
    tts_api_key: str = Field(
        default="",
        description="TTS API key. 留空则回退使用 openai_api_key",
    )
    tts_base_url: str = Field(
        default="",
        description="TTS API base URL. 留空则回退使用 openai_base_url",
    )

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
