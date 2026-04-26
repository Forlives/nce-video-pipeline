from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class VideoStatus(str, Enum):
    PENDING = "pending"
    SCRIPT_READY = "script_ready"
    AUDIO_READY = "audio_ready"
    SUBTITLES_READY = "subtitles_ready"
    ASSEMBLED = "assembled"
    PUBLISHED = "published"
    FAILED = "failed"


class VideoProject(BaseModel):
    """Tracks the full lifecycle of one video."""

    project_id: str = Field(..., description="Unique project identifier")
    lesson_id: int
    status: VideoStatus = Field(default=VideoStatus.PENDING)
    script_path: Path | None = None
    audio_path: Path | None = None
    subtitle_path: Path | None = None
    video_path: Path | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def advance(self, status: VideoStatus, **kwargs: object) -> None:
        self.status = status
        self.updated_at = datetime.now(timezone.utc)
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def fail(self, message: str) -> None:
        self.status = VideoStatus.FAILED
        self.error_message = message
        self.updated_at = datetime.now(timezone.utc)
