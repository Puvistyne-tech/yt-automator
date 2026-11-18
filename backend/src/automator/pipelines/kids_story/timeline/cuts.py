from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from automator.domain.run_parts import Artifact
from automator.pipelines.kids_story.artifacts import VARIANTS
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.story.model import Story
from automator.pipelines.kids_story.timeline.plan import Segment
from automator.pipelines.kids_story.timeline.variants import planned
from automator.pipelines.kids_story.timeline.voices import VoiceLine, voice_lines


@dataclass(frozen=True)
class Cut:
    story: Story
    variant: str
    voices: Mapping[str, VoiceLine]
    segments: list[Segment]

    @property
    def language(self) -> str:
        return self.story.language

    @property
    def name(self) -> str:
        return f"{self.story.language}-{self.variant}"


def story_cuts(
    story: Story, voices: Mapping[str, VoiceLine], settings: KidsStorySettings
) -> list[Cut]:
    return [
        Cut(story, variant, voices, segments)
        for variant in VARIANTS
        if (segments := planned(story, voices, settings, variant))
    ]


def planned_cuts(
    stories: Mapping[str, Story], artifacts: Sequence[Artifact], settings: KidsStorySettings
) -> list[Cut]:
    return [
        cut
        for language, story in stories.items()
        for cut in story_cuts(story, voice_lines(artifacts, language), settings)
    ]
