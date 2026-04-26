from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class LessonLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class Lesson(BaseModel):
    """Represents one New Concept English lesson."""

    lesson_id: int = Field(..., ge=1, description="Lesson number")
    title: str = Field(..., min_length=1, description="Lesson title")
    text: str = Field(..., min_length=1, description="Original lesson text")
    level: LessonLevel = Field(
        default=LessonLevel.BEGINNER, description="Difficulty level"
    )
    vocabulary: list[str] = Field(
        default_factory=list, description="Key vocabulary words"
    )
    grammar_points: list[str] = Field(
        default_factory=list, description="Grammar points covered"
    )
