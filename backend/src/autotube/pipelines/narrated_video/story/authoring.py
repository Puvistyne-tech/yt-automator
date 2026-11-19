from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import partial

from autotube.domain.capabilities import Capability, TextGenerator
from autotube.domain.pipeline import ProviderResolver, StageLog
from autotube.domain.run_enums import LogLevel
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.checks import story_problems, translation_problems
from autotube.pipelines.narrated_video.story.model import Story, StoryDraft, StoryText, with_text
from autotube.pipelines.narrated_video.story.parsing import StoryFormatError, parse_model
from autotube.pipelines.narrated_video.story.prompts import story_request, translation_request

Written = tuple[dict[str, Story], str]


class WriterUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoryAuthor:
    llm: TextGenerator
    settings: KidsStorySettings
    log: StageLog
    seed: str = ""

    def answer(self, request_text: Callable[[], str]) -> str:
        try:
            return request_text()
        except Exception as error:
            raise WriterUnavailableError(str(error) or type(error).__name__) from error

    def drafted(self, theme: str, language: str, feedback: list[str]) -> Story:
        request = story_request(self.settings, theme, language, feedback, self.seed)
        draft = parse_model(self.answer(partial(self.llm.generate, request)), StoryDraft)
        return Story(language=language, theme=theme, **draft.model_dump())

    def written(self, theme: str, language: str) -> Story | None:
        feedback: list[str] = []
        for attempt in range(1, self.settings.story.max_attempts + 1):
            try:
                story = self.drafted(theme, language, feedback)
            except StoryFormatError as error:
                feedback = [str(error)]
            else:
                feedback = story_problems(story, self.settings, self.seed)
                if not feedback:
                    return story
            self.log(
                f"story attempt {attempt} failed checks: {'; '.join(feedback)}", LogLevel.WARNING
            )
        return None

    def translated(self, story: Story, target: str) -> Story | None:
        for attempt in range(1, self.settings.story.max_attempts + 1):
            request = translation_request(self.settings, story, story.language, target)
            raw = self.answer(partial(self.llm.generate, request))
            try:
                result = with_text(story, parse_model(raw, StoryText), target)
            except (StoryFormatError, ValueError) as error:
                problems = [str(error)]
            else:
                problems = translation_problems(result, self.settings)
                if not problems:
                    return result
            self.log(
                f"translation to {target} attempt {attempt} failed: {'; '.join(problems)}",
                LogLevel.WARNING,
            )
        return None


def authored_scripts(
    providers: ProviderResolver,
    settings: KidsStorySettings,
    log: StageLog,
    seed: str,
    theme: str,
    order: Sequence[str],
) -> Written | None:
    llm = providers.resolve(Capability.LLM)
    author = StoryAuthor(llm, settings, log, seed)
    first = author.written(theme, order[0])
    if first is None:
        return None
    stories = {order[0]: first}
    for language in order[1:]:
        translated = author.translated(first, language)
        if translated is None:
            return None
        stories[language] = translated
    return stories, llm.provider_id
