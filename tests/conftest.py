from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.models.lesson import Lesson, LessonLevel
from src.models.script import AdaptedScript, ScriptScene


@pytest.fixture
def sample_lesson() -> Lesson:
    return Lesson(
        lesson_id=1,
        title="Excuse me!",
        text=(
            "Excuse me! Yes? Is this your handbag? Pardon? "
            "Is this your handbag? Yes, it is. Thank you very much."
        ),
        level=LessonLevel.BEGINNER,
        vocabulary=["excuse", "handbag", "pardon", "thank you"],
        grammar_points=["Is this your ...?", "Yes, it is."],
    )


@pytest.fixture
def sample_script() -> AdaptedScript:
    scenes = [
        ScriptScene(
            scene_number=1,
            narration_en="Excuse me, is this your bag?",
            narration_cn="打扰一下，这是你的包吗？",
            stage_direction="A busy coffee shop. Person A taps Person B on the shoulder.",
            vocabulary_highlight=["excuse", "bag"],
            duration_seconds=8.0,
        ),
        ScriptScene(
            scene_number=2,
            narration_en="Oh yes, it is! Thank you so much!",
            narration_cn="哦对，是的！非常感谢！",
            stage_direction="Person B smiles and takes the bag.",
            vocabulary_highlight=["thank you"],
            duration_seconds=6.0,
        ),
        ScriptScene(
            scene_number=3,
            narration_en="You're welcome! Have a great day!",
            narration_cn="不客气！祝你有美好的一天！",
            stage_direction="Both wave goodbye. Vocabulary review card appears.",
            vocabulary_highlight=["welcome"],
            duration_seconds=7.0,
        ),
    ]
    script = AdaptedScript(
        lesson_id=1,
        title="The Lost Bag — Excuse Me!",
        style="modern_dialogue",
        scenes=scenes,
    )
    script.compute_duration()
    return script


@pytest.fixture
def sample_script_json(sample_script: AdaptedScript) -> str:
    data = {
        "title": sample_script.title,
        "style": sample_script.style,
        "scenes": [s.model_dump() for s in sample_script.scenes],
    }
    return json.dumps(data)


@pytest.fixture
def tmp_output(tmp_path: Path) -> Path:
    out = tmp_path / "output"
    out.mkdir()
    return out
