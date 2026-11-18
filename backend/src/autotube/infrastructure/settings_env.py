from __future__ import annotations

from autotube.domain.settings_overrides import SettingOverride
from autotube.infrastructure.config import ENV_PREFIX, RuntimeConfig

ENV_SETTINGS: dict[str, str] = {
    "youtube_caption_track_name": "caption_track_name",
    "max_run_log_entries": "max_run_log_entries",
    "log_level": "log_level",
    "doctor_min_free_gb": "doctor_min_free_gb",
    "cleanup_interval_hours": "cleanup_interval_hours",
}


def env_name(config_field: str) -> str:
    return ENV_PREFIX + config_field.upper()


def lock_reason(config_field: str) -> str:
    return f"Set by the environment variable {env_name(config_field)}; unset it to change it here"


def settings_overrides(config: RuntimeConfig) -> tuple[SettingOverride, ...]:
    values = config.model_dump(mode="json", include=set(ENV_SETTINGS))
    return tuple(
        SettingOverride(field=setting, value=values[name], reason=lock_reason(name))
        for name, setting in ENV_SETTINGS.items()
        if name in config.model_fields_set
    )
