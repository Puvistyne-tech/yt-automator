from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from automator.domain.run_enums import RunStatus, RunTrigger
from automator.domain.schedules import Schedule, ScheduleKind
from tests.fixtures.builders import add_automation, add_credential, automation_input, finished_run
from tests.fixtures.harness import Harness
from tests.fixtures.use_cases import get_dashboard, run_due, update_automation

HOURLY = Schedule(kind=ScheduleKind.INTERVAL, every_hours=1)
NINE_AM = Schedule(kind=ScheduleKind.CRON, cron="0 9 * * *")


def test_dashboard_counts_and_quota(harness: Harness) -> None:
    finished = finished_run(harness)
    add_automation(harness, name="Off", enabled=False)
    harness.start_run.execute(finished.automation_id)
    add_credential(harness, credential_id="cred-2", quota=500)
    day = harness.quota_report.today()
    harness.ledger.record("cred-2", 120, day)
    summary = get_dashboard(harness).execute()
    assert (summary.automations, summary.enabled_automations, summary.channels) == (2, 1, 1)
    assert (summary.runs_awaiting_review, summary.runs_today) == (1, 2)
    assert {r.automation_name for r in summary.recent_runs} == {"Bedtime"}
    assert [(q.credential_id, q.used, q.limit) for q in summary.quota] == [
        ("cred-1", 0, 10000),
        ("cred-2", 120, 500),
    ]


@pytest.mark.parametrize(("zone", "count"), [("UTC", 1), ("Asia/Kolkata", 0)])
def test_runs_today_uses_app_timezone(harness: Harness, zone: str, count: int) -> None:
    harness.clock.current = datetime(2026, 1, 5, 18, 0, tzinfo=UTC)
    finished_run(harness)
    harness.app_settings.settings = harness.app_settings.settings.model_copy(
        update={"timezone": zone}
    )
    harness.clock.current = datetime(2026, 1, 5, 19, 0, tzinfo=UTC)
    assert get_dashboard(harness).execute().runs_today == count


def test_dashboard_recent_runs_are_limited(harness: Harness) -> None:
    automation = add_automation(harness)
    for _ in range(12):
        harness.clock.advance(seconds=1)
        harness.start_run.execute(automation.id)
    assert len(get_dashboard(harness).execute().recent_runs) == 10


def test_scheduler_fires_due_automations_once(harness: Harness) -> None:
    hourly = add_automation(harness, name="Hourly", schedule=HOURLY)
    add_automation(harness, name="Manual")
    add_automation(harness, name="Disabled", schedule=HOURLY, enabled=False)
    tick = run_due(harness)
    assert tick.execute(harness.clock.now()) == []
    harness.clock.advance(hours=1)
    started = tick.execute(harness.clock.now())
    assert [(r.automation_id, r.trigger) for r in started] == [(hourly.id, RunTrigger.SCHEDULE)]
    assert tick.execute(harness.clock.now()) == []
    harness.clock.advance(minutes=59)
    assert tick.execute(harness.clock.now()) == []
    harness.clock.advance(minutes=1)
    assert len(tick.execute(harness.clock.now())) == 1


@pytest.mark.parametrize(("hours_later", "fires"), [(22, False), (23, True)])
def test_scheduler_follows_cron(harness: Harness, hours_later: int, fires: bool) -> None:
    add_automation(harness, schedule=NINE_AM)
    harness.clock.advance(hours=hours_later)
    assert bool(run_due(harness).execute(harness.clock.now())) is fires


def test_manual_runs_do_not_reset_the_schedule(harness: Harness) -> None:
    automation = add_automation(harness, schedule=HOURLY)
    harness.clock.advance(minutes=30)
    harness.start_run.execute(automation.id)
    harness.clock.advance(minutes=30)
    started = run_due(harness).execute(harness.clock.now())
    assert len(started) == 1 and started[0].status is RunStatus.QUEUED


def test_scheduler_skips_automations_that_cannot_start(harness: Harness) -> None:
    add_automation(harness, schedule=HOURLY)
    harness.pipelines.pipelines.clear()
    harness.clock.advance(hours=2)
    assert run_due(harness).execute(harness.clock.now()) == []


def test_editing_after_a_scheduled_run_moves_the_anchor(harness: Harness) -> None:
    automation = add_automation(harness, schedule=HOURLY)
    harness.clock.advance(hours=1)
    assert len(run_due(harness).execute(harness.clock.now())) == 1
    harness.clock.advance(minutes=10)
    edited = update_automation(harness).execute(
        automation.id, automation_input(name="Edited", schedule=HOURLY)
    )
    assert edited.next_run_at == edited.updated_at + timedelta(hours=1)
    harness.clock.advance(minutes=59)
    assert run_due(harness).execute(harness.clock.now()) == []
    harness.clock.advance(minutes=1)
    assert len(run_due(harness).execute(harness.clock.now())) == 1
