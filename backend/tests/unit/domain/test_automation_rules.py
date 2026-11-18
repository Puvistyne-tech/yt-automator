from __future__ import annotations

from typing import Any

import pytest

from automator.domain.automation_rules import automation_errors, normalized_settings
from automator.domain.automations import Automation
from automator.domain.schedules import Schedule, ScheduleKind
from tests.fixtures.builders import automation_input, target_input
from tests.fixtures.fake_pipeline import FakePipeline, FakeSettings, kids_pipeline

PIPELINE = FakePipeline()
CHANNELS = {"chan-1", "chan-2"}


def errors_for(**overrides: Any) -> dict[str, str]:
    data = automation_input(**overrides)
    return automation_errors(data, PIPELINE.descriptor, PIPELINE.settings_model, CHANNELS)


def test_valid_input_has_no_errors() -> None:
    assert errors_for() == {}


def test_unknown_pipeline_is_reported() -> None:
    data = automation_input(pipeline_type="nope")
    assert automation_errors(data, None, None, CHANNELS) == {
        "pipeline_type": "unknown pipeline type 'nope'"
    }


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"settings": {"topic": ""}}, "settings.topic"),
        ({"settings": {"score": 300}}, "settings.score"),
        ({"settings": {"unknown": 1}}, "settings.unknown"),
        ({"languages": ("en", "fr")}, "languages.1"),
        ({"languages": ("en", "en")}, "languages.1"),
        ({"targets": (target_input(language="ta"),)}, "targets.0.language"),
        ({"targets": (target_input(channel_id="ghost"),)}, "targets.0.channel_id"),
        ({"targets": (target_input(variants=("landscape", "square")),)}, "targets.0.variants.1"),
        ({"schedule": Schedule(kind=ScheduleKind.INTERVAL, every_hours=0)}, "schedule.every_hours"),
        ({"schedule": Schedule(kind=ScheduleKind.CRON, cron="* *")}, "schedule.cron"),
        ({"schedule": Schedule(timezone="Bad/Zone")}, "schedule.timezone"),
    ],
)
def test_each_rule_reports_its_field_path(overrides: dict[str, Any], field: str) -> None:
    assert list(errors_for(**overrides)) == [field]


def test_errors_accumulate_across_rules() -> None:
    errors = errors_for(
        languages=("en", "xx"),
        targets=(target_input(channel_id="ghost", language="ta"),),
        schedule=Schedule(kind=ScheduleKind.INTERVAL),
    )
    assert set(errors) == {
        "languages.1",
        "targets.0.language",
        "targets.0.channel_id",
        "schedule.every_hours",
    }


def test_unknown_pipeline_still_reports_schedule_errors() -> None:
    data = automation_input(pipeline_type="nope", schedule=Schedule(kind=ScheduleKind.CRON))
    assert set(automation_errors(data, None, None, CHANNELS)) == {"pipeline_type", "schedule.cron"}


@pytest.mark.parametrize(("value", "has_error"), [(None, False), (True, False), (False, True)])
def test_kids_pipeline_refuses_targets_not_made_for_kids(
    value: bool | None, has_error: bool
) -> None:
    kids = kids_pipeline()
    data = automation_input(
        pipeline_type=kids.type_id, targets=(target_input(made_for_kids=value),)
    )
    errors = automation_errors(data, kids.descriptor, kids.settings_model, CHANNELS)
    assert ("targets.0.made_for_kids" in errors) is has_error


def test_regular_pipeline_allows_explicit_made_for_kids_choice() -> None:
    assert errors_for(targets=(target_input(made_for_kids=False),)) == {}
    assert errors_for(targets=(target_input(made_for_kids=True),)) == {}


def test_normalized_settings_fill_defaults() -> None:
    assert normalized_settings(FakeSettings, {"topic": "owls"}) == {
        "topic": "owls",
        "fail_stage": "",
        "score": 90.0,
        "with_thumbnail": True,
        "extra_meta": {},
    }


def test_automation_round_trips_to_input(automation: Automation) -> None:
    again = automation.as_input()
    assert again.name == automation.name
    assert again.targets[0].id == automation.targets[0].id
    assert automation.targets_channel("chan-1") and not automation.targets_channel("chan-9")
