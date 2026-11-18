from __future__ import annotations

from collections.abc import Sequence

from autotube.domain.capabilities import Capability
from autotube.domain.pipeline import NewArtifact, StageContext, StageOutcome
from autotube.domain.pipeline_descriptors import StageDescriptor
from autotube.domain.run_enums import ArtifactKind, LogLevel
from autotube.pipelines.kids_story.artifacts import Role, artifact, folder, write_json
from autotube.pipelines.kids_story.languages import ordered_languages, primary_language
from autotube.pipelines.kids_story.settings.root import KidsStorySettings
from autotube.pipelines.kids_story.settings.story import StorySource
from autotube.pipelines.kids_story.stages.media_types import JSON
from autotube.pipelines.kids_story.stages.run_settings import kids_settings
from autotube.pipelines.kids_story.story.authoring import StoryAuthor, WriterUnavailableError
from autotube.pipelines.kids_story.story.bundled import BundledChoice, pick_bundled
from autotube.pipelines.kids_story.story.model import Story
from autotube.pipelines.kids_story.story.shaping import shaped
from autotube.pipelines.kids_story.story.themes import choose_theme

BUNDLED_PROVIDER = "bundled"
Written = tuple[dict[str, Story], str]


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
        if settings.story.source is StorySource.LLM_WITH_FALLBACK:
            written = self.from_writer(context, settings, order, theme)
            if written is not None:
                return written
            context.log(
                "falling back to a bundled story",
                LogLevel.WARNING,
            )
        return self.from_bundle(context, settings, order, theme)

    def from_writer(
        self, context: StageContext, settings: KidsStorySettings, order: list[str], theme: str
    ) -> Written | None:
        try:
            llm = context.providers.resolve(Capability.LLM)
            author = StoryAuthor(llm, settings, context.log, context.run_id)
            first = author.written(theme, order[0])
            if first is None:
                return None
            stories = {order[0]: first}
            for language in order[1:]:
                translated = author.translated(first, language)
                if translated is None:
                    return None
                stories[language] = translated
        except (LookupError, WriterUnavailableError) as error:
            context.log(
                f"story writer unavailable: {error}",
                LogLevel.WARNING,
            )
            return None
        return stories, llm.provider_id

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
        bundled = pick_bundled(choice)
        context.log(f"using bundled story {bundled.id}")
        stories = {
            language: bundled.to_story(language, settings.series.refrain.for_language(language))
            for language in order
        }
        return stories, BUNDLED_PROVIDER

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
