from __future__ import annotations

from collections.abc import Sequence

from autotube.domain.automations import TargetFields, TargetInput
from autotube.domain.channels import ChannelDefaults, Privacy
from autotube.domain.pipeline_descriptors import PipelineDescriptor
from autotube.domain.validation import field_path

KIDS_REQUIRED = "must be made for kids: this pipeline produces kids' content"


def kids_errors(targets: Sequence[TargetInput], descriptor: PipelineDescriptor) -> dict[str, str]:
    if not descriptor.makes_kids_content:
        return {}
    return {
        field_path("targets", index, "made_for_kids"): KIDS_REQUIRED
        for index, target in enumerate(targets)
        if target.made_for_kids is False
    }


def enforce_kids_content(
    targets: Sequence[TargetInput], descriptor: PipelineDescriptor
) -> tuple[TargetInput, ...]:
    if not descriptor.makes_kids_content:
        return tuple(targets)
    return tuple(target.model_copy(update={"made_for_kids": True}) for target in targets)


def effective_made_for_kids(
    target: TargetFields, defaults: ChannelDefaults, descriptor: PipelineDescriptor
) -> bool:
    if descriptor.makes_kids_content:
        return True
    return defaults.made_for_kids if target.made_for_kids is None else target.made_for_kids


def effective_privacy(target: TargetFields, defaults: ChannelDefaults) -> Privacy:
    return defaults.privacy if target.privacy is None else target.privacy
