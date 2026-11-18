from __future__ import annotations

import json
from pathlib import Path

from autotube.domain.capabilities import Capability
from autotube.domain.providers import ProviderChoice, provider_config_errors
from autotube.infrastructure.providers.catalog import build_provider_catalog
from autotube.infrastructure.providers.registry import ALL_SPECS, default_order
from tests.fixtures.fake_runtime import InMemorySecrets
from tests.unit.infrastructure.providers.fakes import chain_config, local_catalog

EXPECTED_ORDER = {
    Capability.LLM: ["groq", "gemini", "ollama", "offline_text"],
    Capability.IMAGE: ["mflux", "offline_image"],
    Capability.MOTION: ["ltx_mlx", "depthflow", "ffmpeg_pan_zoom"],
    Capability.TTS: ["edge_tts", "kokoro", "espeak", "offline_speech"],
    Capability.MUSIC: ["ace_step", "library_music", "synth_music"],
    Capability.MEDIA: ["ffmpeg"],
}
SECRET_PROVIDERS = {
    "groq": ("groq_api_key",),
    "gemini": ("gemini_api_key",),
}


def test_default_order_puts_real_providers_first_and_offline_last() -> None:
    assert {capability: default_order(capability) for capability in Capability} == EXPECTED_ORDER


def test_descriptors_report_live_availability_and_option_schemas(tmp_path: Path) -> None:
    descriptors = {item.provider_id: item for item in local_catalog(tmp_path).descriptors()}
    assert list(descriptors) == [spec.provider_id for spec in ALL_SPECS]
    assert descriptors["offline_text"].available
    assert not descriptors["groq"].available
    assert descriptors["groq"].unavailable_reason == "set the Groq API key secret (groq_api_key)"
    assert not descriptors["edge_tts"].offline
    assert descriptors["espeak"].available
    assert "Model" in json.dumps(descriptors["groq"].options_schema["properties"])
    llm_chain = chain_config(Capability.LLM, ProviderChoice(provider_id="groq"))
    assert provider_config_errors([llm_chain], list(descriptors.values())) == {}


def test_descriptors_declare_required_secrets_per_provider(tmp_path: Path) -> None:
    secrets = {
        item.provider_id: item.required_secrets for item in local_catalog(tmp_path).descriptors()
    }
    expected = {spec.provider_id: SECRET_PROVIDERS.get(spec.provider_id, ()) for spec in ALL_SPECS}
    assert secrets == expected
    declared = {secret.name for secret in local_catalog(tmp_path).secrets()}
    assert {name for names in secrets.values() for name in names} <= declared


def test_secrets_are_declared(tmp_path: Path) -> None:
    names = [secret.name for secret in local_catalog(tmp_path).secrets()]
    assert names == ["groq_api_key", "gemini_api_key", "huggingface_token"]


def test_build_provider_catalog_wires_real_context(tmp_path: Path) -> None:
    built = build_provider_catalog(InMemorySecrets(), tmp_path)
    assert {item.provider_id for item in built.descriptors() if item.available} >= {
        "offline_text",
        "offline_image",
        "offline_speech",
        "synth_music",
    }
