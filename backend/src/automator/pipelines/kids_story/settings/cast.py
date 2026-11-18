from __future__ import annotations

from pydantic import Field

from automator.pipelines.kids_story.settings.base import (
    HexColor,
    LocalizedText,
    SettingsSection,
    localized_text,
)


class Character(SettingsSection):
    id: str = Field(
        pattern=r"^[a-z][a-z0-9_]*$",
        title="Character id",
        description="A short lowercase id the story uses to refer to this character.",
    )
    name: LocalizedText = localized_text("", "", "Name", "The character's name per language.")
    species: str = Field(
        min_length=1, title="Species", description="What kind of animal the character is."
    )
    visual_descriptor: str = Field(
        min_length=1,
        title="Fixed look",
        description="Exact visual description repeated in every picture to keep them on model.",
    )
    personality: str = Field(
        default="",
        title="Personality",
        description="How the character behaves and speaks, given to the story writer.",
    )
    palette: list[HexColor] = Field(
        default_factory=list,
        title="Colour palette",
        description="Signature colours of the character as hex values.",
    )
    voice_override: LocalizedText = localized_text(
        "",
        "",
        "Voice override",
        "Voice id used when this character speaks a whole scene. Empty uses the narrator.",
    )


def character(
    character_id: str,
    names: tuple[str, str],
    species: str,
    look: str,
    personality: str,
    palette: list[str],
) -> Character:
    return Character(
        id=character_id,
        name=LocalizedText(en=names[0], ta=names[1]),
        species=species,
        visual_descriptor=look,
        personality=personality,
        palette=palette,
    )


def default_cast() -> list[Character]:
    return [
        character(
            "kavin",
            ("Kavin", "கவின்"),
            "baby elephant",
            "a small round baby elephant with soft blue-grey skin, big floppy ears with pink "
            "insides, a short curly trunk, bright curious eyes and a red-and-yellow striped scarf",
            "curious, cheerful and caring; asks lots of questions and loves helping friends",
            ["#8FA3B8", "#E5534B", "#F4C430"],
        ),
        character(
            "mittu",
            ("Mittu", "மிட்டு"),
            "parrot",
            "a little green parrot with a bright red curved beak, a yellow chest patch, "
            "blue-tipped wings and a tiny orange flower tucked behind one eye",
            "chatty and funny; loves singing and sometimes talks before thinking",
            ["#3DAA5C", "#D7263D", "#F7D046"],
        ),
        character(
            "chinnu",
            ("Chinnu", "சின்னு"),
            "palm squirrel",
            "a tiny brown palm squirrel with three cream stripes down its back, a big fluffy tail "
            "and a small green satchel across its chest",
            "quick, clever and a little shy; good at noticing small things",
            ["#8B5A2B", "#F3E5C8", "#6BA368"],
        ),
        character(
            "aamai_thatha",
            ("Grandpa Tortoise", "ஆமை தாத்தா"),
            "tortoise",
            "a gentle old tortoise with a domed olive-green shell with honey-coloured patterns, "
            "round spectacles and a soft white beard",
            "calm, patient and wise; tells the friends gentle lessons with a smile",
            ["#7A8F3E", "#D9A441", "#FFFFFF"],
        ),
    ]
