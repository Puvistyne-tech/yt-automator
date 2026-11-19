from __future__ import annotations

from typing import Any

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.model import Story, StoryText, with_text
from tests.fixtures.kids_fakes import FakeWriter
from tests.fixtures.script_builders import Labels, scripted_draft, scripted_text, scripted_writer
from tests.fixtures.template_settings import model_for

TOPIC = "facts about honeybees"
WORDS = ["one", "two", "three", "four", "five", "six", "seven"]
ITEMS_EN = [
    (
        "Bees dance to talk",
        "bees dance to talk. A bee wiggles its body in a little dance. The dance shows the other "
        "bees which way to fly to find the best flowers.",
    ),
    (
        "Bees have five eyes",
        "bees have five eyes. Two big eyes sit on the sides of the head. Three tiny eyes sit on "
        "top, and they help the bee see the light.",
    ),
    (
        "Bees taste with their feet",
        "bees taste with their feet. When a bee lands on a flower, its feet can tell at once if "
        "the flower has sweet nectar inside.",
    ),
    (
        "A hive is a busy home",
        "a hive is a busy home. Many thousands of bees live and work there together, and each "
        "bee has its own job to do every day.",
    ),
    (
        "Bees make their own wax",
        "bees make their own wax. The wax comes from their bodies. They shape it into neat little "
        "rooms with six sides to keep the honey safe.",
    ),
    (
        "Wings beat very fast",
        "their wings beat very fast. A bee flaps its wings more than two hundred times every "
        "second. That is what makes the soft buzzing sound we hear.",
    ),
    (
        "Honey keeps for years",
        "honey keeps for years. Bees dry it and seal it in wax, so it stays sweet and good for a "
        "very long time on the shelf.",
    ),
]
ITEMS_TA = [
    ("தேனீக்கள் நடனமாடிப் பேசும்", "தேனீக்கள் நடனமாடி மற்ற தேனீக்களுக்குப் பூக்களின் வழியைக் காட்டுகின்றன."),
    ("தேனீக்களுக்கு ஐந்து கண்கள்", "தலையின் இருபக்கமும் இரண்டு பெரிய கண்கள், மேலே மூன்று சிறிய கண்கள்."),
    ("கால்களால் சுவைக்கும்", "பூவில் அமரும்போது கால்களாலேயே இனிப்பான தேன் இருக்கிறதா என்று அறியும்."),
    ("கூடு ஒரு சுறுசுறுப்பான வீடு", "ஆயிரக்கணக்கான தேனீக்கள் ஒன்றாக வாழ்ந்து வேலை செய்கின்றன."),
    ("தேனீக்கள் மெழுகு செய்யும்", "மெழுகால் ஆறு பக்க அறைகளைக் கட்டித் தேனைப் பாதுகாக்கின்றன."),
    ("இறக்கைகள் வேகமாக அடிக்கும்", "ஒரு நொடியில் இருநூறு முறைக்கு மேல் இறக்கைகளை அடிக்கின்றன."),
    ("தேன் பல ஆண்டுகள் கெடாது", "தேனீக்கள் தேனை உலர்த்தி மெழுகால் மூடுவதால் அது நீண்ட காலம் இருக்கும்."),
]
INTRO_EN = (
    "Bees are small, but they do big things every single day. Here are seven facts about "
    "honeybees that may surprise you. Listen closely and pick the one you like best."
)
CLOSING_EN = (
    "Those were seven facts about honeybees. Next time you hear a soft buzz near a flower, "
    "stop for a moment and wave hello to a busy bee. Thank you for listening today."
)
INTRO_TA = "தேனீக்கள் சிறியவை, ஆனால் பெரிய வேலைகள் செய்கின்றன. தேனீக்கள் பற்றிய ஏழு உண்மைகளைப் பார்ப்போம்."
CLOSING_TA = "தேனீக்கள் பற்றிய ஏழு உண்மைகள் இவை. அடுத்த முறை பூவருகே ரீங்காரம் கேட்டால் தேனீக்கு வணக்கம் சொல்லுங்கள்."
NO_LABEL: Labels = {}


def item_order(countdown: bool) -> list[int]:
    numbers = list(range(1, len(ITEMS_EN) + 1))
    return numbers[::-1] if countdown else numbers


def item_labels(countdown: bool, items: list[tuple[str, str]]) -> list[Labels]:
    numbered = [{"number": n, "heading": items[n - 1][0]} for n in item_order(countdown)]
    return [NO_LABEL, *numbered, NO_LABEL]


def english_narrations(countdown: bool) -> list[str]:
    items = [f"Number {WORDS[n - 1]}: {ITEMS_EN[n - 1][1]}" for n in item_order(countdown)]
    return [INTRO_EN, *items, CLOSING_EN]


def tamil_narrations(countdown: bool) -> list[str]:
    items = [f"{ITEMS_TA[n - 1][0]}. {ITEMS_TA[n - 1][1]}" for n in item_order(countdown)]
    return [INTRO_TA, *items, CLOSING_TA]


def list_draft(countdown: bool = False) -> dict[str, Any]:
    title = "Seven Facts About Honeybees"
    return scripted_draft(title, english_narrations(countdown), item_labels(countdown, ITEMS_EN))


def list_text_ta(countdown: bool = False) -> dict[str, Any]:
    labels = [{"heading": label.get("heading", "")} for label in item_labels(countdown, ITEMS_TA)]
    return scripted_text("தேனீக்கள் பற்றிய ஏழு உண்மைகள்", tamil_narrations(countdown), labels)


def list_story(countdown: bool = False, **changes: Any) -> Story:
    fields = {**list_draft(countdown), "language": "en", "theme": TOPIC}
    return Story.model_validate(fields | changes)


def tamil_list(countdown: bool = False, **changes: Any) -> Story:
    text = StoryText.model_validate(list_text_ta(countdown) | changes)
    return with_text(list_story(countdown), text, "ta")


def with_scene(story: Story, index: int, **changes: Any) -> Story:
    scenes = list(story.scenes)
    scenes[index] = scenes[index].model_copy(update=changes)
    return story.model_copy(update={"scenes": scenes})


def list_writer(countdown: bool = False) -> FakeWriter:
    return scripted_writer(lambda: list_draft(countdown), lambda: list_text_ta(countdown))


def list_settings(
    audience: TemplateAudience, structure: str = "list", **sections: Any
) -> KidsStorySettings:
    return model_for(audience, structure=structure).model_validate(sections)
