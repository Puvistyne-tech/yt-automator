from __future__ import annotations

from autotube.domain.pipeline_descriptors import LanguageOption
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.domain.sample_scripts import (
    PREVIEW_TEMPLATE_ID,
    TemplatePreviewInput,
    preview_template,
    sample_language,
    sample_language_errors,
)
from tests.fixtures.fake_runtime import START

OFFERED = (LanguageOption(code="en", name="English"), LanguageOption(code="ta", name="Tamil"))


def test_the_sample_language_defaults_to_the_first_offered() -> None:
    assert sample_language(None, OFFERED) == "en"
    assert sample_language("ta", OFFERED) == "ta"
    assert sample_language(None, ()) == ""


def test_only_an_offered_language_is_accepted() -> None:
    assert sample_language_errors("ta", OFFERED) == {}
    assert sample_language_errors("fr", OFFERED) == {"language": "language must be one of: en, ta"}


def test_a_preview_template_is_an_unsaved_user_template() -> None:
    data = TemplatePreviewInput(
        engine="sample", name=" Sky ", audience=TemplateAudience.GENERAL, topic="comets"
    )
    made = preview_template(data, START)
    assert (made.id, made.type_id, made.name, made.revision) == (
        PREVIEW_TEMPLATE_ID,
        f"t_{PREVIEW_TEMPLATE_ID}",
        "Sky",
        1,
    )
