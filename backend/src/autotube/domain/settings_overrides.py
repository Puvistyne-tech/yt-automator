from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import JsonValue

from autotube.domain.diagnostics import DoctorPolicy
from autotube.domain.model_base import DomainModel
from autotube.domain.run_parts import RunLogPolicy
from autotube.domain.settings import AppSettings, AppSettingsInput, input_fields


class SettingOverride(DomainModel):
    field: str
    value: JsonValue
    reason: str


Overrides = Sequence[SettingOverride]


def stored_settings(payload: Mapping[str, Any] | None) -> AppSettingsInput:
    known = input_fields()
    values = {name: value for name, value in (payload or {}).items() if name in known}
    return AppSettingsInput.model_validate(values)


def override_values(overrides: Overrides) -> dict[str, JsonValue]:
    return {override.field: override.value for override in overrides}


def effective_settings(
    stored: AppSettingsInput, overrides: Overrides, data_dir: str
) -> AppSettings:
    values = stored.model_dump(mode="json") | override_values(overrides)
    locked = {override.field: override.reason for override in overrides}
    return AppSettings.model_validate(values | {"data_dir": data_dir, "locked": locked})


def storable_settings(
    changes: AppSettingsInput, stored: AppSettingsInput, locked: Sequence[str]
) -> AppSettingsInput:
    kept = {name: getattr(stored, name) for name in locked}
    return changes.model_copy(update=kept)


def run_log_policy(settings: AppSettingsInput) -> RunLogPolicy:
    return RunLogPolicy(max_entries=settings.max_run_log_entries)


def doctor_policy(base: DoctorPolicy, settings: AppSettingsInput) -> DoctorPolicy:
    return base.model_copy(update={"min_free_gb": settings.doctor_min_free_gb})
