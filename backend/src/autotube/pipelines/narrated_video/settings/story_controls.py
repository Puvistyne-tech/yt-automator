from __future__ import annotations

from pydantic import Field

from autotube.pipelines.narrated_video.settings.base import SettingsSection
from autotube.pipelines.narrated_video.settings.story_choices import (
    ENDING_STYLE_CHOICES,
    LEAD_MODE_CHOICES,
    STORY_CHECK_CHOICES,
    EndingStyle,
    LeadMode,
    StoryCheck,
)

TONE = "warm, gentle"
WRITING_STYLE = "Short sentences, simple everyday words, warm and calm tone."
QUESTION_STYLE = '"What happens next?" style questions for children'
TRANSLATION_STYLE = "natural, simple, warm"


class StoryWritingSettings(SettingsSection):
    tone: str = Field(
        default=TONE,
        min_length=1,
        max_length=300,
        title="Tone",
        description="How the stories feel, as the writer is told: 'You write <tone>, original "
        "stories that a parent is happy to play for a small child.'",
    )
    writing_style: str = Field(
        default=WRITING_STYLE,
        min_length=1,
        max_length=500,
        title="Writing style",
        description="One requirement on how sentences sound. Change it together with the tone.",
    )
    extra_instructions: str = Field(
        default="",
        max_length=2000,
        title="Extra instructions",
        description="Anything else the writer must do. Each line becomes one requirement.",
    )
    ending_style: EndingStyle = Field(
        default=EndingStyle.MORAL_AND_REFRAIN,
        json_schema_extra=ENDING_STYLE_CHOICES,
        title="Ending",
        description="How a story ends. Story prompts, translations and the ending check follow "
        "it. Bundled stories drop the refrain when the ending has none, but keep the moral "
        "their characters say.",
    )
    question_style: str = Field(
        default=QUESTION_STYLE,
        min_length=1,
        max_length=300,
        title="Question style",
        description="What kind of questions the writer asks children at the end.",
    )
    translation_style: str = Field(
        default=TRANSLATION_STYLE,
        min_length=1,
        max_length=300,
        title="Translation style",
        description="Words describing the language translations use, for example 'natural, "
        "simple, warm'.",
    )
    cast_per_episode: int = Field(
        default=0,
        ge=0,
        le=20,
        title="Characters per episode",
        description="How many cast members each story may use, the lead included. 0 uses all.",
    )
    lead_mode: LeadMode = Field(
        default=LeadMode.FIXED,
        json_schema_extra=LEAD_MODE_CHOICES,
        title="Lead character",
        description="The first cast member always leads, or each episode's lead is picked from "
        "its run, so the same lead can come up twice in a row. The next cast members in order "
        "join the lead.",
    )
    enabled_checks: list[StoryCheck] = Field(
        default_factory=lambda: list(StoryCheck),
        json_schema_extra=STORY_CHECK_CHOICES,
        title="Story checks",
        description="Checks a written story must pass, or it is rewritten. Banned words and "
        "brand names are always checked.",
    )
