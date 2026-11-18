from __future__ import annotations

import re
from typing import Any

import pytest
from pydantic import ValidationError

from automator.domain.ui_schema import CHOICE_GROUP_KEY, CHOICE_SWATCHES_KEY
from automator.pipelines.kids_story.plugin import KidsStoryPipeline
from automator.pipelines.kids_story.resources import resource_json
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.styles.library import (
    FAMILY_TITLES,
    StyleFamily,
    parsed_library,
    style_ids,
    style_library,
    style_named,
)

BANNED_NAMES = tuple(
    "".join(parts)
    for parts in (
        ("Dis", "ney"),
        ("Pix", "ar"),
        ("Ghi", "bli"),
        ("Dream", "Works"),
        ("Aard", "man"),
        ("Le", "go"),
        ("Mine", "craft"),
        ("Mar", "vel"),
        ("Poke", "mon"),
        ("San", "rio"),
        ("Hello ", "Kitty"),
        ("Miya", "zaki"),
        ("Lai", "ka"),
        ("Nickel", "odeon"),
        ("Cartoon ", "Network"),
        ("Pep", "pa"),
        ("Blu", "ey"),
        ("Un", "real"),
        ("Oct", "ane"),
        ("Ko", "dak"),
        ("Pola", "roid"),
        ("Cray", "ola"),
        ("Play", "-Doh"),
        ("Nin", "tendo"),
        ("Art", "Station"),
        ("Ses", "ame"),
    )
)
REQUIRED_STYLES = {
    "animated_3d",
    "flat_cartoon_2d",
    "classic_cel",
    "anime",
    "chibi",
    "watercolour_storybook",
    "gouache_picture_book",
    "vintage_storybook",
    "crayon_drawing",
    "coloured_pencil",
    "pencil_sketch",
    "ink_line_art",
    "ink_and_wash",
    "comic_book",
    "paper_cutout",
    "claymation",
    "felt_plush",
    "pixel_art",
    "low_poly_3d",
    "flat_vector",
    "pastel_kawaii",
    "chalkboard",
    "shadow_puppet",
    "oil_painting",
    "realistic_photo",
    "cinematic_realistic",
}


def mentions(text: str, name: str) -> bool:
    return re.search(rf"\b{re.escape(name.casefold())}\b", text.casefold()) is not None


def raw_entries() -> list[dict[str, Any]]:
    loaded = resource_json("styles", "library.json")
    assert isinstance(loaded, list)
    return [dict(entry) for entry in loaded]


def test_the_library_ships_every_required_style_and_more() -> None:
    assert len(style_library()) >= 24
    assert set(style_ids()) >= REQUIRED_STYLES
    assert len(set(style_ids())) == len(style_ids())


def test_every_family_has_styles_and_a_title() -> None:
    assert {style.family for style in style_library()} == set(StyleFamily)
    assert set(FAMILY_TITLES) == set(StyleFamily)


@pytest.mark.parametrize("name", BANNED_NAMES)
def test_no_style_names_a_studio_brand_or_artist(name: str) -> None:
    texts = [f"{s.title} {s.description} {s.prompt} {s.negative_prompt}" for s in style_library()]
    assert [text for text in texts if mentions(text, name)] == []


def test_the_banned_name_check_matches_whole_words_only() -> None:
    assert mentions(f"like a {BANNED_NAMES[0].upper()} film", BANNED_NAMES[0])
    assert not mentions("a colourful legoland-free legend", "leg")


def test_every_description_is_one_plain_sentence() -> None:
    for style in style_library():
        assert style.description.endswith(".") and style.description.count(". ") == 0, style.id


def test_a_repeated_style_id_is_refused() -> None:
    entries = raw_entries()
    with pytest.raises(ValueError, match="repeated: anime"):
        parsed_library([*entries, next(e for e in entries if e["id"] == "anime")])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("palette", ["#FFFFFF", "#000000", "#123456"]),
        ("palette", ["#FFFFFF", "#000000", "#123456", "red"]),
        ("family", "sculpted"),
        ("outline", "dotted"),
        ("texture", "glossy"),
        ("id", "Has Spaces"),
        ("prompt", ""),
    ],
)
def test_an_invalid_style_entry_is_refused(field: str, value: object) -> None:
    broken = {**raw_entries()[0], field: value}
    with pytest.raises(ValidationError):
        parsed_library([broken])


def test_an_unknown_style_id_is_not_found() -> None:
    assert style_named("nope") is None
    assert style_named("anime") is not None


def test_the_style_choice_publishes_cards_with_groups_and_swatches() -> None:
    schema = KidsStorySettings.model_json_schema()
    choice = schema["$defs"]["LookSettings"]["properties"]["visual_style"]
    entries = choice["oneOf"]
    assert choice["type"] == "string" and choice["default"] == "watercolour_storybook"
    assert [entry["const"] for entry in entries] == [*style_ids(), "custom"]
    first = entries[0]
    library_first = style_library()[0]
    assert first["description"] == library_first.description
    assert first[CHOICE_GROUP_KEY] == FAMILY_TITLES[library_first.family]
    assert first[CHOICE_SWATCHES_KEY] == list(library_first.palette)
    assert CHOICE_SWATCHES_KEY not in entries[-1]


def test_the_ui_schema_shows_the_style_as_cards() -> None:
    ui = KidsStoryPipeline().descriptor.ui_schema
    look = ui["look"]
    assert isinstance(look, dict)
    assert look["visual_style"] == {"ui:widget": "cards"}
