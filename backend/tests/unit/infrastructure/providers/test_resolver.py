from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from autotube.domain.capabilities import Capability, TextRequest
from autotube.domain.model_base import JsonObject
from autotube.domain.providers import ProviderChoice, ProviderConfig
from autotube.infrastructure.providers.llm.offline_text import OfflineTextOptions
from autotube.infrastructure.providers.option_validation import invalid_options_reason
from autotube.shared.errors import RuleConflict
from tests.unit.infrastructure.providers.fakes import chain_config, local_catalog

ZERO_WORDS: JsonObject = {"topic_words": 0}
ZERO_WORDS_REASON = (
    "offline_text: invalid options (topic_words: Input should be greater than or equal to 1)"
)


@pytest.mark.parametrize(
    "configs", [[], [chain_config(Capability.LLM)]], ids=["no config", "empty chain"]
)
def test_resolver_falls_back_to_the_default_order(
    tmp_path: Path, configs: list[ProviderConfig]
) -> None:
    resolver = local_catalog(tmp_path).resolver(configs)
    assert resolver.resolve(Capability.LLM).provider_id == "offline_text"
    assert resolver.resolve(Capability.TTS).provider_id == "espeak"
    assert resolver.resolve(Capability.MEDIA).provider_id == "ffmpeg"


def test_resolver_prefers_a_default_provider_once_its_secret_is_set(tmp_path: Path) -> None:
    resolver = local_catalog(tmp_path, groq_api_key="k").resolver([])
    assert resolver.resolve(Capability.LLM).provider_id == "groq"


def test_resolver_honours_chain_order_enabled_and_options(tmp_path: Path) -> None:
    chain = chain_config(
        Capability.LLM,
        ProviderChoice(provider_id="gemini", enabled=False),
        ProviderChoice(provider_id="offline_text", options={"template": "T {topic}"}),
        ProviderChoice(provider_id="groq"),
    )
    catalog = local_catalog(tmp_path, gemini_api_key="g", groq_api_key="k")
    text = catalog.resolver([chain]).resolve(Capability.LLM)
    assert text.provider_id == "offline_text"
    assert text.generate(TextRequest(prompt="owl")) == "T owl"


def test_resolver_skips_invalid_options_and_records_why(tmp_path: Path) -> None:
    chain = chain_config(
        Capability.LLM,
        ProviderChoice(provider_id="offline_text", options=ZERO_WORDS),
        ProviderChoice(provider_id="groq"),
    )
    resolver = local_catalog(tmp_path, groq_api_key="k").resolver([chain])
    assert resolver.resolve(Capability.LLM).provider_id == "groq"
    assert resolver.skipped[Capability.LLM] == [ZERO_WORDS_REASON]


def test_resolver_explains_when_nothing_is_available(tmp_path: Path) -> None:
    chain = chain_config(
        Capability.LLM,
        ProviderChoice(provider_id="groq"),
        ProviderChoice(provider_id="offline_text", options=ZERO_WORDS),
        ProviderChoice(provider_id="mflux"),
        ProviderChoice(provider_id="nope"),
        ProviderChoice(provider_id="ollama", enabled=False),
    )
    with pytest.raises(RuleConflict) as raised:
        local_catalog(tmp_path).resolver([chain]).resolve(Capability.LLM)
    assert raised.value.code == "provider_unavailable"
    assert raised.value.message == (
        "No llm provider is available: groq: set the Groq API key secret (groq_api_key); "
        f"{ZERO_WORDS_REASON}; mflux: unknown llm provider; nope: unknown llm provider; "
        "ollama: disabled"
    )


def test_option_errors_use_the_saved_config_field_paths(tmp_path: Path) -> None:
    configs = [
        chain_config(Capability.MEDIA, ProviderChoice(provider_id="ffmpeg")),
        chain_config(
            Capability.TTS,
            ProviderChoice(provider_id="espeak", options={"alignment": {"min_match": 2}}),
            ProviderChoice(provider_id="offline_speech", enabled=False, options={"pace": 1}),
            ProviderChoice(provider_id="groq", options={"model": ""}),
            ProviderChoice(provider_id="nope", options={"x": 1}),
        ),
    ]
    assert local_catalog(tmp_path).option_errors(configs) == {
        "1.chain.0.options.alignment.min_match": "Input should be less than or equal to 1",
        "1.chain.1.options.pace": "Extra inputs are not permitted",
    }


def test_option_errors_are_empty_for_valid_options(tmp_path: Path) -> None:
    chain = chain_config(
        Capability.LLM, ProviderChoice(provider_id="groq", options={"max_retries": 0})
    )
    assert local_catalog(tmp_path).option_errors([chain]) == {}


def test_invalid_options_reason_joins_every_field_error() -> None:
    with pytest.raises(ValidationError) as raised:
        OfflineTextOptions.model_validate({"topic_words": 0, "nope": 1})
    assert invalid_options_reason(raised.value) == (
        "invalid options (topic_words: Input should be greater than or equal to 1; "
        "nope: Extra inputs are not permitted)"
    )
