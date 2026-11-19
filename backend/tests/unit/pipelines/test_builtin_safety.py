from __future__ import annotations

import pytest

from autotube.domain.pipeline_templates import PipelineTemplate, TemplateAudience
from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.series import BANNED_WORDS, PICTURE_EXCLUSIONS
from autotube.pipelines.narrated_video.template.kids_floor import listed_terms
from tests.fixtures.builtin_catalog import PACKAGED_FORMATS
from tests.fixtures.template_records import template

RELAXED = "scary_stories"
ENGINE = NarratedVideoEngine()
BUILTINS = {item.id: item for item in ENGINE.builtin_templates()}
KIDS = TemplateAudience.KIDS


def settings_of(item: PipelineTemplate) -> KidsStorySettings:
    settings = ENGINE.pipeline(item).settings_model()
    assert isinstance(settings, KidsStorySettings)
    return settings


def overlay_safety(item: PipelineTemplate) -> object:
    overlay = item.definition.get("settings", {})
    return overlay.get("safety") if isinstance(overlay, dict) else None


@pytest.mark.parametrize("template_id", sorted(set(PACKAGED_FORMATS) - {RELAXED}))
def test_every_other_builtin_keeps_its_audience_banned_words(template_id: str) -> None:
    item = BUILTINS[template_id]
    assert overlay_safety(item) is None
    expected = BANNED_WORDS if item.audience is KIDS else []
    assert settings_of(item).safety.banned_words == expected


def test_scary_stories_applies_its_own_banned_words() -> None:
    item = BUILTINS[RELAXED]
    safety = overlay_safety(item)
    assert isinstance(safety, dict)
    assert settings_of(item).safety.banned_words == safety["banned_words"]
    assert set(BANNED_WORDS) - set(safety["banned_words"])


def test_scary_stories_built_for_kids_gets_the_full_kids_floor_back() -> None:
    kids = template(audience=KIDS, definition=BUILTINS[RELAXED].definition)
    safety = settings_of(kids).safety
    assert set(BANNED_WORDS) <= set(safety.banned_words)
    assert set(listed_terms(PICTURE_EXCLUSIONS)) <= set(listed_terms(safety.picture_exclusions))
