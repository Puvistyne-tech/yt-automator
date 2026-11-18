from __future__ import annotations

import json
from pathlib import Path

import pytest

from automator.domain.capabilities import Capability, TextRequest
from automator.domain.providers import ProviderChoice, ProviderConfig, provider_config_errors
from automator.infrastructure.providers.catalog import LocalProviderCatalog, build_provider_catalog
from automator.infrastructure.providers.registry import default_order
from automator.shared.errors import RuleConflict, UpstreamFailure, ValidationFailed
from tests.fixtures.fake_runtime import InMemorySecrets
from tests.unit.infrastructure.providers.fakes import host, make_context

EXPECTED_ORDER = {
    Capability.LLM: ["groq", "gemini", "ollama", "offline_text"],
    Capability.IMAGE: ["mflux", "offline_image"],
    Capability.MOTION: ["depthflow", "ffmpeg_pan_zoom"],
    Capability.TTS: ["edge_tts", "kokoro", "espeak", "offline_speech"],
    Capability.MUSIC: ["ace_step", "library_music", "synth_music"],
    Capability.MEDIA: ["ffmpeg"],
}


def catalog(tmp_path: Path, **secrets: str) -> LocalProviderCatalog:
    tools = host(binaries=frozenset({"ffmpeg", "ffprobe", "espeak-ng"}))
    return LocalProviderCatalog(make_context(tmp_path, probe=tools, secrets=secrets))


def config(capability: Capability, *choices: ProviderChoice) -> ProviderConfig:
    return ProviderConfig(capability=capability, chain=choices)


def test_default_order_puts_real_providers_first_and_offline_last() -> None:
    assert {capability: default_order(capability) for capability in Capability} == EXPECTED_ORDER


def test_descriptors_report_live_availability_and_option_schemas(tmp_path: Path) -> None:
    descriptors = {item.provider_id: item for item in catalog(tmp_path).descriptors()}
    assert len(descriptors) == 16
    assert descriptors["offline_text"].available
    assert not descriptors["groq"].available
    assert descriptors["groq"].unavailable_reason == "set the Groq API key secret (groq_api_key)"
    assert descriptors["groq"].required_secrets == ("groq_api_key",)
    assert not descriptors["edge_tts"].offline
    assert descriptors["espeak"].available
    assert "Model" in json.dumps(descriptors["groq"].options_schema["properties"])
    assert (
        provider_config_errors(
            [config(Capability.LLM, ProviderChoice(provider_id="groq"))], list(descriptors.values())
        )
        == {}
    )


def test_secrets_are_declared(tmp_path: Path) -> None:
    names = [secret.name for secret in catalog(tmp_path).secrets()]
    assert names == ["groq_api_key", "gemini_api_key", "huggingface_token"]


def test_resolver_without_config_uses_first_available_default(tmp_path: Path) -> None:
    resolver = catalog(tmp_path).resolver([])
    assert resolver.resolve(Capability.LLM).provider_id == "offline_text"
    assert resolver.resolve(Capability.TTS).provider_id == "espeak"
    assert resolver.resolve(Capability.MEDIA).provider_id == "ffmpeg"
    with_key = catalog(tmp_path, groq_api_key="k").resolver([])
    assert with_key.resolve(Capability.LLM).provider_id == "groq"


def test_resolver_honours_chain_order_enabled_and_options(tmp_path: Path) -> None:
    chain = config(
        Capability.LLM,
        ProviderChoice(provider_id="gemini", enabled=False),
        ProviderChoice(provider_id="offline_text", options={"template": "T {topic}"}),
        ProviderChoice(provider_id="groq"),
    )
    text = (
        catalog(tmp_path, gemini_api_key="g", groq_api_key="k")
        .resolver([chain])
        .resolve(Capability.LLM)
    )
    assert text.provider_id == "offline_text"
    assert text.generate(TextRequest(prompt="owl")) == "T owl"


def test_resolver_rejects_invalid_options(tmp_path: Path) -> None:
    chain = config(
        Capability.LLM, ProviderChoice(provider_id="offline_text", options={"topic_words": 0})
    )
    with pytest.raises(ValidationFailed) as raised:
        catalog(tmp_path).resolver([chain]).resolve(Capability.LLM)
    assert list(raised.value.fields) == ["llm.chain.0.options.topic_words"]


def test_resolver_explains_when_nothing_is_available(tmp_path: Path) -> None:
    chain = config(
        Capability.LLM,
        ProviderChoice(provider_id="groq"),
        ProviderChoice(provider_id="offline_text", enabled=False),
        ProviderChoice(provider_id="mflux"),
    )
    with pytest.raises(RuleConflict) as raised:
        catalog(tmp_path).resolver([chain]).resolve(Capability.LLM)
    assert raised.value.code == "provider_unavailable"
    assert raised.value.message == (
        "No llm provider is available: groq: set the Groq API key secret (groq_api_key); "
        "offline_text: disabled; mflux: unknown llm provider"
    )


def test_fallback_proxy_moves_on_after_upstream_failure(tmp_path: Path) -> None:
    chain = config(
        Capability.LLM,
        ProviderChoice(provider_id="groq"),
        ProviderChoice(provider_id="offline_text"),
    )
    text = catalog(tmp_path, groq_api_key="k").resolver([chain]).resolve(Capability.LLM)
    assert text.provider_id == "groq"
    reply = text.generate(TextRequest(prompt="owl", images=(tmp_path / "x.png",)))
    assert reply == "Offline draft. owl"
    assert text.provider_id == "offline_text"


def test_fallback_raises_when_every_provider_fails(tmp_path: Path) -> None:
    chain = config(Capability.LLM, ProviderChoice(provider_id="groq", options={"max_retries": 0}))
    text = catalog(tmp_path, groq_api_key="k").resolver([chain]).resolve(Capability.LLM)
    with pytest.raises(
        UpstreamFailure, match="every llm provider failed: groq: Groq request failed"
    ):
        text.generate(TextRequest(prompt="owl"))


def test_build_provider_catalog_wires_real_context(tmp_path: Path) -> None:
    built = build_provider_catalog(InMemorySecrets(), tmp_path)
    assert {item.provider_id for item in built.descriptors() if item.available} >= {
        "offline_text",
        "offline_image",
        "offline_speech",
        "synth_music",
    }
