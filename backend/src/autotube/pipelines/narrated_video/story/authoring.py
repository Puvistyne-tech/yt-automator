from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from functools import partial

from autotube.domain.capabilities import Capability, TextGenerator, TextRequest
from autotube.domain.pipeline import ProviderResolver, StageLog
from autotube.domain.run_enums import LogLevel
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.attempts import Attempt
from autotube.pipelines.narrated_video.story.checks import story_problems, translation_problems
from autotube.pipelines.narrated_video.story.model import Story, StoryDraft, StoryText, with_text
from autotube.pipelines.narrated_video.story.parsing import StoryFormatError, parse_model
from autotube.pipelines.narrated_video.story.prompts import story_request, translation_request
from autotube.pipelines.narrated_video.story.repairing import repaired_script

Written = tuple[dict[str, Story], str]


class WriterUnavailableError(RuntimeError):
    pass


class ScriptRejectedError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoryAuthor:
    llm: TextGenerator
    settings: KidsStorySettings
    log: StageLog
    seed: str = ""
    failures: list[str] = field(default_factory=list)

    def failed(self, message: str) -> None:
        self.failures.append(message)
        self.log(message, LogLevel.WARNING)

    def answer(self, request_text: Callable[[], str]) -> str:
        try:
            return request_text()
        except Exception as error:
            raise WriterUnavailableError(str(error) or type(error).__name__) from error

    def request(self, theme: str, language: str, last: Attempt | None) -> TextRequest:
        feedback = last.problems if last else ()
        previous = last.story if last else None
        return story_request(self.settings, theme, language, feedback, self.seed, previous)

    def attempted(self, theme: str, language: str, last: Attempt | None) -> Attempt:
        number = last.number + 1 if last else 1
        raw = self.answer(partial(self.llm.generate, self.request(theme, language, last)))
        try:
            draft = parse_model(raw, StoryDraft)
        except StoryFormatError as error:
            return Attempt(number, language, raw, None, (str(error),))
        story = Story(language=language, theme=theme, **draft.model_dump())
        problems = story_problems(story, self.settings, self.seed)
        attempt = Attempt(number, language, raw, story, tuple(problems))
        return self.mended(attempt) if problems and self.settings.story.repair_slips else attempt

    def mended(self, attempt: Attempt) -> Attempt:
        if attempt.story is None:
            return attempt
        fixed, notes = repaired_script(attempt.story, self.settings)
        if not notes or story_problems(fixed, self.settings, self.seed):
            return attempt
        self.log(f"story attempt {attempt.number} passed after repair: {'; '.join(notes)}")
        return replace(attempt, story=fixed, problems=(), repairs=notes)

    def rejected(self, attempt: Attempt) -> None:
        self.failed(f"story attempt {attempt.number} failed checks: {'; '.join(attempt.problems)}")

    def written(self, theme: str, language: str) -> Story | None:
        last: Attempt | None = None
        for _ in range(self.settings.story.max_attempts):
            last = self.attempted(theme, language, last)
            if last.accepted:
                return last.story
            self.rejected(last)
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
            self.failed(f"translation to {target} attempt {attempt} failed: {'; '.join(problems)}")
        return None


def authored_scripts(
    providers: ProviderResolver,
    settings: KidsStorySettings,
    log: StageLog,
    seed: str,
    theme: str,
    order: Sequence[str],
) -> Written:
    llm = providers.resolve(Capability.LLM)
    author = StoryAuthor(llm, settings, log, seed)
    stories = all_languages(author, theme, order)
    if stories is None:
        raise ScriptRejectedError(author.failures[-1])
    return stories, llm.provider_id


def all_languages(author: StoryAuthor, theme: str, order: Sequence[str]) -> dict[str, Story] | None:
    first = author.written(theme, order[0])
    if first is None:
        return None
    stories = {order[0]: first}
    for language in order[1:]:
        translated = author.translated(first, language)
        if translated is None:
            return None
        stories[language] = translated
    return stories
