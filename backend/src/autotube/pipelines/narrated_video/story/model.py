from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from autotube.domain.capabilities import CameraMove


class StorySourceKind(StrEnum):
    LLM = "llm"
    BUNDLED = "bundled"


class StoryScene(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    narration: str = Field(min_length=1)
    visual: str = Field(min_length=1)
    characters: list[str] = Field(default_factory=list)
    setting: str = ""
    mood: str = ""
    camera: CameraMove = CameraMove.PUSH_IN
    hero: bool = False
    sound_effects: list[str] = Field(default_factory=list)
    speaker: str = "narrator"


class StoryDraft(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    title: str = Field(min_length=1)
    moral: str = Field(min_length=1)
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
    moral: str = Field(min_length=1)
    narrations: list[str] = Field(min_length=1)
    questions: list[str] = Field(default_factory=list)
    hook_line: str = ""


def text_of(story: StoryDraft) -> StoryText:
    return StoryText(
        title=story.title,
        moral=story.moral,
        narrations=[scene.narration for scene in story.scenes],
        questions=list(story.questions),
        hook_line=story.hook_line,
    )


def with_text(story: Story, text: StoryText, language: str) -> Story:
    if len(text.narrations) != len(story.scenes):
        raise ValueError("translation must keep every scene")
    scenes = [
        scene.model_copy(update={"narration": narration})
        for scene, narration in zip(story.scenes, text.narrations, strict=True)
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
