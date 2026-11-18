from __future__ import annotations

from collections.abc import Mapping, Sequence

from pydantic import ValidationError

from autotube.domain.providers import ProviderChoice, ProviderConfig
from autotube.domain.validation import field_errors, field_path, validated_settings
from autotube.infrastructure.providers.registry import AnySpec


def choice_option_errors(spec: AnySpec, choice: ProviderChoice, prefix: str) -> dict[str, str]:
    return validated_settings(spec.options, dict(choice.options), prefix)[1]


def matching_spec(
    specs: Mapping[str, AnySpec], config: ProviderConfig, choice: ProviderChoice
) -> AnySpec | None:
    spec = specs.get(choice.provider_id)
    return spec if spec is not None and spec.capability is config.capability else None


def config_option_errors(
    specs: Mapping[str, AnySpec], configs: Sequence[ProviderConfig]
) -> dict[str, str]:
    errors: dict[str, str] = {}
    for index, config in enumerate(configs):
        for position, choice in enumerate(config.chain):
            spec = matching_spec(specs, config, choice)
            if spec is not None:
                prefix = field_path(index, "chain", position, "options")
                errors |= choice_option_errors(spec, choice, prefix)
    return errors


def invalid_options_reason(error: ValidationError) -> str:
    details = "; ".join(f"{path}: {message}" for path, message in field_errors(error).items())
    return f"invalid options ({details})"
