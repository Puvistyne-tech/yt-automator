from __future__ import annotations

from autotube.domain.capabilities import Capability, MusicGenerator, MusicRequest
from autotube.domain.pipeline import NewArtifact, StageContext, StageOutcome
from autotube.domain.pipeline_descriptors import StageDescriptor
from autotube.domain.run_enums import ArtifactKind, LogLevel
from autotube.pipelines.kids_story.artifacts import SHORT, Role, artifact, folder
from autotube.pipelines.kids_story.settings.root import KidsStorySettings
from autotube.pipelines.kids_story.stages.media_types import WAV
from autotube.pipelines.kids_story.stages.run_settings import kids_settings
from autotube.pipelines.kids_story.stages.story_loading import load_stories
from autotube.pipelines.kids_story.story.model import Story
from autotube.pipelines.kids_story.text.templates import render_template
from autotube.pipelines.kids_story.timeline.cuts import Cut, planned_cuts
from autotube.pipelines.kids_story.timeline.plan import total_seconds


def effect_cues(stories: dict[str, Story]) -> list[str]:
    story = next(iter(stories.values()))
    cues: list[str] = []
    for scene in story.scenes:
        cues.extend(cue for cue in scene.sound_effects if cue and cue not in cues)
    return cues


def effect_prompt(settings: KidsStorySettings, cue: str) -> str:
    return render_template(settings.sound_effects.prompt_template, {"cue": cue})


def bed_prompt(settings: KidsStorySettings, variant: str) -> str:
    short_mood = settings.music.short_mood_prompt
    return short_mood if variant == SHORT and short_mood.strip() else settings.music.mood_prompt


def effect_name(index: int) -> str:
    return f"effect-{index}.wav"


class MusicStage:
    @property
    def descriptor(self) -> StageDescriptor:
        return StageDescriptor(
            id="music",
            title="Compose music and sounds",
            description="A music bed for every video and the story's gentle sound effects.",
        )

    def run(self, context: StageContext) -> StageOutcome:
        settings = kids_settings(context)
        if not (settings.music.enabled or settings.sound_effects.enabled):
            return StageOutcome(message="music and sound effects are turned off")
        try:
            composer = context.providers.resolve(Capability.MUSIC)
        except LookupError as error:
            context.log(
                f"no music provider, continuing without music: {error}",
                LogLevel.WARNING,
            )
            return StageOutcome(message="no music provider")
        stories = load_stories(context)
        made = self.beds(context, composer, settings, stories) if settings.music.enabled else []
        if settings.sound_effects.enabled:
            made.extend(self.effects(context, composer, settings, stories))
        return StageOutcome(
            artifacts=tuple(made), provider=composer.provider_id, message=f"{len(made)} tracks"
        )

    def beds(
        self,
        context: StageContext,
        composer: MusicGenerator,
        settings: KidsStorySettings,
        stories: dict[str, Story],
    ) -> list[NewArtifact]:
        cuts = planned_cuts(stories, context.artifacts, settings)
        return [self.bed(context, composer, settings, cut) for cut in cuts]

    def bed(
        self, context: StageContext, composer: MusicGenerator, settings: KidsStorySettings, cut: Cut
    ) -> NewArtifact:
        seconds = total_seconds(cut.segments)
        context.log(f"composing {seconds:.0f} s of music for {cut.language} {cut.variant}")
        request = MusicRequest(prompt=bed_prompt(settings, cut.variant), duration_seconds=seconds)
        path = composer.compose(request, folder(context, "music") / f"music-{cut.name}.wav")
        return artifact(
            ArtifactKind.AUDIO,
            path,
            WAV,
            Role.MUSIC,
            language=cut.language,
            variant=cut.variant,
            duration_seconds=seconds,
        )

    def effects(
        self,
        context: StageContext,
        composer: MusicGenerator,
        settings: KidsStorySettings,
        stories: dict[str, Story],
    ) -> list[NewArtifact]:
        made = []
        seconds = settings.sound_effects.duration_seconds
        for index, cue in enumerate(effect_cues(stories)):
            request = MusicRequest(prompt=effect_prompt(settings, cue), duration_seconds=seconds)
            path = composer.compose(request, folder(context, "music") / effect_name(index))
            made.append(
                artifact(
                    ArtifactKind.AUDIO,
                    path,
                    WAV,
                    Role.SOUND_EFFECT,
                    cue=cue,
                    duration_seconds=seconds,
                )
            )
        return made
