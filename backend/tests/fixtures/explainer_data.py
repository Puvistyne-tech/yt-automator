from __future__ import annotations

from typing import Any

from autotube.domain.capabilities import TextRequest
from autotube.domain.pipeline import Pipeline
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.model import Story, StoryText, with_text
from tests.fixtures.kids_data import is_judge, is_translation
from tests.fixtures.kids_fakes import FakeWriter, as_json
from tests.fixtures.template_settings import model_for, pipeline_of

EXPLAINER = {"structure": "explainer"}
TAKEAWAY_EN = "Sunlight bends in raindrops and spreads into colours to make a rainbow."
TAKEAWAY_TA = "சூரிய ஒளி மழைத்துளிகளில் வளைந்து நிறங்களாகப் பிரிந்து வானவில் ஆகிறது."
HOOKLESS = (
    "Sunlight is really many colours mixed together, and every single drop of rain in the sky "
    "splits those colours apart for us to see."
)
NARRATIONS_EN = [
    "Have you ever seen a rainbow after the rain? Where do all those bright colours come from? "
    "Today we find out, one small step at a time. Let us look up at the wet sky together.",
    "Sunlight looks white to our eyes. But it is really many colours mixed together. Red, "
    "orange, yellow, green, blue and violet all travel side by side in every beam of light.",
    "After the rain, tiny drops of water still float in the air. Each drop is round and "
    "clear. It works like a small piece of glass that hangs quietly in the sky.",
    "Sunlight goes into a drop and slows down. The light bends as it enters. Each colour bends "
    "a little bit in its own way, so the colours start to spread apart inside the drop.",
    "Next, the light bounces off the back of the drop. It is like a ball that hits a wall and "
    "comes back. Then the light bends once more as it leaves the drop again.",
    "Every colour leaves the drop at its own angle. Red comes to us from higher drops, and "
    "violet comes from lower ones. Many drops together paint the colours in neat bands.",
    "To see a rainbow, the sun must be behind you. The rain must be in front of you. That is "
    "why rainbows often come late in the day, when the sun sits low in the sky.",
    "So next time the sun comes out after rain, turn around and look up high. Remember this: "
    f"{TAKEAWAY_EN.lower()} Now you know the secret of the sky.",
]
NARRATIONS_TA = [
    "மழைக்குப் பிறகு வானத்தில் வானவில் ஏன் தோன்றுகிறது? அந்த அழகான நிறங்கள் எங்கிருந்து "
    "வருகின்றன? வாருங்கள், ஒவ்வொரு படியாகச் சேர்ந்து கண்டுபிடிப்போம்.",
    "சூரிய ஒளி வெள்ளையாகத் தெரிகிறது. ஆனால் அதில் பல நிறங்கள் ஒன்றாகக் கலந்திருக்கின்றன. "
    "சிவப்பு, மஞ்சள், பச்சை, நீலம் எல்லாம் சேர்ந்து பயணிக்கின்றன.",
    "மழைக்குப் பிறகு சிறிய நீர்த்துளிகள் காற்றில் மிதக்கின்றன. ஒவ்வொரு துளியும் உருண்டையாகத் "
    "தெளிவாக இருக்கிறது. அது ஒரு சிறிய கண்ணாடி போல வேலை செய்கிறது.",
    "ஒளி ஒரு துளிக்குள் நுழையும்போது வளைகிறது. ஒவ்வொரு நிறமும் சற்று வேறு விதமாக வளைகிறது. "
    "அதனால் நிறங்கள் துளிக்குள் பிரியத் தொடங்குகின்றன.",
    "பிறகு ஒளி துளியின் பின்பக்கத்தில் பட்டுத் திரும்புகிறது. சுவரில் பட்ட பந்து போல அது "
    "திரும்பி வருகிறது. வெளியே வரும்போது மீண்டும் வளைகிறது.",
    "ஒவ்வொரு நிறமும் தனது கோணத்தில் வெளியே வருகிறது. சிவப்பு உயரமான துளிகளிலிருந்து வருகிறது. "
    "ஊதா தாழ்வான துளிகளிலிருந்து வருகிறது.",
    "வானவில்லைப் பார்க்க சூரியன் உங்களுக்குப் பின்னால் இருக்க வேண்டும். மழை உங்களுக்கு "
    "முன்னால் இருக்க வேண்டும். அதனால் மாலையில் வானவில் அடிக்கடி தோன்றுகிறது.",
    f"அடுத்த முறை மழைக்குப் பிறகு மேலே பாருங்கள். நினைவில் கொள்ளுங்கள்: {TAKEAWAY_TA} "
    "இப்போது வானத்தின் ரகசியம் உங்களுக்குத் தெரியும்.",
]


def explainer_scene(narration: str, index: int) -> dict[str, Any]:
    return {
        "narration": narration,
        "visual": f"a bright rainbow over wet green fields, view {index + 1}",
        "characters": [],
        "setting": "green fields after a summer shower",
        "mood": "bright and calm",
        "camera": "push_in",
        "hero": index in (3, 7),
        "sound_effects": [],
        "speaker": "narrator",
    }


def explainer_draft() -> dict[str, Any]:
    return {
        "title": "How a Rainbow Is Made",
        "moral": TAKEAWAY_EN,
        "scenes": [explainer_scene(line, index) for index, line in enumerate(NARRATIONS_EN)],
        "questions": ["Which colour sits at the top of a rainbow?", "Where must the sun be?"],
        "short_scenes": [0, 3, 7],
        "hook_line": "Why does a rainbow appear after the rain?",
        "thumbnail": "a bright rainbow arching over wet green fields after a summer shower",
    }


def explainer_text_ta() -> dict[str, Any]:
    return {
        "title": "வானவில் எப்படி உருவாகிறது",
        "moral": TAKEAWAY_TA,
        "narrations": NARRATIONS_TA,
        "questions": ["வானவில்லின் மேலே எந்த நிறம்?", "சூரியன் எங்கே இருக்க வேண்டும்?"],
        "hook_line": "மழைக்குப் பிறகு வானவில் ஏன் தோன்றுகிறது?",
    }


def explainer_story(language: str = "en", **changes: Any) -> Story:
    fields = {**explainer_draft(), "language": language, "theme": "how a rainbow forms"}
    return Story.model_validate(fields | changes)


def without_hook() -> Story:
    first, *rest = explainer_story().scenes
    return explainer_story(scenes=[first.model_copy(update={"narration": HOOKLESS}), *rest])


def without_hook_or_takeaway() -> Story:
    scenes = without_hook().scenes
    return explainer_story(scenes=[*scenes[:-1], scenes[1]])


def tamil_explainer(narrations: list[str] | None = None) -> Story:
    text = explainer_text_ta() | ({"narrations": narrations} if narrations else {})
    return with_text(explainer_story(), StoryText.model_validate(text), "ta")


def explainer_writer(judge_answer: str = "1") -> FakeWriter:
    def respond(request: TextRequest) -> str:
        if is_judge(request):
            return judge_answer
        return as_json(explainer_text_ta() if is_translation(request) else explainer_draft())

    return FakeWriter(respond)


def explainer_settings(audience: TemplateAudience, **sections: Any) -> KidsStorySettings:
    return model_for(audience, **EXPLAINER).model_validate(sections)


def explainer_pipeline(audience: TemplateAudience, **definition: Any) -> Pipeline:
    return pipeline_of(audience, **EXPLAINER, **definition)
