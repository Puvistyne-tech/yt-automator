from __future__ import annotations

from pydantic import Field, field_validator

from autotube.pipelines.narrated_video.settings.base import SettingsSection

SINGLE_CHOICE = 1


class StructureShapeSettings(SettingsSection):
    item_count: int = Field(
        default=7,
        ge=3,
        le=15,
        title="List items",
        description="How many numbered items a list or countdown has, one scene each, between "
        "an intro scene and a closing scene.",
    )
    quiz_questions: int = Field(
        default=4,
        ge=1,
        le=10,
        title="Quiz questions",
        description="How many questions a quiz asks. Each gets a question scene and a reveal "
        "scene, between an intro scene and a closing scene.",
    )
    answer_choices: int = Field(
        default=0,
        ge=0,
        le=6,
        title="Answer choices",
        description="How many choices each quiz question offers, from 2 to 6. 0 asks open "
        "questions.",
    )

    @field_validator("answer_choices")
    @classmethod
    def not_one_choice(cls, value: int) -> int:
        if value == SINGLE_CHOICE:
            raise ValueError("a quiz question needs no choices or at least two")
        return value
