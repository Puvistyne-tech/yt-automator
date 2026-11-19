from __future__ import annotations

import pytest

from autotube.domain.capabilities import Capability
from autotube.domain.providers import ProviderDescriptor, is_placeholder

DESCRIPTORS = (
    ProviderDescriptor(provider_id="writer", capability=Capability.LLM, name="Writer"),
    ProviderDescriptor(
        provider_id="stand-in", capability=Capability.LLM, name="Stand-in", placeholder=True
    ),
)


@pytest.mark.parametrize(
    ("provider_id", "placeholder"), [("stand-in", True), ("writer", False), ("missing", False)]
)
def test_a_provider_is_a_placeholder_only_when_its_descriptor_says_so(
    provider_id: str, placeholder: bool
) -> None:
    assert is_placeholder(provider_id, DESCRIPTORS) is placeholder
