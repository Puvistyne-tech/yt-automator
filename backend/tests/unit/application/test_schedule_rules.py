from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from autotube.application.run_due_automations import marked_skip, skip_message
from autotube.domain.retries import RetryPolicy
from autotube.domain.run_enums import LogLevel, RunStatus
from autotube.domain.runs import Run
from autotube.domain.schedules import Schedule, ScheduleKind
from tests.fixtures.builders import add_automation, execute_run, started_run
from tests.fixtures.harness import Harness
from tests.fixtures.use_cases import run_due


def hourly(**fields: Any) -> Schedule:
    return Schedule(kind=ScheduleKind.INTERVAL, every_hours=1, **fields)


def stored(harness: Harness, run_id: str) -> Run:
    run = harness.runs.get(run_id)
    assert run is not None
    return run


def warnings(harness: Harness, run_id: str) -> list[str]:
    return [log.message for log in stored(harness, run_id).logs if log.level is LogLevel.WARNING]


def tick(harness: Harness, **delta: float) -> list[Run]:
    harness.clock.advance(**delta)
    return run_due(harness).execute(harness.clock.now())


def test_a_start_is_skipped_while_the_previous_run_is_unfinished(harness: Harness) -> None:
    automation = add_automation(harness, schedule=hourly())
    [first] = tick(harness, hours=1)
    assert tick(harness, hours=1) == []
    assert warnings(harness, first.id) == [
        f"Scheduled start at 2026-01-05 12:00 UTC skipped: run {first.id} is still queued"
    ]
    assert stored(harness, first.id).skipped_start_at == harness.clock.now()
    assert tick(harness, minutes=1) == []
    assert len(warnings(harness, first.id)) == 1
    assert harness.presenter.next_run_at(automation) == datetime(2026, 1, 5, 13, tzinfo=UTC)
    execute_run(harness).execute(first.id)
    assert len(tick(harness, minutes=59)) == 1


def test_a_skipped_start_is_remembered_after_a_later_manual_run(harness: Harness) -> None:
    automation = add_automation(harness, schedule=hourly())
    [first] = tick(harness, hours=1)
    tick(harness, hours=1)
    execute_run(harness).execute(first.id)
    harness.clock.advance(minutes=5)
    manual = harness.start_run.execute(automation.id)
    execute_run(harness).execute(manual.id)
    assert harness.presenter.next_run_at(automation) == datetime(2026, 1, 5, 13, tzinfo=UTC)


def test_overlapping_starts_are_allowed_when_skipping_is_off(harness: Harness) -> None:
    add_automation(harness, schedule=hourly(skip_if_unfinished=False))
    assert len(tick(harness, hours=1)) == 1
    assert len(tick(harness, hours=1)) == 1


def test_a_failed_run_waiting_for_its_retry_blocks_the_schedule(harness: Harness) -> None:
    retrying = RetryPolicy(auto_retry_count=1, retry_delay_minutes=120)
    settings = {"fail_stage": "render"}
    run = started_run(harness, schedule=hourly(), retry_policy=retrying, settings=settings)
    failed = execute_run(harness).execute(run.id)
    assert failed.status is RunStatus.FAILED and failed.retry_at is not None
    assert tick(harness, hours=1) == []
    assert warnings(harness, run.id)[-1].endswith("is still waiting for an automatic retry")


def test_the_daily_cap_stops_scheduled_starts_until_the_next_day(harness: Harness) -> None:
    automation = add_automation(
        harness, schedule=hourly(skip_if_unfinished=False, max_runs_per_day=2)
    )
    assert len(tick(harness, hours=1)) == 1
    assert len(tick(harness, hours=1)) == 1
    assert tick(harness, hours=1) == []
    assert harness.presenter.next_run_at(automation) == datetime(2026, 1, 6, tzinfo=UTC)


def test_manual_runs_count_toward_the_daily_cap(harness: Harness) -> None:
    automation = add_automation(harness, schedule=hourly(max_runs_per_day=1))
    manual = harness.start_run.execute(automation.id)
    execute_run(harness).execute(manual.id)
    assert tick(harness, hours=1) == []
    assert harness.presenter.next_run_at(automation) == datetime(2026, 1, 6, tzinfo=UTC)


def test_starts_wait_for_the_active_hours(harness: Harness) -> None:
    window = hourly(skip_if_unfinished=False, active_from="12:00", active_until="13:00")
    automation = add_automation(harness, schedule=window)
    assert harness.presenter.next_run_at(automation) == datetime(2026, 1, 5, 12, tzinfo=UTC)
    assert tick(harness, hours=1) == []
    assert len(tick(harness, hours=1)) == 1
    assert harness.presenter.next_run_at(automation) == datetime(2026, 1, 6, 12, tzinfo=UTC)


def test_the_cap_with_an_unknown_zone_counts_nothing(harness: Harness) -> None:
    automation = add_automation(harness, schedule=hourly())
    broken = automation.model_copy(update={"schedule": hourly(timezone="Nowhere/City")})
    assert harness.presenter.started_on(broken, harness.clock.now().date()) == 0


def test_skip_messages_fall_back_to_utc_for_an_unknown_zone(harness: Harness) -> None:
    run = started_run(harness)
    automation = harness.automations.get(run.automation_id)
    assert automation is not None
    broken = automation.model_copy(update={"schedule": hourly(timezone="Nowhere/City")})
    slot = datetime(2026, 1, 5, 12, tzinfo=UTC)
    assert skip_message(broken, slot, run) == (
        f"Scheduled start at 2026-01-05 12:00 Nowhere/City skipped: run {run.id} is still queued"
    )


def created_at(harness: Harness, automation_id: str, moment: datetime) -> None:
    run = harness.start_run.execute(automation_id)
    harness.runs.update(run.id, lambda stored: stored.model_copy(update={"created_at": moment}))


def test_the_cap_counts_the_23_hour_day_in_the_schedule_zone(harness: Harness) -> None:
    automation = add_automation(harness, schedule=hourly(timezone="America/New_York"))
    for moment in (
        datetime(2026, 3, 8, 4, 59, tzinfo=UTC),
        datetime(2026, 3, 8, 5, tzinfo=UTC),
        datetime(2026, 3, 9, 3, 59, tzinfo=UTC),
        datetime(2026, 3, 9, 4, tzinfo=UTC),
    ):
        created_at(harness, automation.id, moment)
    counts = [harness.presenter.started_on(automation, date(2026, 3, day)) for day in (7, 8, 9)]
    assert counts == [1, 2, 1]


def test_marking_a_skip_keeps_the_latest_slot(harness: Harness) -> None:
    run = started_run(harness)
    later = harness.clock.now() + timedelta(hours=2)
    marked = marked_skip(later, run)
    assert marked_skip(harness.clock.now(), marked).skipped_start_at == later
