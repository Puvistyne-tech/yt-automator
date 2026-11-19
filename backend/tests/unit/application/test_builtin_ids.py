from __future__ import annotations

from dataclasses import dataclass

import pytest

from autotube.domain.pipeline_templates import PipelineTemplate, TemplateAudience, builtin_template
from autotube.shared.errors import RuleConflict
from tests.fixtures.fake_engines import ENGINE_ID, FakeEngine, FakeEngineCatalog
from tests.fixtures.template_rig import TemplateRig

NEXT_ID = "id-1"


@dataclass(frozen=True)
class ClaimingEngine(FakeEngine):
    def builtin_templates(self) -> list[PipelineTemplate]:
        general = TemplateAudience.GENERAL
        return [builtin_template(ENGINE_ID, NEXT_ID, "Claimed", "", general, {"brief": "x"})]


@pytest.fixture
def claimed(rig: TemplateRig) -> TemplateRig:
    rig.engines = FakeEngineCatalog((ClaimingEngine(),))
    return rig


def test_create_refuses_an_id_a_builtin_already_has(claimed: TemplateRig) -> None:
    with pytest.raises(RuleConflict) as raised:
        claimed.created()
    assert raised.value.code == "template_exists"
    assert claimed.templates.list() == []


def test_duplicate_refuses_an_id_a_builtin_already_has(claimed: TemplateRig) -> None:
    with pytest.raises(RuleConflict) as raised:
        claimed.duplicate().execute(NEXT_ID)
    assert raised.value.code == "template_exists"
    assert claimed.templates.list() == []
