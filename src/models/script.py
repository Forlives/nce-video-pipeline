from __future__ import annotations

from pydantic import BaseModel, Field


class ScriptScene(BaseModel):
    """One scene in the adapted script."""

    scene_number: int = Field(..., ge=1)
    narration_en: str = Field(..., min_length=1, description="English narration")
    narration_cn: str = Field(
        default="", description="Chinese translation / subtitle"
    )
    stage_direction: str = Field(
        default="", description="Visual cue / stage direction"
    )
    vocabulary_highlight: list[str] = Field(
        default_factory=list, description="Words to highlight on screen"
    )
    duration_seconds: float = Field(
        default=10.0, ge=1.0, description="Estimated scene duration"
    )


class AdaptedScript(BaseModel):
    """Complete adapted script generated from a lesson."""

    lesson_id: int
    title: str
    style: str = Field(
        default="modern_dialogue",
        description="Adaptation style (modern_dialogue / story / sitcom)",
    )
    scenes: list[ScriptScene] = Field(default_factory=list)
    total_duration_seconds: float = Field(default=0.0)

    def compute_duration(self) -> float:
        self.total_duration_seconds = sum(s.duration_seconds for s in self.scenes)
        return self.total_duration_seconds
