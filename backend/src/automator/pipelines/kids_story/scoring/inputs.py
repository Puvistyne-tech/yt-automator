from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from automator.domain.capabilities import Capability, MediaToolkit
from automator.domain.pipeline import StageContext
from automator.domain.quality import ScoreItem
from automator.domain.run_parts import Artifact
from automator.pipelines.kids_story.artifacts import MissingArtifactError, Role, latest, number
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.stages.common import kids_settings, load_story
from automator.pipelines.kids_story.story.model import Story
from automator.pipelines.kids_story.subtitles.srt import SrtEntry, parse_srt
from automator.pipelines.kids_story.timeline.voices import VoiceLine, voice_lines


@dataclass(frozen=True)
class ScoreInputs:
    settings: KidsStorySettings
    languages: tuple[str, ...]
    artifacts: tuple[Artifact, ...]
    workspace: Path
    stories: dict[str, Story]
    voices: dict[str, dict[str, VoiceLine]]
    media: MediaToolkit | None

    def video(self, language: str, variant: str) -> Artifact | None:
        return latest(self.artifacts, Role.FINAL_VIDEO, language, variant)

    def video_seconds(self, language: str, variant: str) -> float | None:
        found = self.video(language, variant)
        return number(found.meta.get("duration_seconds")) if found else None

    def path(self, artifact: Artifact) -> Path:
        return self.workspace / artifact.filename

    def subtitles(self, language: str, variant: str) -> list[SrtEntry] | None:
        found = latest(self.artifacts, Role.CAPTIONS, language, variant)
        if found is None:
            return None
        return parse_srt(self.path(found).read_text(encoding="utf-8"))


ScoreRule = Callable[[ScoreInputs], ScoreItem | None]


def stories_of(context: StageContext) -> dict[str, Story]:
    stories = {}
    for language in context.languages:
        try:
            stories[language] = load_story(context, language)
        except MissingArtifactError:
            continue
    return stories


def media_of(context: StageContext) -> MediaToolkit | None:
    try:
        return context.providers.resolve(Capability.MEDIA)
    except LookupError:
        return None


def gathered(context: StageContext) -> ScoreInputs:
    return ScoreInputs(
        settings=kids_settings(context),
        languages=context.languages,
        artifacts=context.artifacts,
        workspace=context.workspace,
        stories=stories_of(context),
        voices={code: voice_lines(context.artifacts, code) for code in context.languages},
        media=media_of(context),
    )
