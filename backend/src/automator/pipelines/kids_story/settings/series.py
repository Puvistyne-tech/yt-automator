from __future__ import annotations

from pydantic import Field, field_validator

from automator.pipelines.kids_story.settings.base import (
    LocalizedText,
    SettingsSection,
    localized_text,
    text_list_field,
)

ART_STYLE = (
    "soft watercolor picture-book illustration for young children, warm pastel colours, "
    "rounded friendly shapes, gentle golden light, clean uncluttered composition"
)
NEGATIVE_PROMPT = (
    "text, letters, words, captions, watermark, logo, signature, scary, dark, gloomy, "
    "violence, weapons, sharp teeth, realistic photo, distorted faces, extra limbs"
)
EDITORIAL_RULES = [
    "Every story is gentle, warm and safe for children aged three to seven.",
    "No violence, fear, danger, villains, punishment or unsafe behaviour.",
    "Problems are small and everyday, and the friends solve them by being kind.",
    "No brands, products, real people, places of worship or current events.",
    "Use short sentences and simple words a young child understands.",
    "End with the moral said plainly, then the series refrain.",
]
BANNED_WORDS = [
    "kill",
    "killed",
    "blood",
    "gun",
    "knife",
    "weapon",
    "die",
    "died",
    "dead",
    "monster",
    "ghost",
    "scary",
    "hate",
    "stupid",
    "fight",
    "punch",
    "hurt",
]
BRAND_NAMES = [
    "Disney",
    "Coca-Cola",
    "Pepsi",
    "McDonald's",
    "Lego",
    "Barbie",
    "Nike",
    "Adidas",
    "Nintendo",
    "Pixar",
    "Marvel",
]


class SeriesSettings(SettingsSection):
    name: LocalizedText = localized_text(
        "Story Time",
        "கதை நேரம்",
        "Series name",
        "Your series name per language, shown on the cards and filled in wherever {series} "
        "appears in the intro, outro, titles, descriptions and playlist title.",
    )
    tagline: LocalizedText = localized_text(
        "Gentle stories for little hearts",
        "சின்ன மனங்களுக்கு இனிய கதைகள்",
        "Tagline",
        "A short line describing the series, used in descriptions and cards.",
    )
    art_style: str = Field(
        default=ART_STYLE,
        min_length=1,
        title="Art style prompt",
        description="Describes the look of every picture so the series stays consistent.",
    )
    negative_prompt: str = Field(
        default=NEGATIVE_PROMPT,
        title="Things to keep out of pictures",
        description="Sent to the image model as the negative prompt for every picture.",
    )
    refrain: LocalizedText = localized_text(
        "Be kind, be brave, be you!",
        "அன்பாக இரு, துணிவாக இரு, நீயாகவே இரு!",
        "Recurring refrain",
        "The line every story ends with, said after the moral.",
    )
    intro_line: LocalizedText = localized_text(
        "Hello, little friends! Welcome to {series}. Let's begin!",
        "வணக்கம், சின்ன நண்பர்களே! {series} உங்களை அன்புடன் வரவேற்கிறது. கதையைத் தொடங்குவோம்!",
        "Intro line",
        "Spoken over the intro card at the start of every episode; {series} and the other "
        "description placeholders are filled in.",
    )
    outro_line: LocalizedText = localized_text(
        "Thank you for listening, little friends. See you in the next story!",
        "கதையைக் கேட்டதற்கு நன்றி, சின்ன நண்பர்களே. அடுத்த கதையில் சந்திப்போம்!",
        "Outro line",
        "Spoken over the outro card at the end of every episode; {series} and the other "
        "description placeholders are filled in.",
    )
    editorial_rules: list[str] = text_list_field(
        EDITORIAL_RULES,
        "Editorial rules",
        "Rules the story writer must follow. Each rule is one line in the prompt.",
    )

    @field_validator("name")
    @classmethod
    def check_name(cls, value: LocalizedText) -> LocalizedText:
        blank = [code for code, text in value.model_dump().items() if not text.strip()]
        if blank:
            raise ValueError(f"enter a series name for every language; blank: {', '.join(blank)}")
        return value


class SafetySettings(SettingsSection):
    banned_words: list[str] = text_list_field(
        BANNED_WORDS,
        "Banned words",
        "A story containing any of these whole words is rejected and rewritten.",
    )
    brand_names: list[str] = text_list_field(
        BRAND_NAMES,
        "Brand names",
        "A story mentioning any of these names is rejected and rewritten.",
    )
