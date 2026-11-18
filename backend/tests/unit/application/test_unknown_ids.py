from __future__ import annotations

from collections.abc import Callable

import pytest

from autotube.application.duplicate_automation import DuplicateAutomation
from autotube.application.set_automation_enabled import SetAutomationEnabled
from autotube.domain.run_enums import ReviewDecision
from autotube.shared.errors import NotFound
from tests.fixtures.harness import Harness
from tests.fixtures.use_cases import cancel_run, publish_run, review_run

UNKNOWN = "missing"


def enable(h: Harness) -> object:
    return SetAutomationEnabled(h.automations, h.presenter, h.clock).execute(UNKNOWN, True)


def duplicate(h: Harness) -> object:
    return DuplicateAutomation(h.automations, h.presenter, h.ids, h.clock).execute(UNKNOWN)


def review(h: Harness) -> object:
    return review_run(h).execute(UNKNOWN, ReviewDecision.APPROVED)


def cancel(h: Harness) -> object:
    return cancel_run(h).execute(UNKNOWN)


def publish(h: Harness) -> object:
    return publish_run(h).execute(UNKNOWN)


@pytest.mark.parametrize(
    ("action", "entity"),
    [
        (enable, "automation"),
        (duplicate, "automation"),
        (review, "run"),
        (cancel, "run"),
        (publish, "run"),
    ],
)
def test_unknown_id_is_not_found_and_saves_nothing(
    harness: Harness, action: Callable[[Harness], object], entity: str
) -> None:
    with pytest.raises(NotFound) as raised:
        action(harness)
    assert (raised.value.entity, raised.value.entity_id) == (entity, UNKNOWN)
    assert harness.automations.list() == [] and harness.runs.saves == 0
    assert harness.queue.cancelled == [] and harness.events.published == []
