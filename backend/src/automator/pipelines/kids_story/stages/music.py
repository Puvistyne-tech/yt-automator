from __future__ import annotations

from automator.domain.capabilities import Capability, MusicGenerator, MusicRequest
from automator.domain.pipeline import NewArtifact, StageContext, StageOutcome
from automator.domain.pipeline_descriptors import StageDescriptor
from automator.domain.run_enums import ArtifactKind
from automator.pipelines.kids_story.artifacts import VARIANTS, Role, artifact, folder
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.stages.common import WAV, kids_settings, load_stories
from automator.pipelines.kids_story.story.model import Story
from automator.pipelines.kids_story.timeline.plan import total_seconds
from automator.pipelines.kids_story.timeline.variants import planned
from automator.pipelines.kids_story.timeline.voices import voice_lines


def effect_cues(stories: dict[str, Story]) -> list[str]:
    story = next(iter(stories.values()))
    cues: list[str] = []
    for scene in story.scenes:
        cues.extend(cue for cue in scene.sound_effects if cue and cue not in cues)
    return cues


def effect_prompt(settings: KidsStorySettings, cue: str) -> str:
    return settings.sound_effects.prompt_template.replace("{cue}", cue)


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
            context.log(f"no music provider, continuing without music: {error}")
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
        made = []
        for language, story in stories.items():
            voices = voice_lines(context.artifacts, language)
            for variant in VARIANTS:
                seconds = total_seconds(planned(story, voices, settings, variant))
                if seconds <= 0:
                    continue
                context.log(f"composing {seconds:.0f} s of music for {language} {variant}")
                request = MusicRequest(prompt=settings.music.mood_prompt, duration_seconds=seconds)
                output = folder(context, "music") / f"music-{language}-{variant}.wav"
                path = composer.compose(request, output)
                made.append(
                    artifact(
                        ArtifactKind.AUDIO,
                        path,
                        WAV,
                        Role.MUSIC,
                        language=language,
                        variant=variant,
                        duration_seconds=seconds,
                    )
                )
        return made

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
