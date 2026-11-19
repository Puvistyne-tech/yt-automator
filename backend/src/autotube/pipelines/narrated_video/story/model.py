from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from autotube.domain.capabilities import CameraMove


class StorySourceKind(StrEnum):
    LLM = "llm"
    BUNDLED = "bundled"


class SceneLabels(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    heading: str = Field(default="", description="The item's short heading in a list.")
    question: str = Field(default="", description="The quiz question this scene asks.")
    choices: list[str] = Field(default_factory=list, description="The quiz question's choices.")
    answer: str = Field(default="", description="The quiz answer this scene reveals.")

    @property
    def texts(self) -> list[str]:
        return [self.heading, self.question, *self.choices, self.answer]


class StoryScene(SceneLabels):
    narration: str = Field(min_length=1)
    visual: str = Field(min_length=1)
    action: str = Field(
        default="",
        description="One short present-tense sentence naming the single visible movement in "
        "this scene, for the video model.",
    )
    characters: list[str] = Field(default_factory=list)
    setting: str = ""
    mood: str = ""
    camera: CameraMove = CameraMove.PUSH_IN
    hero: bool = False
    sound_effects: list[str] = Field(default_factory=list)
    speaker: str = "narrator"
    number: int | None = Field(default=None, ge=1, description="The item's number in a list.")


class StoryDraft(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    title: str = Field(min_length=1)
    moral: str = ""
    scenes: list[StoryScene] = Field(min_length=1)
    questions: list[str] = Field(default_factory=list)
    short_scenes: list[int] = Field(default_factory=list)
    hook_line: str = ""
    thumbnail: str = ""

    @property
    def character_ids(self) -> list[str]:
        return list(dict.fromkeys(name for scene in self.scenes for name in scene.characters))


class Story(StoryDraft):
    language: str
    theme: str = ""
    source: StorySourceKind = StorySourceKind.LLM


class StoryText(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    title: str = Field(min_length=1)
    moral: str = ""
    narrations: list[str] = Field(min_length=1)
    questions: list[str] = Field(default_factory=list)
    hook_line: str = ""
    scene_labels: list[SceneLabels] | None = None


def draft_dump(story: StoryDraft) -> dict[str, Any]:
    return story.model_dump(mode="json", include=set(StoryDraft.model_fields))


def text_of(story: StoryDraft) -> StoryText:
    return StoryText(
        title=story.title,
        moral=story.moral,
        narrations=[scene.narration for scene in story.scenes],
        questions=list(story.questions),
        hook_line=story.hook_line,
        scene_labels=labels_of(story),
    )


def labels_of(story: StoryDraft) -> list[SceneLabels] | None:
    labels = [SceneLabels.model_validate(scene.model_dump()) for scene in story.scenes]
    return labels if any(label != SceneLabels() for label in labels) else None


def translated_labels(story: Story, text: StoryText) -> list[dict[str, object]]:
    if labels_of(story) is None:
        return [{} for _ in story.scenes]
    if text.scene_labels is None or len(text.scene_labels) != len(story.scenes):
        raise ValueError("translation must keep one scene_labels entry per scene")
    return [label.model_dump() for label in text.scene_labels]


def with_text(story: Story, text: StoryText, language: str) -> Story:
    if len(text.narrations) != len(story.scenes):
        raise ValueError("translation must keep every scene")
    scenes = [
        scene.model_copy(update={**labels, "narration": narration})
        for scene, narration, labels in zip(
            story.scenes, text.narrations, translated_labels(story, text), strict=True
        )
    ]
    return story.model_copy(
        update={
            "language": language,
            "title": text.title,
            "moral": text.moral,
            "scenes": scenes,
            "questions": list(text.questions),
            "hook_line": text.hook_line,
        }
    )
