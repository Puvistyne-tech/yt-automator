from __future__ import annotations

import pytest

from autotube.domain.automations import Automation
from autotube.domain.channels import Channel
from autotube.domain.deletion_rules import (
    ensure_channel_deletable,
    ensure_credential_deletable,
    ensure_run_deletable,
)
from autotube.domain.run_enums import RunStatus
from autotube.domain.runs import Run
from autotube.shared.errors import RuleConflict


def test_channel_targeted_by_enabled_automation_cannot_be_deleted(
    automation: Automation,
) -> None:
    with pytest.raises(RuleConflict, match="Bedtime") as raised:
        ensure_channel_deletable("chan-1", [automation])
    assert raised.value.code == "channel_in_use"


def test_channel_deletable_when_only_disabled_or_other_targets(automation: Automation) -> None:
    disabled = automation.model_copy(update={"enabled": False})
    ensure_channel_deletable("chan-1", [disabled])
    ensure_channel_deletable("chan-2", [automation])


def test_credential_used_by_channel_cannot_be_deleted(channel: Channel) -> None:
    with pytest.raises(RuleConflict) as raised:
        ensure_credential_deletable(channel.credential_id, [channel])
    assert raised.value.code == "credential_in_use"
    ensure_credential_deletable("other", [channel])


@pytest.mark.parametrize("status", list(RunStatus))
def test_only_inactive_runs_are_deletable(status: RunStatus, idle_run: Run) -> None:
    run = idle_run.model_copy(update={"status": status})
    active = status in {RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.PUBLISHING}
    if active:
        with pytest.raises(RuleConflict, match="cancel it"):
            ensure_run_deletable(run)
    else:
        ensure_run_deletable(run)


@pytest.fixture
def idle_run(automation: Automation) -> Run:
    return Run(
        id="r1",
        automation_id=automation.id,
        automation_name=automation.name,
        pipeline_type="fake",
        languages=("en",),
        settings_snapshot={},
        created_at=automation.created_at,
    )
