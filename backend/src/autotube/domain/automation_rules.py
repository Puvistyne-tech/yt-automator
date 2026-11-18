from __future__ import annotations

from collections.abc import Collection, Sequence

from pydantic import BaseModel

from autotube.domain.automations import AutomationInput, TargetInput
from autotube.domain.kids_rules import kids_errors
from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline_descriptors import PipelineDescriptor
from autotube.domain.publish_time import publish_time_errors
from autotube.domain.quality import review_policy_errors
from autotube.domain.schedule_timing import schedule_start_errors
from autotube.domain.validation import field_path, prefixed, validated_settings


def language_errors(languages: Sequence[str], descriptor: PipelineDescriptor) -> dict[str, str]:
    errors: dict[str, str] = {}
    for index, code in enumerate(languages):
        if code not in descriptor.language_codes:
            errors[field_path("languages", index)] = f"pipeline does not offer language {code!r}"
        elif code in languages[:index]:
            errors[field_path("languages", index)] = f"language {code!r} is listed twice"
    return errors


def variant_errors(
    index: int, target: TargetInput, descriptor: PipelineDescriptor
) -> dict[str, str]:
    return {
        field_path("targets", index, "variants", position): f"pipeline does not offer {variant!r}"
        for position, variant in enumerate(target.variants)
        if variant not in descriptor.variant_ids
    }


def target_errors(
    data: AutomationInput, descriptor: PipelineDescriptor, channel_ids: Collection[str]
) -> dict[str, str]:
    errors: dict[str, str] = {}
    for index, target in enumerate(data.targets):
        if target.language not in data.languages:
            message = f"language {target.language!r} is not one of the automation's languages"
            errors[field_path("targets", index, "language")] = message
        if target.channel_id not in channel_ids:
            message = f"channel {target.channel_id!r} does not exist"
            errors[field_path("targets", index, "channel_id")] = message
        errors |= variant_errors(index, target, descriptor)
        errors |= prefixed(publish_time_errors(target), "targets", index)
    return errors


def automation_errors(
    data: AutomationInput,
    descriptor: PipelineDescriptor | None,
    settings_model: type[BaseModel] | None,
    channel_ids: Collection[str],
) -> dict[str, str]:
    errors = prefixed(schedule_start_errors(data.schedule), "schedule")
    errors |= prefixed(review_policy_errors(data.review_policy), "review_policy")
    if descriptor is None or settings_model is None:
        return errors | {"pipeline_type": f"unknown pipeline type {data.pipeline_type!r}"}
    errors |= validated_settings(settings_model, data.settings)[1]
    errors |= language_errors(data.languages, descriptor)
    errors |= target_errors(data, descriptor, channel_ids)
    return errors | kids_errors(data.targets, descriptor)


def normalized_settings(settings_model: type[BaseModel], settings: JsonObject) -> JsonObject:
    return settings_model.model_validate(settings).model_dump(mode="json")
