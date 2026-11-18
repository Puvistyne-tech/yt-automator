from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from autotube.domain.automation_export import (
    APP_NAME,
    FORMAT_VERSION,
    AutomationDocument,
    automation_document,
    channel_choice_errors,
    imported_input,
    read_document,
    resolved_channels,
    unresolved_channels,
)
from autotube.domain.automations import Automation, Target
from autotube.domain.channels import Channel

NOW = datetime(2026, 1, 2, 3, 4, tzinfo=UTC)


def channel(channel_id: str, youtube_id: str | None = None) -> Channel:
    return Channel(
        id=channel_id,
        credential_id="cred",
        youtube_channel_id=youtube_id or f"UC-{channel_id}",
        title=f"Channel {channel_id}",
        connected_at=NOW,
    )


def target(channel_id: str, target_id: str = "t1") -> Target:
    return Target(id=target_id, channel_id=channel_id, language="en", variants=("landscape",))


def automation(*targets: Target) -> Automation:
    return Automation(
        id="auto-1",
        name="Bedtime",
        pipeline_type="fake",
        settings={"topic": "owls"},
        languages=("en",),
        targets=targets or (target("chan-1"),),
        created_at=NOW,
        updated_at=NOW,
    )


def raw_document(**changes: Any) -> dict[str, Any]:
    document = automation_document(automation(), [channel("chan-1")], NOW)
    return document.model_dump(mode="json") | changes


def test_document_holds_portable_fields_only() -> None:
    dumped = raw_document()
    assert set(dumped) == {"app", "format_version", "exported_at", "automation", "channels"}
    assert (dumped["app"], dumped["format_version"]) == (APP_NAME, FORMAT_VERSION)
    assert set(dumped["automation"]) == {
        "name",
        "description",
        "pipeline_type",
        "settings",
        "languages",
        "schedule",
        "review_policy",
        "retry_policy",
        "targets",
    }
    assert "id" not in dumped["automation"]["targets"][0]
    assert dumped["channels"] == [
        {"id": "chan-1", "youtube_channel_id": "UC-chan-1", "title": "Channel chan-1"}
    ]


def test_document_lists_only_target_channels_once() -> None:
    source = automation(target("chan-1"), target("chan-1", "t2"), target("gone", "t3"))
    document = automation_document(source, [channel("chan-1"), channel("other")], NOW)
    assert [item.id for item in document.channels] == ["chan-1"]


def test_read_document_round_trips() -> None:
    document, errors = read_document(raw_document())
    assert errors == {}
    assert document is not None and document.automation.name == "Bedtime"


def test_read_document_fills_fields_missing_from_old_exports() -> None:
    raw = raw_document()
    for key in ("schedule", "review_policy", "retry_policy", "description"):
        del raw["automation"][key]
    del raw["channels"]
    document, errors = read_document(raw)
    assert errors == {} and document is not None
    assert document.automation.retry_policy.retry_delay_minutes == 10
    assert document.channels == ()


def test_read_document_refuses_newer_format_with_clear_message() -> None:
    document, errors = read_document(raw_document(format_version=FORMAT_VERSION + 1))
    assert document is None
    message = errors["format_version"]
    assert f"newer {APP_NAME}" in message and f"format {FORMAT_VERSION + 1}" in message
    assert "update" in message


@pytest.mark.parametrize("app", [None, "Something else"])
def test_read_document_refuses_other_files(app: str | None) -> None:
    document, errors = read_document(raw_document(app=app))
    assert document is None and "app" in errors


def test_read_document_reports_field_errors() -> None:
    raw = raw_document()
    raw["automation"]["languages"] = []
    document, errors = read_document(raw)
    assert document is None and set(errors) == {"automation.languages"}


def parsed(*targets: Target, channels: tuple[Channel, ...] = ()) -> AutomationDocument:
    return automation_document(automation(*targets), list(channels), NOW)


def test_resolved_channels_keeps_known_and_matches_youtube_ids() -> None:
    document = parsed(
        target("chan-1"), target("old", "t2"), target("lost", "t3"), channels=(channel("old"),)
    )
    local = [channel("chan-1"), channel("new", youtube_id="UC-old")]
    mapping = resolved_channels(document, local, {})
    assert mapping == {"chan-1": "chan-1", "old": "new"}
    assert [item.id for item in unresolved_channels(document, mapping)] == ["lost"]


def test_resolved_channels_prefers_explicit_choices() -> None:
    document = parsed(target("chan-1"), target("lost", "t2"))
    mapping = resolved_channels(document, [channel("chan-1")], {"chan-1": None, "lost": "x"})
    assert mapping == {"chan-1": None, "lost": "x"}


def test_unresolved_channels_carry_exported_title_or_bare_id() -> None:
    document = parsed(target("lost"), channels=(channel("lost"),))
    assert unresolved_channels(document, {})[0].title == "Channel lost"
    bare = parsed(target("gone"))
    assert unresolved_channels(bare, {})[0].title == ""


def test_channel_choice_errors_name_missing_choices() -> None:
    errors = channel_choice_errors({"a": "chan-1", "b": "nope", "c": None}, {"chan-1"})
    assert set(errors) == {"channel_map.b"}


def test_imported_input_is_disabled_renamed_and_mapped() -> None:
    document = parsed(target("a"), target("b", "t2"), target("c", "t3"))
    data = imported_input(document, {"a": "chan-1", "b": None})
    assert (data.name, data.enabled) == ("Bedtime (imported)", False)
    assert [item.channel_id for item in data.targets] == ["chan-1", "c"]
    assert all(item.id is None for item in data.targets)
