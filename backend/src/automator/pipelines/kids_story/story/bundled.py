from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, model_validator

from automator.domain.capabilities import CameraMove
from automator.pipelines.kids_story.resources import resource_json, resource_names
from automator.pipelines.kids_story.story.model import (
    Story,
    StoryScene,
    StorySourceKind,
    StoryText,
    with_text,
)
from automator.pipelines.kids_story.story.themes import fresh_items, stable_index
from automator.pipelines.kids_story.text.templates import render_template

FOLDER = "bundled"
REFRAIN = "refrain"
REFRAIN_SLOT = "{refrain}"


class BundledScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    visual: str = Field(min_length=1)
    characters: list[str] = Field(min_length=1)
    setting: str = Field(min_length=1)
    mood: str = Field(min_length=1)
    camera: CameraMove
    hero: bool = False
    sound_effects: list[str] = Field(default_factory=list)


class BundledStory(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    theme: str = Field(min_length=1)
    cast: list[str] = Field(min_length=1)
    thumbnail: str = Field(min_length=1)
    short_scenes: list[int]
    scenes: list[BundledScene] = Field(min_length=1)
    text: dict[str, StoryText]

    @model_validator(mode="after")
    def check_structure(self) -> BundledStory:
        for language, text in self.text.items():
            if len(text.narrations) != len(self.scenes):
                raise ValueError(f"{language} narrations must match the scenes")
        if any(not 0 <= index < len(self.scenes) for index in self.short_scenes):
            raise ValueError("short scenes must point at scenes")
        return self

    def to_story(self, language: str, refrain: str) -> Story:
        base = Story(
            language=language,
            theme=self.theme,
            source=StorySourceKind.BUNDLED,
            title=self.text[language].title,
            moral=self.text[language].moral,
            scenes=[
                StoryScene(narration=REFRAIN_SLOT, **scene.model_dump()) for scene in self.scenes
            ],
            short_scenes=list(self.short_scenes),
            thumbnail=self.thumbnail,
        )
        return with_text(base, filled_text(self.text[language], refrain), language)


def filled_text(text: StoryText, refrain: str) -> StoryText:
    slots = {REFRAIN: refrain}
    narrations = [render_template(line, slots).strip() for line in text.narrations]
    return text.model_copy(update={"narrations": narrations})


def bundled_stories() -> list[BundledStory]:
    return [
        BundledStory.model_validate(resource_json(FOLDER, name))
        for name in resource_names(FOLDER, ".json")
    ]


def compatible(story: BundledStory, cast_ids: set[str], languages: Sequence[str]) -> bool:
    return set(story.cast) <= cast_ids and all(code in story.text for code in languages)


@dataclass(frozen=True)
class BundledChoice:
    cast_ids: set[str]
    languages: Sequence[str]
    theme: str
    recent: Sequence[str]
    avoid: int
    seed: str


def listed(names: Iterable[str]) -> str:
    return ", ".join(sorted(names))


def bundled_requirements(stories: Sequence[BundledStory]) -> str:
    needs = dict.fromkeys(
        f"the cast ids {listed(story.cast)} with the languages {listed(story.text)}"
        for story in stories
    )
    return ", or ".join(needs)


def no_fit_message(choice: BundledChoice) -> str:
    return (
        f"no bundled story fits this automation, whose cast ids are {listed(choice.cast_ids)} "
        f"and whose languages are {listed(choice.languages)}. Bundled stories need "
        f"{bundled_requirements(bundled_stories())}. Use those cast ids, or let the language "
        "model write the stories."
    )


def pick_bundled(choice: BundledChoice) -> BundledStory:
    usable = [
        story for story in bundled_stories() if compatible(story, choice.cast_ids, choice.languages)
    ]
    if not usable:
        raise LookupError(no_fit_message(choice))
    by_theme = {story.theme.casefold(): story for story in usable}
    if choice.theme.casefold() in by_theme:
        return by_theme[choice.theme.casefold()]
    themes = fresh_items(list(by_theme), choice.recent, choice.avoid)
    seed = choice.seed
    return by_theme[themes[stable_index(seed, len(themes))]]
