from __future__ import annotations

from collections.abc import Callable

import pytest

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.domain.runs import Run
from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.template.merging import deep_merged
from tests.fixtures.explainer_data import TAKEAWAY_EN, explainer_writer
from tests.fixtures.harness import Harness
from tests.fixtures.kids_data import smart_writer
from tests.fixtures.kids_fakes import FakeWriter
from tests.fixtures.offline_checks import assert_published_offline, upload_details
from tests.fixtures.pipeline_runs import executed_run
from tests.fixtures.quick_sections import QUICK_SECTIONS
from tests.fixtures.structure_writers import SCRIPTED_WRITERS
from tests.fixtures.template_records import template
from tests.fixtures.template_settings import GENERAL, KIDS, general_writer

pytestmark = pytest.mark.integration


def blank_run(
    harness: Harness, audience: TemplateAudience, structure: str, writer: FakeWriter
) -> Run:
    engine = NarratedVideoEngine()
    definition = {**engine.blank(audience), "structure": structure}
    pipeline = engine.pipeline(template(audience=audience, definition=definition))
    settings = deep_merged(pipeline.descriptor.default_settings, QUICK_SECTIONS)
    type_id = pipeline.descriptor.type_id
    return executed_run(harness, [pipeline], type_id, settings, writer)


@pytest.mark.parametrize("audience", [KIDS, GENERAL])
def test_a_blank_explainer_runs_offline_for_each_audience(
    harness: Harness, audience: TemplateAudience
) -> None:
    run = blank_run(harness, audience, "explainer", explainer_writer())
    assert_published_offline(run, harness, audience)
    english = [item for item in upload_details(run) if item.default_language == "en"]
    assert any(TAKEAWAY_EN in item.description for item in english)


@pytest.mark.parametrize("structure", list(SCRIPTED_WRITERS))
@pytest.mark.parametrize("audience", [KIDS, GENERAL])
def test_a_blank_scripted_structure_runs_offline_for_each_audience(
    harness: Harness, audience: TemplateAudience, structure: str
) -> None:
    run = blank_run(harness, audience, structure, SCRIPTED_WRITERS[structure]())
    assert_published_offline(run, harness, audience)


@pytest.mark.parametrize(("audience", "writer"), [(KIDS, smart_writer), (GENERAL, general_writer)])
def test_a_blank_story_runs_offline_for_each_audience(
    harness: Harness, audience: TemplateAudience, writer: Callable[[], FakeWriter]
) -> None:
    run = blank_run(harness, audience, "story", writer())
    assert_published_offline(run, harness, audience)
