from __future__ import annotations

from collections.abc import Sequence
from functools import partial

from autotube.domain.pipeline import NewArtifact, StageContext, StageOutcome
from autotube.domain.pipeline_descriptors import StageDescriptor
from autotube.domain.run_enums import ArtifactKind, LogLevel
from autotube.pipelines.narrated_video.artifacts import Role, artifact, folder, write_json
from autotube.pipelines.narrated_video.languages import ordered_languages, primary_language
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story import StorySource
from autotube.pipelines.narrated_video.settings.story_choices import says_refrain
from autotube.pipelines.narrated_video.stages.media_types import JSON
from autotube.pipelines.narrated_video.stages.run_settings import kids_settings
from autotube.pipelines.narrated_video.story.attempts import (
    Attempt,
    attempt_filename,
    attempt_record,
)
from autotube.pipelines.narrated_video.story.authoring import (
    ScriptRejectedError,
    WriterUnavailableError,
    Written,
    authored_scripts,
)
from autotube.pipelines.narrated_video.story.bundled import BundledChoice, pick_bundled
from autotube.pipelines.narrated_video.story.bundled_fit import (
    length_pool,
    length_wish,
    misfit_warning,
)
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.shaping import shaped
from autotube.pipelines.narrated_video.story.themes import choose_theme
from autotube.pipelines.narrated_video.structures.registry import spec_of

BUNDLED_PROVIDER = "bundled"
NO_GENERAL_FALLBACK = (
    "the script writer did not produce a usable script, and a general-audience template never "
    "falls back to the bundled children's stories"
)
NO_STRUCTURE_FALLBACK = (
    "the script writer did not produce a usable script, and {structure} scripts have no bundled "
    "fallback"
)


def no_fallback_reason(settings: KidsStorySettings) -> str:
    if not settings.safety.for_kids:
        return NO_GENERAL_FALLBACK
    return NO_STRUCTURE_FALLBACK.format(structure=spec_of(settings).title.lower())


def bundled_refrain(settings: KidsStorySettings, language: str) -> str:
    if not says_refrain(settings.story.ending_style):
        return ""
    return settings.series.refrain.for_language(language)


class ScriptUnavailableError(RuntimeError):
    pass


class StoryStage:
    @property
    def descriptor(self) -> StageDescriptor:
        return StageDescriptor(
            id="story",
            title="Write the story",
            description="Writes, checks and translates the story, or uses a bundled one.",
        )

    def run(self, context: StageContext) -> StageOutcome:
        settings = kids_settings(context)
        primary = primary_language(settings.story.primary_language.value, context.languages)
        order = ordered_languages(primary, context.languages)
        theme = choose_theme(settings.story, context.run_id)
        context.log(f"story theme: {theme}")
        stories, provider = self.authored(context, settings, order, theme)
        artifacts = [self.saved(context, shaped(story, settings)) for story in stories.values()]
        first = stories[primary]
        return StageOutcome(
            artifacts=tuple(artifacts),
            provider=provider,
            message=f"{first.title} ({first.source.value}, {len(first.scenes)} scenes)",
        )

    def authored(
        self, context: StageContext, settings: KidsStorySettings, order: list[str], theme: str
    ) -> Written:
        if not settings.safety.for_kids or not spec_of(settings).uses_bundled:
            return self.written_only(context, settings, order, theme)
        if settings.story.source is StorySource.LLM_WITH_FALLBACK:
            written = self.from_writer(context, settings, order, theme)
            if not isinstance(written, str):
                return written
            context.log(
                "falling back to a bundled story",
                LogLevel.WARNING,
            )
        return self.from_bundle(context, settings, order, theme)

    def written_only(
        self, context: StageContext, settings: KidsStorySettings, order: list[str], theme: str
    ) -> Written:
        written = self.from_writer(context, settings, order, theme)
        if isinstance(written, str):
            raise ScriptUnavailableError(f"{no_fallback_reason(settings)}; {written}")
        return written

    def from_writer(
        self, context: StageContext, settings: KidsStorySettings, order: list[str], theme: str
    ) -> Written | str:
        try:
            keep = partial(self.kept_attempt, context)
            return authored_scripts(
                context.providers, settings, context.log, context.run_id, theme, order, keep
            )
        except ScriptRejectedError as error:
            return f"the last {error}"
        except (LookupError, WriterUnavailableError) as error:
            reason = f"story writer unavailable: {error}"
            context.log(reason, LogLevel.WARNING)
            return reason

    def from_bundle(
        self, context: StageContext, settings: KidsStorySettings, order: Sequence[str], theme: str
    ) -> Written:
        choice = BundledChoice(
            cast_ids={member.id for member in settings.cast},
            languages=order,
            theme=theme,
            recent=settings.story.recent_themes,
            avoid=settings.story.avoid_repeat_last,
            seed=context.run_id,
        )
        wish = length_wish(settings, order[0], bundled_refrain(settings, order[0]))
        bundled = pick_bundled(choice, partial(length_pool, wish=wish))
        context.log(f"using bundled story {bundled.id}")
        warning = misfit_warning(bundled, wish)
        if warning:
            context.log(warning, LogLevel.WARNING)
        stories = {
            language: bundled.to_story(language, bundled_refrain(settings, language))
            for language in order
        }
        return stories, BUNDLED_PROVIDER

    def kept_attempt(self, context: StageContext, attempt: Attempt) -> None:
        write_json(folder(context, "story") / attempt_filename(attempt), attempt_record(attempt))

    def saved(self, context: StageContext, story: Story) -> NewArtifact:
        path = folder(context, "story") / f"story-{story.language}.json"
        write_json(path, story.model_dump(mode="json"))
        return artifact(
            ArtifactKind.TEXT,
            path,
            JSON,
            Role.STORY,
            language=story.language,
            title=story.title,
            moral=story.moral,
            theme=story.theme,
            source=story.source.value,
            scene_count=len(story.scenes),
        )
