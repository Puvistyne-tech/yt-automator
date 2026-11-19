from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from autotube.domain.capabilities import Capability, TextGenerator, TextRequest
from autotube.domain.providers import ProviderConfig, ProviderDescriptor
from autotube.domain.secrets import SecretDefinition
from autotube.domain.validation import field_path

DESCRIPTORS = (
    ProviderDescriptor(provider_id="fake-llm", capability=Capability.LLM, name="Fake LLM"),
    ProviderDescriptor(
        provider_id="cloud-llm",
        capability=Capability.LLM,
        name="Cloud LLM",
        required_secrets=("cloud_api_key",),
        offline=False,
    ),
    ProviderDescriptor(provider_id="fake-image", capability=Capability.IMAGE, name="Fake Image"),
)
PLACEHOLDER_LLM = ProviderDescriptor(
    provider_id="placeholder-llm", capability=Capability.LLM, name="Stand-in", placeholder=True
)
SECRETS = (
    SecretDefinition(name="cloud_api_key", title="Cloud API key", description="For Cloud LLM"),
)


class EchoTextGenerator:
    provider_id = "fake-llm"

    def __init__(self) -> None:
        self.requests: list[TextRequest] = []

    def generate(self, request: TextRequest) -> str:
        self.requests.append(request)
        return f"story about {request.prompt}"


class FakeResolver:
    def __init__(self, configs: Sequence[ProviderConfig], text: EchoTextGenerator) -> None:
        self.configs = list(configs)
        self.text = text

    def resolve(self, capability: Capability) -> Any:
        if capability is Capability.LLM:
            return self.text
        raise LookupError(f"no provider for {capability.value}")


class FakeProviderCatalog:
    def __init__(self) -> None:
        self.text = EchoTextGenerator()
        self.resolved_with: list[list[ProviderConfig]] = []

    def descriptors(self) -> list[ProviderDescriptor]:
        return list(DESCRIPTORS)

    def secrets(self) -> list[SecretDefinition]:
        return list(SECRETS)

    def option_errors(self, configs: Sequence[ProviderConfig]) -> dict[str, str]:
        return {
            field_path(index, "chain", position, "options", "model"): "model must not be empty"
            for index, config in enumerate(configs)
            for position, choice in enumerate(config.chain)
            if choice.options.get("model") == ""
        }

    def resolver(self, configs: Sequence[ProviderConfig]) -> FakeResolver:
        self.resolved_with.append(list(configs))
        return FakeResolver(configs, self.text)


class WriterResolver(FakeResolver):
    def __init__(
        self,
        configs: Sequence[ProviderConfig],
        text: EchoTextGenerator,
        writer: TextGenerator | None,
    ) -> None:
        super().__init__(configs, text)
        self.writer = writer

    def resolve(self, capability: Capability) -> Any:
        if capability is Capability.LLM and self.writer is not None:
            return self.writer
        raise LookupError(f"no provider for {capability.value}")


class WriterCatalog(FakeProviderCatalog):
    def __init__(self, writer: TextGenerator | None) -> None:
        super().__init__()
        self.writer = writer

    def descriptors(self) -> list[ProviderDescriptor]:
        return [*DESCRIPTORS, PLACEHOLDER_LLM]

    def resolver(self, configs: Sequence[ProviderConfig]) -> FakeResolver:
        self.resolved_with.append(list(configs))
        return WriterResolver(configs, self.text, self.writer)
