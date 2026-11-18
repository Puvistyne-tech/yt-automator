from __future__ import annotations

from automator.pipelines.kids_story.publishing.limits import (
    TAGS_MAX,
    cleaned,
    tags_length,
    tags_within,
    truncated,
)
from automator.pipelines.kids_story.publishing.metadata import upload_metadata
from automator.pipelines.kids_story.publishing.templates import render_template, template_values
from automator.pipelines.kids_story.story.model import Story
from tests.unit.pipelines.kids_data import draft_dict, quick_settings


def story(language: str = "en") -> Story:
    return Story.model_validate({**draft_dict(), "language": language, "theme": "sharing"})


def test_render_template_fills_known_and_keeps_unknown_placeholders() -> None:
    assert render_template("{title} - {nope} {", {"title": "Hi"}) == "Hi - {nope} {"


def test_template_values_are_localised() -> None:
    values = template_values(story("ta"), quick_settings())
    assert values["series"] == "குட்டி கதைகள்"
    assert values["questions"].startswith("• ")
    assert "#KuttyStories" in values["hashtags"]
    assert values["characters"].startswith("குட்டி")


def test_limits() -> None:
    assert truncated("short", 10) == "short"
    long_title = "word " * 40
    cut = truncated(long_title, 100)
    assert len(cut) <= 100 and cut.endswith("…")
    assert cleaned(" <b>Hi</b> ") == "bHi/b"
    assert tags_length(["a b", "c"]) == 7
    many = [f"tag number {index}" for index in range(100)]
    kept = tags_within([*many, "Tag Number 1", "with,comma"])
    assert tags_length(kept) <= TAGS_MAX and len(kept) == len(set(kept))


def test_upload_metadata_uses_templates_per_variant() -> None:
    settings = quick_settings(
        metadata={
            "title_template": {"en": "{series}: {title}", "ta": "{title}"},
            "description_template": {"en": "Moral: {moral}\n{questions}", "ta": "{moral}"},
            "category": "27",
        }
    )
    episode = upload_metadata(story(), settings, "episode")
    assert episode.title == "Kutty Stories: Kutty and the Golden Mango"
    assert episode.description.startswith("Moral: Sharing makes everyone happier.")
    assert episode.category_id == "27" and episode.made_for_kids
    assert episode.default_language == "en" and episode.playlist_title == "Kutty Stories"
    short = upload_metadata(story(), settings, "short")
    assert short.title == "Kutty and the Golden Mango #Shorts"


def test_upload_metadata_respects_youtube_limits() -> None:
    settings = quick_settings(
        metadata={
            "title_template": {"en": "{title} " * 20, "ta": "{title}"},
            "description_template": {"en": "{moral} " * 400, "ta": "{moral}"},
            "tags": {"en": ["kids stories"] + [f"tag {n}" for n in range(200)], "ta": []},
        }
    )
    made = upload_metadata(story(), settings, "episode")
    assert len(made.title) <= 100 and len(made.description) <= 5000
    assert tags_length(made.tags) <= 500
