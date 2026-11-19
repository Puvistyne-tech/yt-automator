from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.model import Story, StoryText, with_text
from tests.fixtures.kids_fakes import FakeWriter
from tests.fixtures.script_builders import Labels, scripted_draft, scripted_text, scripted_writer
from tests.fixtures.template_settings import model_for

TOPIC = "the night sky"


@dataclass(frozen=True)
class Round:
    question: str
    ask: str
    answer: str
    reveal: str
    choices: tuple[str, ...]


ROUNDS_EN = (
    Round(
        "Which planet is closest to the sun?",
        "Here is question one. Many planets travel around the sun, some near and some very far "
        "away from it.",
        "Mercury",
        "The answer is Mercury. It is the smallest planet of all, and it races around the sun "
        "faster than any other planet does.",
        ("Mercury", "Venus", "Mars"),
    ),
    Round(
        "How many moons does Earth have?",
        "Now for question two. Look up on a clear night and you will often see it shining "
        "softly above the trees.",
        "one moon",
        "Earth has just one moon. It is our closest friend in space, and its light is really "
        "sunlight that bounces off its dusty ground.",
        ("one moon", "two moons", "three moons"),
    ),
    Round(
        "Which planet has the biggest rings?",
        "Here comes question three. Some planets wear wide, shining rings of ice and rock all "
        "the way around their middles.",
        "Saturn",
        "The answer is Saturn. Its bright rings are made of countless bits of ice, from tiny "
        "grains to chunks as big as a house.",
        ("Saturn", "Jupiter", "Neptune"),
    ),
    Round(
        "Which star gives Earth its daylight?",
        "And now the last one, question four. Every morning it rises in the east and warms the "
        "land and the sea.",
        "the sun",
        "The answer is the sun. It is a star just like the ones we see at night, but it is much "
        "closer, so it looks huge and bright.",
        ("the sun", "the North Star", "Sirius"),
    ),
)
ROUNDS_TA = (
    Round(
        "சூரியனுக்கு மிக அருகில் உள்ள கோள் எது?",
        "முதல் கேள்வி.",
        "புதன்",
        "விடை புதன். அது மிகச் சிறிய கோள், சூரியனை மிக வேகமாகச் சுற்றுகிறது.",
        ("புதன்", "வெள்ளி", "செவ்வாய்"),
    ),
    Round(
        "பூமிக்கு எத்தனை நிலாக்கள் உள்ளன?",
        "இரண்டாவது கேள்வி.",
        "ஒரே ஒரு நிலா",
        "பூமிக்கு ஒரே ஒரு நிலா தான் உள்ளது. அதன் ஒளி உண்மையில் சூரிய ஒளி.",
        ("ஒரே ஒரு நிலா", "இரண்டு நிலாக்கள்", "மூன்று நிலாக்கள்"),
    ),
    Round(
        "எந்தக் கோளுக்கு மிகப் பெரிய வளையங்கள் உள்ளன?",
        "மூன்றாவது கேள்வி.",
        "சனி",
        "விடை சனி. அதன் வளையங்கள் பனிக்கட்டித் துண்டுகளால் ஆனவை.",
        ("சனி", "வியாழன்", "நெப்டியூன்"),
    ),
    Round(
        "பூமிக்குப் பகல் ஒளி தரும் நட்சத்திரம் எது?",
        "கடைசி கேள்வி.",
        "சூரியன்",
        "விடை சூரியன். அது ஒரு நட்சத்திரம், ஆனால் நமக்கு மிக அருகில் உள்ளது.",
        ("சூரியன்", "துருவ நட்சத்திரம்", "சிரியஸ்"),
    ),
)
FRAMING_EN = (
    "Welcome to a quick quiz about the night sky. There are four questions today. Think of your "
    "answer before each reveal, and see how many you get right.",
    "That is the end of our quiz about the night sky. Count your right answers and try again "
    "another day. There is always more to learn up there.",
)
FRAMING_TA = (
    "இரவு வானம் பற்றிய ஒரு சிறிய வினாடி வினாவுக்கு வருக. இன்று நான்கு கேள்விகள் உள்ளன.",
    "இரவு வானம் பற்றிய வினாடி வினா முடிந்தது. உங்கள் சரியான விடைகளை எண்ணிப் பாருங்கள்.",
)


def round_labels(item: Round, choices: bool) -> list[Labels]:
    offered = list(item.choices) if choices else []
    return [{"question": item.question, "choices": offered}, {"answer": item.answer}]


def quiz_labels(rounds: tuple[Round, ...], choices: bool) -> list[Labels]:
    pairs = [label for item in rounds for label in round_labels(item, choices)]
    return [{}, *pairs, {}]


def quiz_narrations(rounds: tuple[Round, ...], framing: tuple[str, str]) -> list[str]:
    pairs = [line for item in rounds for line in (f"{item.ask} {item.question}", item.reveal)]
    return [framing[0], *pairs, framing[1]]


def quiz_draft(choices: bool = False) -> dict[str, Any]:
    narrations = quiz_narrations(ROUNDS_EN, FRAMING_EN)
    return scripted_draft("A Night Sky Quiz", narrations, quiz_labels(ROUNDS_EN, choices))


def quiz_text_ta(choices: bool = False) -> dict[str, Any]:
    narrations = quiz_narrations(ROUNDS_TA, FRAMING_TA)
    return scripted_text("இரவு வான வினாடி வினா", narrations, quiz_labels(ROUNDS_TA, choices))


def quiz_story(choices: bool = False, **changes: Any) -> Story:
    fields = {**quiz_draft(choices), "language": "en", "theme": TOPIC}
    return Story.model_validate(fields | changes)


def tamil_quiz(choices: bool = False, **changes: Any) -> Story:
    text = StoryText.model_validate(quiz_text_ta(choices) | changes)
    return with_text(quiz_story(choices), text, "ta")


def quiz_writer() -> FakeWriter:
    return scripted_writer(quiz_draft, quiz_text_ta)


def quiz_settings(audience: TemplateAudience, **sections: Any) -> KidsStorySettings:
    return model_for(audience, structure="quiz").model_validate(sections)
