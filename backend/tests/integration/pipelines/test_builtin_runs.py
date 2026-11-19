from __future__ import annotations

from collections.abc import Callable
from functools import partial

import pytest

from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.template.merging import deep_merged
from tests.fixtures.builtin_catalog import BUILTIN_IDS, KIDS_STORY
from tests.fixtures.builtin_samples import sample, sample_ids, sample_writer
from tests.fixtures.harness import Harness
from tests.fixtures.kids_data import draft_dict, smart_writer, tamil_text
from tests.fixtures.kids_fakes import FakeWriter
from tests.fixtures.offline_checks import assert_published_offline, upload_details
from tests.fixtures.pipeline_runs import executed_run
from tests.fixtures.quick_sections import QUICK_SECTIONS

pytestmark = pytest.mark.integration
LANGUAGES = ("en", "ta")
ENGINE = NarratedVideoEngine()
BUILTINS = {template.id: template for template in ENGINE.builtin_templates()}
WRITERS: dict[str, Callable[[], FakeWriter]] = {
    KIDS_STORY: smart_writer,
    **{template_id: partial(sample_writer, template_id) for template_id in sample_ids()},
}


def sample_titles(template_id: str) -> dict[str, str]:
    texts = sample(template_id)["text"]
    return {code: texts[code]["title"] for code in LANGUAGES}


TITLES = {
    KIDS_STORY: {"en": draft_dict()["title"], "ta": tamil_text()["title"]},
    **{template_id: sample_titles(template_id) for template_id in sample_ids()},
}


def test_every_builtin_has_one_offline_sample() -> None:
    assert sorted(WRITERS) == sorted(TITLES) == sorted(BUILTIN_IDS) == sorted(BUILTINS)


@pytest.mark.parametrize("template_id", BUILTIN_IDS)
def test_every_builtin_runs_offline_in_both_languages(harness: Harness, template_id: str) -> None:
    template = BUILTINS[template_id]
    pipeline = ENGINE.pipeline(template)
    settings = deep_merged(pipeline.descriptor.default_settings, QUICK_SECTIONS)
    run = executed_run(harness, [pipeline], template.type_id, settings, WRITERS[template_id]())
    assert_published_offline(run, harness, template.audience)
    expected = TITLES[template_id]
    found = upload_details(run)
    assert all(item.title.startswith(expected[item.default_language]) for item in found)
