from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence

from pydantic import AwareDatetime, Field, ValidationError

from autotube.domain.automations import (
    Automation,
    AutomationFields,
    AutomationInput,
    TargetFields,
    TargetInput,
)
from autotube.domain.channels import Channel
from autotube.domain.model_base import DomainModel, JsonObject
from autotube.domain.validation import field_errors, field_path

APP_NAME = "AutoTube"
FORMAT_VERSION = 1
IMPORTED_SUFFIX = " (imported)"

ChannelChoices = Mapping[str, str | None]


def channel_ids(targets: Sequence[TargetFields]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(target.channel_id for target in targets))


def imported_name(name: str) -> str:
    return name if name.endswith(IMPORTED_SUFFIX) else f"{name}{IMPORTED_SUFFIX}"


class ExportedChannel(DomainModel):
    id: str = Field(min_length=1)
    youtube_channel_id: str = ""
    title: str = ""


class ExportedAutomation(AutomationFields):
    enabled: bool = Field(default=False, exclude=True)
    targets: tuple[TargetFields, ...] = ()


class AutomationDocument(DomainModel):
    app: str = APP_NAME
    format_version: int = Field(default=FORMAT_VERSION, ge=1)
    exported_at: AwareDatetime | None = None
    automation: ExportedAutomation
    channels: tuple[ExportedChannel, ...] = ()

    def exported_channel(self, channel_id: str) -> ExportedChannel:
        found = (item for item in self.channels if item.id == channel_id)
        return next(found, ExportedChannel(id=channel_id))


class ImportPreview(DomainModel):
    automation: AutomationInput
    unknown_channels: tuple[ExportedChannel, ...] = ()


def exported_channels(
    automation: Automation, channels: Sequence[Channel]
) -> tuple[ExportedChannel, ...]:
    used = channel_ids(automation.targets)
    return tuple(
        ExportedChannel(id=item.id, youtube_channel_id=item.youtube_channel_id, title=item.title)
        for item in channels
        if item.id in used
    )


def automation_document(
    automation: Automation, channels: Sequence[Channel], exported_at: AwareDatetime
) -> AutomationDocument:
    fields = automation.model_dump(include=set(AutomationFields.model_fields) - {"enabled"})
    targets = tuple(
        TargetFields(**target.model_dump(exclude={"id"})) for target in automation.targets
    )
    return AutomationDocument(
        exported_at=exported_at,
        automation=ExportedAutomation(**fields, targets=targets),
        channels=exported_channels(automation, channels),
    )


def format_errors(raw: JsonObject) -> dict[str, str]:
    if raw.get("app") != APP_NAME:
        return {"app": f"this file is not an {APP_NAME} automation export"}
    version = raw.get("format_version")
    if isinstance(version, int) and not isinstance(version, bool) and version > FORMAT_VERSION:
        return {
            "format_version": (
                f"this file was exported by a newer {APP_NAME} (format {version}); this version "
                f"reads format {FORMAT_VERSION} and older, so update {APP_NAME} to import it"
            )
        }
    return {}


def read_document(raw: JsonObject) -> tuple[AutomationDocument | None, dict[str, str]]:
    errors = format_errors(raw)
    if errors:
        return None, errors
    try:
        return AutomationDocument.model_validate(raw), {}
    except ValidationError as error:
        return None, field_errors(error)


def matched_channel(exported: ExportedChannel, channels: Sequence[Channel]) -> str | None:
    if exported.youtube_channel_id == "":
        return None
    found = (item.id for item in channels if item.youtube_channel_id == exported.youtube_channel_id)
    return next(found, None)


def resolved_channels(
    document: AutomationDocument, channels: Sequence[Channel], chosen: ChannelChoices
) -> dict[str, str | None]:
    local = {item.id for item in channels}
    mapping: dict[str, str | None] = {}
    for channel_id in channel_ids(document.automation.targets):
        if channel_id in chosen:
            mapping[channel_id] = chosen[channel_id]
        elif channel_id in local:
            mapping[channel_id] = channel_id
        elif match := matched_channel(document.exported_channel(channel_id), channels):
            mapping[channel_id] = match
    return mapping


def unresolved_channels(
    document: AutomationDocument, mapping: ChannelChoices
) -> tuple[ExportedChannel, ...]:
    return tuple(
        document.exported_channel(channel_id)
        for channel_id in channel_ids(document.automation.targets)
        if channel_id not in mapping
    )


def channel_choice_errors(chosen: ChannelChoices, local: Collection[str]) -> dict[str, str]:
    return {
        field_path("channel_map", exported): f"channel {local_id!r} does not exist"
        for exported, local_id in chosen.items()
        if local_id is not None and local_id not in local
    }


def imported_input(document: AutomationDocument, mapping: ChannelChoices) -> AutomationInput:
    source = document.automation
    targets = [
        target.model_copy(update={"channel_id": mapping.get(target.channel_id, target.channel_id)})
        for target in source.targets
        if not (target.channel_id in mapping and mapping[target.channel_id] is None)
    ]
    fields = source.model_dump(exclude={"targets", "enabled", "name"})
    return AutomationInput(
        **fields,
        name=imported_name(source.name),
        enabled=False,
        targets=tuple(TargetInput(**target.model_dump()) for target in targets),
    )


def without_missing_channel_errors(
    errors: Mapping[str, str], data: AutomationInput, local: Collection[str]
) -> dict[str, str]:
    hidden = {
        field_path("targets", index, "channel_id")
        for index, target in enumerate(data.targets)
        if target.channel_id not in local
    }
    return {path: message for path, message in errors.items() if path not in hidden}


def missing_choice_errors(unknown: Sequence[ExportedChannel]) -> dict[str, str]:
    return {
        field_path("channel_map", item.id): (
            f"channel {item.title or item.id!r} is not connected here: "
            "choose a channel for its targets or leave them out"
        )
        for item in unknown
    }


def refusal_message(errors: Mapping[str, str]) -> str:
    reason = errors.get("format_version") or errors.get("app")
    return f"This file cannot be imported: {reason}." if reason else "Validation failed"
