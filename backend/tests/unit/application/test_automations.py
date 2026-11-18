from __future__ import annotations

from datetime import timedelta

import pytest

from automator.application.delete_automation import DeleteAutomation
from automator.application.duplicate_automation import DuplicateAutomation
from automator.application.get_automation import GetAutomation
from automator.application.list_automations import ListAutomations
from automator.application.set_automation_enabled import SetAutomationEnabled
from automator.application.update_automation import UpdateAutomation
from automator.domain.automations import Automation
from automator.domain.run_enums import RunStatus
from automator.domain.schedules import Schedule, ScheduleKind
from automator.shared.errors import NotFound, ValidationFailed
from tests.fixtures.builders import (
    add_automation,
    automation_input,
    create_automation,
    started_run,
    target_input,
)
from tests.fixtures.harness import Harness

pytestmark = pytest.mark.usefixtures("channel")


def test_create_normalizes_settings_and_assigns_ids(harness: Harness) -> None:
    created = create_automation(harness).execute(
        automation_input(targets=(target_input(), target_input(id="keep-me")))
    )
    assert harness.automations.get(created.id) == created
    assert created.settings["topic"] == "owls" and created.settings["score"] == 90.0
    assert [t.id for t in created.targets][1] == "keep-me"
    assert created.targets[0].id != created.id
    assert (created.created_at, created.updated_at) == (harness.clock.now(), harness.clock.now())
    assert created.next_run_at is None and created.last_run is None


def test_create_rejects_invalid_input_with_field_map(harness: Harness) -> None:
    with pytest.raises(ValidationFailed) as raised:
        create_automation(harness).execute(
            automation_input(settings={"topic": ""}, targets=(target_input(channel_id="x"),))
        )
    assert set(raised.value.fields) == {"settings.topic", "targets.0.channel_id"}
    assert harness.automations.list() == []


def test_create_unknown_pipeline(harness: Harness) -> None:
    with pytest.raises(ValidationFailed) as raised:
        create_automation(harness).execute(automation_input(pipeline_type="missing"))
    assert "pipeline_type" in raised.value.fields


def test_kids_pipeline_targets_are_stored_made_for_kids(harness: Harness) -> None:
    created = create_automation(harness).execute(automation_input(pipeline_type="fake_kids"))
    assert created.targets[0].made_for_kids is True


def update(harness: Harness) -> UpdateAutomation:
    return UpdateAutomation(harness.automations, harness.builder, harness.presenter, harness.clock)


def test_update_keeps_identity_and_creation_time(harness: Harness, automation: Automation) -> None:
    harness.clock.advance(hours=1)
    updated = update(harness).execute(automation.id, automation_input(name="Renamed"))
    assert (updated.id, updated.created_at) == (automation.id, automation.created_at)
    assert updated.name == "Renamed" and updated.updated_at == harness.clock.now()


def test_update_validates_and_requires_existing(harness: Harness, automation: Automation) -> None:
    with pytest.raises(NotFound):
        update(harness).execute("missing", automation_input())
    with pytest.raises(ValidationFailed):
        update(harness).execute(automation.id, automation_input(languages=("xx",)))
    assert harness.automations.get(automation.id) == automation


@pytest.mark.parametrize("enabled", [True, False])
def test_set_enabled(harness: Harness, automation: Automation, enabled: bool) -> None:
    harness.clock.advance(minutes=5)
    result = SetAutomationEnabled(harness.automations, harness.presenter, harness.clock).execute(
        automation.id, enabled
    )
    assert result.enabled is enabled
    changed = enabled != automation.enabled
    expected_update = harness.clock.now() if changed else automation.updated_at
    assert result.updated_at == expected_update


def test_delete_keeps_runs(harness: Harness, automation: Automation) -> None:
    run = harness.start_run.execute(automation.id)
    DeleteAutomation(harness.automations).execute(automation.id)
    assert harness.automations.get(automation.id) is None
    assert harness.runs.get(run.id) is not None
    with pytest.raises(NotFound):
        DeleteAutomation(harness.automations).execute(automation.id)


def test_duplicate_is_disabled_copy_with_new_ids(harness: Harness, automation: Automation) -> None:
    duplicate = DuplicateAutomation(
        harness.automations, harness.presenter, harness.ids, harness.clock
    ).execute(automation.id)
    assert duplicate.id != automation.id and duplicate.name == "Bedtime (copy)"
    assert duplicate.enabled is False and duplicate.settings == automation.settings
    assert duplicate.targets[0].id != automation.targets[0].id
    assert len(harness.automations.list()) == 2


def test_get_and_list_derive_next_run_and_last_run(harness: Harness) -> None:
    interval = Schedule(kind=ScheduleKind.INTERVAL, every_hours=2)
    scheduled = add_automation(harness, name="b scheduled", schedule=interval)
    manual = add_automation(harness, name="A manual")
    run = harness.start_run.execute(manual.id)
    fetched = GetAutomation(harness.automations, harness.presenter).execute(scheduled.id)
    assert fetched.next_run_at == scheduled.updated_at + timedelta(hours=2)
    listed = ListAutomations(harness.automations, harness.presenter).execute()
    assert [a.name for a in listed] == ["A manual", "b scheduled"]
    assert listed[0].next_run_at is None
    assert listed[0].last_run is not None and listed[0].last_run.id == run.id
    assert listed[0].last_run.status is RunStatus.QUEUED


def test_disabled_automation_has_no_next_run(harness: Harness) -> None:
    automation = add_automation(
        harness, enabled=False, schedule=Schedule(kind=ScheduleKind.CRON, cron="0 9 * * *")
    )
    assert (
        GetAutomation(harness.automations, harness.presenter).execute(automation.id).next_run_at
        is None
    )


def test_get_unknown_automation(harness: Harness) -> None:
    with pytest.raises(NotFound):
        GetAutomation(harness.automations, harness.presenter).execute("missing")


def test_run_snapshot_is_independent_of_later_edits(harness: Harness) -> None:
    run = started_run(harness)
    update(harness).execute(
        run.automation_id,
        automation_input(settings={"topic": "bats"}, languages=("ta",), targets=()),
    )
    stored = harness.runs.get(run.id)
    assert stored is not None
    assert stored.settings_snapshot["topic"] == "owls" and stored.languages == ("en",)
