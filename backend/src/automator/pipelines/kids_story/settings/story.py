from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from automator.pipelines.kids_story.settings.base import (
    LocalizedNumber,
    SettingsSection,
    StoryLanguage,
    localized_number,
    text_list_field,
)
from automator.pipelines.kids_story.settings.choices import (
    LANGUAGE_CHOICES,
    READING_LEVEL_CHOICES,
    STORY_SOURCE_CHOICES,
    THEME_MODE_CHOICES,
)

THEMES = [
    "sharing",
    "helping a friend",
    "trying again",
    "saying sorry",
    "being patient",
    "making a new friend",
    "telling the truth",
    "taking care of nature",
]
MORALS = [
    "Sharing makes everyone happier.",
    "Kind words can mend a sad heart.",
    "It is fine to make mistakes if we try again.",
    "Good friends listen to each other.",
    "Small helpers can do big things.",
]


class ThemeMode(StrEnum):
    ROTATE = "rotate"
    FIXED = "fixed"


class ReadingLevel(StrEnum):
    TODDLER = "toddler"
    PRESCHOOL = "preschool"
    EARLY_READER = "early_reader"


class StorySource(StrEnum):
    LLM_WITH_FALLBACK = "llm_with_fallback"
    BUNDLED_ONLY = "bundled_only"


class StorySettings(SettingsSection):
    source: StorySource = Field(
        default=StorySource.LLM_WITH_FALLBACK,
        json_schema_extra=STORY_SOURCE_CHOICES,
        title="Story source",
        description="Write new stories with the language model, or only use the bundled stories.",
    )
    primary_language: StoryLanguage = Field(
        default=StoryLanguage.ENGLISH,
        json_schema_extra=LANGUAGE_CHOICES,
        title="Writing language",
        description="The story is written in this language and translated into the others.",
    )
    theme_mode: ThemeMode = Field(
        default=ThemeMode.ROTATE,
        json_schema_extra=THEME_MODE_CHOICES,
        title="Theme choice",
        description="Rotate through the theme list, or always use the fixed theme.",
    )
    themes: list[str] = text_list_field(
        THEMES,
        "Themes",
        "Story themes the writer rotates through, one per episode.",
    )
    fixed_theme: str = Field(
        default="sharing", title="Fixed theme", description="Used when theme choice is fixed."
    )
    recent_themes: list[str] = text_list_field(
        [], "Recently used themes", "Themes of recent episodes, newest last. Avoided by rotation."
    )
    avoid_repeat_last: int = Field(
        default=3,
        ge=0,
        le=20,
        title="Avoid repeating last themes",
        description="How many of the most recent themes rotation skips.",
    )
    morals: list[str] = text_list_field(
        MORALS, "Moral themes", "Morals the writer may choose from."
    )
    age_min: int = Field(
        default=3, ge=1, le=12, title="Youngest age", description="Youngest viewer, in years."
    )
    age_max: int = Field(
        default=7, ge=1, le=12, title="Oldest age", description="Oldest viewer, in years."
    )
    target_duration_seconds: int = Field(
        default=150,
        ge=30,
        le=600,
        title="Target episode length",
        description="Seconds of narration the story should fill.",
    )
    duration_tolerance_seconds: int = Field(
        default=30,
        ge=0,
        le=300,
        title="Length tolerance",
        description="How far the estimated length may be from the target, in seconds.",
    )
    scene_count_min: int = Field(
        default=8, ge=1, le=30, title="Fewest scenes", description="A story needs this many scenes."
    )
    scene_count_max: int = Field(
        default=10, ge=1, le=30, title="Most scenes", description="A story may have this many."
    )
    words_per_scene_min: LocalizedNumber = localized_number(
        18, 8, "Fewest words per scene", "Each scene's narration needs at least this many words."
    )
    words_per_scene_max: LocalizedNumber = localized_number(
        50, 40, "Most words per scene", "Each scene's narration may have at most this many words."
    )
    words_per_minute: LocalizedNumber = localized_number(
        120, 80, "Estimated speaking rate", "Words per minute used to estimate story length."
    )
    reading_level: ReadingLevel = Field(
        default=ReadingLevel.PRESCHOOL,
        json_schema_extra=READING_LEVEL_CHOICES,
        title="Reading level",
        description="How simple the language must be.",
    )
    max_average_sentence_words: LocalizedNumber = localized_number(
        12, 9, "Longest average sentence", "Most words a narration sentence may have on average."
    )
    long_word_graphemes: LocalizedNumber = localized_number(
        9, 10, "Long word size", "Words with more letters than this count as long."
    )
    max_long_word_share: float = Field(
        default=0.15,
        ge=0,
        le=1,
        title="Most long words",
        description="Largest share of long words allowed in the narration.",
    )
    ending_scenes: int = Field(
        default=2,
        ge=1,
        le=5,
        title="Closing scenes",
        description="How many final scenes must contain the moral and the refrain.",
    )
    question_count: int = Field(
        default=2,
        ge=0,
        le=5,
        title="'What happens next?' questions",
        description="Questions for children added to the description.",
    )
    temperature: float = Field(
        default=0.8,
        ge=0,
        le=2,
        title="Creativity",
        description="How surprising the writer may be: 0 is predictable, 2 is wild.",
    )
    translation_temperature: float = Field(
        default=0.3,
        ge=0,
        le=2,
        title="Translation creativity",
        description="Lower keeps translations closer to the original.",
    )
    max_tokens: int = Field(
        default=6000,
        ge=500,
        le=32000,
        title="Response size",
        description="Most tokens the writer may answer with.",
    )
    max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        title="Rewrite attempts",
        description="How often the writer may retry after failing a check before fallback.",
    )

    @model_validator(mode="after")
    def check_ranges(self) -> StorySettings:
        if self.scene_count_min > self.scene_count_max:
            raise ValueError("fewest scenes must not exceed most scenes")
        if self.age_min > self.age_max:
            raise ValueError("youngest age must not exceed oldest age")
        return self
