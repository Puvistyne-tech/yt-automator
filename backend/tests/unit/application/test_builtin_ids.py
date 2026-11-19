from __future__ import annotations

from collections.abc import Callable

import pytest

from autotube.domain.model_base import JsonObject
from autotube.shared.errors import RuleConflict
from tests.fixtures.fake_engines import (
    ENGINE_ID,
    BuiltinEngine,
    FakeEngineCatalog,
    general_builtin,
)
from tests.fixtures.template_records import template
from tests.fixtures.template_rig import TemplateRig

NEXT_ID = "id-1"
SAMPLE_DEFINITION: JsonObject = {"brief": "facts"}


def held_by_builtin(rig: TemplateRig) -> None:
    claimed = general_builtin(NEXT_ID, SAMPLE_DEFINITION)
    rig.engines = FakeEngineCatalog((BuiltinEngine(builtins=(claimed,)),))


def held_by_stored(rig: TemplateRig) -> None:
    rig.templates.add(template(NEXT_ID, engine=ENGINE_ID, definition=SAMPLE_DEFINITION))


def create(rig: TemplateRig) -> object:
    return rig.created()


def duplicate(rig: TemplateRig) -> object:
    return rig.duplicate().execute(NEXT_ID)


@pytest.mark.parametrize("hold", [held_by_builtin, held_by_stored], ids=["builtin", "stored"])
@pytest.mark.parametrize("action", [create, duplicate], ids=["create", "duplicate"])
def test_a_new_template_may_not_take_an_id_already_held(
    rig: TemplateRig,
    hold: Callable[[TemplateRig], None],
    action: Callable[[TemplateRig], object],
) -> None:
    hold(rig)
    before = rig.templates.list()
    with pytest.raises(RuleConflict) as raised:
        action(rig)
    assert raised.value.code == "template_exists"
    assert rig.templates.list() == before
