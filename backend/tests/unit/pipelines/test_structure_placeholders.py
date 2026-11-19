from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.art.cards import card_lines
from autotube.pipelines.narrated_video.artifacts import EPISODE, SHORT
from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.publishing.metadata import UploadMetadata, upload_metadata
from autotube.pipelines.narrated_video.settings.story_choices import Structure
from autotube.pipelines.narrated_video.stages.voice import lines_to_speak
from autotube.pipelines.narrated_video.structures.registry import metadata_placeholders
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition
from autotube.pipelines.narrated_video.template.settings_model import template_defaults
from autotube.pipelines.narrated_video.template.text_leaves import text_leaves
from autotube.pipelines.narrated_video.text.templates import filled_template, unknown_placeholders
from tests.fixtures.explainer_data import explainer_settings, explainer_story
from tests.fixtures.template_records import template
from tests.fixtures.template_settings import GENERAL, KIDS, model_for

EXPLAINER_ID = Structure.EXPLAINER.value
METADATA_FIELDS = ("title_template", "short_title_template", "description_template")


def problems(audience: TemplateAudience = GENERAL, **definition: Any) -> dict[str, str]:
    return NarratedVideoEngine().problems(template(audience=audience, definition=definition))


def test_filled_template_empties_every_unknown_placeholder() -> None:
    assert filled_template("{title} - {nope} {", {"title": "Hi"}) == "Hi -  {"


@pytest.mark.parametrize("audience", [KIDS, GENERAL])
@pytest.mark.parametrize("structure", list(Structure))
def test_every_default_metadata_template_uses_only_the_structures_placeholders(
    audience: TemplateAudience, structure: Structure
) -> None:
    definition = NarratedDefinition(structure=structure)
    metadata = template_defaults(definition, audience)["metadata"]
    assert isinstance(metadata, dict)
    known = frozenset(metadata_placeholders(structure))
    texts = [text for field in METADATA_FIELDS for text in text_leaves(metadata[field])]
    assert len(texts) == len(METADATA_FIELDS) * 2
    assert [name for text in texts for name in unknown_placeholders(text, known)] == []


def test_an_explainer_reports_story_placeholders_as_template_problems() -> None:
    found = problems(
        structure=EXPLAINER_ID,
        title_template={"en": "{title} | {moral}"},
        description_template={"ta": "{takeaway} {characters}"},
    )
    assert set(found) == {"definition.title_template", "definition.description_template"}
    assert "{moral}" in found["definition.title_template"]
    assert "{takeaway}" in found["definition.title_template"]
    assert "{characters}" in found["definition.description_template"]


def test_a_story_reports_the_explainer_placeholder() -> None:
    found = problems(title_template={"en": "{title} | {takeaway}"})
    assert "{takeaway}" in found["definition.title_template"]


def test_overlay_metadata_templates_are_checked_where_they_were_written() -> None:
    overlay = {"metadata": {"playlist_title": {"en": "{series} {refrain}"}, "tags": {"en": ["x"]}}}
    found = problems(structure=EXPLAINER_ID, settings=overlay)
    assert set(found) == {"definition.settings.metadata.playlist_title"}
    assert "{refrain}" in found["definition.settings.metadata.playlist_title"]
    assert problems(settings={"metadata": "broken"}).keys() == {"definition.settings.metadata"}


def test_an_explainer_renders_placeholders_it_does_not_supply_as_empty() -> None:
    settings = explainer_settings(
        GENERAL,
        metadata={
            "title_template": {"en": "{title} {moral}"},
            "short_title_template": {"en": "{characters}{title}"},
            "description_template": {"en": "Remember: {takeaway} {refrain}"},
            "playlist_title": {"en": "{series}{nope}"},
        },
    )
    episode = upload_metadata(explainer_story(), settings, EPISODE)
    short = upload_metadata(explainer_story(), settings, SHORT)
    assert episode.title == "How a Rainbow Is Made"
    assert short.title == "How a Rainbow Is Made"
    assert episode.description.startswith("Remember: Sunlight bends")
    assert "{" not in episode.description + episode.playlist_title


def test_explainer_cards_and_spoken_lines_drop_story_placeholders() -> None:
    settings = explainer_settings(KIDS, series={"outro_line": {"en": "That was {title}. {moral}"}})
    lines = card_lines(settings, explainer_story(), "outro")
    assert lines == [settings.series.name.en]
    spoken = [line.text for line in lines_to_speak(explainer_story(), settings)]
    assert "That was How a Rainbow Is Made." in [text.strip() for text in spoken]


@pytest.mark.parametrize("variant", [EPISODE, SHORT])
@pytest.mark.parametrize(
    ("structure", "emptied"), [(Structure.EXPLAINER, "{moral}"), (Structure.STORY, "{nope}")]
)
def test_a_title_that_renders_empty_falls_back_to_the_script_title(
    variant: str, structure: Structure, emptied: str
) -> None:
    templates = {"title_template": {"en": emptied}, "short_title_template": {"en": f" {emptied} "}}
    model = model_for(GENERAL, structure=structure.value)
    settings = model.model_validate({"metadata": templates})
    assert upload_metadata(explainer_story(), settings, variant).title == "How a Rainbow Is Made"


def test_upload_metadata_refuses_an_empty_title() -> None:
    fields = upload_metadata(explainer_story(), explainer_settings(GENERAL), EPISODE).model_dump()
    with pytest.raises(ValidationError):
        UploadMetadata.model_validate({**fields, "title": ""})
