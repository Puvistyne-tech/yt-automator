from __future__ import annotations

import pytest

from autotube.application.delete_secret import DeleteSecret
from autotube.application.get_pipeline import GetPipeline
from autotube.application.get_providers import GetProviders
from autotube.application.get_settings import GetSettings
from autotube.application.list_pipelines import ListPipelines
from autotube.application.list_secrets import ListSecrets
from autotube.application.save_provider_config import SaveProviderConfig
from autotube.application.save_settings import SaveSettings
from autotube.application.set_secret import SetSecret
from autotube.domain.capabilities import Capability
from autotube.domain.providers import ProviderChoice, ProviderConfig
from autotube.shared.errors import NotFound, ValidationFailed
from tests.fixtures.harness import Harness

LLM_CHAIN = ProviderConfig(
    capability=Capability.LLM,
    chain=(
        ProviderChoice(provider_id="cloud-llm", enabled=False, options={"model": "x"}),
        ProviderChoice(provider_id="fake-llm"),
    ),
)


def test_get_providers_returns_descriptors_and_config(harness: Harness) -> None:
    harness.provider_configs.save_all([LLM_CHAIN])
    view = GetProviders(harness.catalog, harness.provider_configs).execute()
    assert [d.provider_id for d in view.descriptors] == ["fake-llm", "cloud-llm", "fake-image"]
    assert view.config == (LLM_CHAIN,)


def test_save_provider_config_validates_then_persists(harness: Harness) -> None:
    save = SaveProviderConfig(harness.catalog, harness.provider_configs)
    assert save.execute([LLM_CHAIN]) == [LLM_CHAIN]
    bad = ProviderConfig(
        capability=Capability.IMAGE, chain=(ProviderChoice(provider_id="fake-llm"),)
    )
    with pytest.raises(ValidationFailed) as raised:
        save.execute([LLM_CHAIN, bad])
    assert set(raised.value.fields) == {"1.chain.0.provider_id"}
    assert harness.provider_configs.list() == [LLM_CHAIN]


def test_save_provider_config_rejects_invalid_options(harness: Harness) -> None:
    save = SaveProviderConfig(harness.catalog, harness.provider_configs)
    blank = ProviderConfig(
        capability=Capability.LLM,
        chain=(
            ProviderChoice(provider_id="fake-llm"),
            ProviderChoice(provider_id="cloud-llm", options={"model": ""}),
        ),
    )
    with pytest.raises(ValidationFailed) as raised:
        save.execute([blank])
    assert raised.value.fields == {"0.chain.1.options.model": "model must not be empty"}
    assert harness.provider_configs.list() == []


def test_save_provider_config_reports_descriptor_and_option_errors_together(
    harness: Harness,
) -> None:
    mixed = ProviderConfig(
        capability=Capability.LLM,
        chain=(
            ProviderChoice(provider_id="unknown"),
            ProviderChoice(provider_id="cloud-llm", options={"model": ""}),
        ),
    )
    with pytest.raises(ValidationFailed) as raised:
        SaveProviderConfig(harness.catalog, harness.provider_configs).execute([mixed])
    assert set(raised.value.fields) == {"0.chain.0.provider_id", "0.chain.1.options.model"}


def test_secrets_list_set_and_delete(harness: Harness) -> None:
    listing = ListSecrets(harness.catalog, harness.secrets)
    assert [(s.name, s.is_set) for s in listing.execute()] == [("cloud_api_key", False)]
    SetSecret(harness.catalog, harness.secrets).execute("cloud_api_key", "abc")
    assert harness.secrets.get("cloud_api_key") == "abc"
    assert listing.execute()[0].is_set is True
    assert "abc" not in listing.execute()[0].model_dump_json()
    DeleteSecret(harness.catalog, harness.secrets).execute("cloud_api_key")
    assert listing.execute()[0].is_set is False


@pytest.mark.parametrize("value", ["", "   "])
def test_set_secret_rejects_blank_values(harness: Harness, value: str) -> None:
    with pytest.raises(ValidationFailed):
        SetSecret(harness.catalog, harness.secrets).execute("cloud_api_key", value)


@pytest.mark.parametrize("action", ["set", "delete"])
def test_unknown_secret_names_are_not_found(harness: Harness, action: str) -> None:
    with pytest.raises(NotFound):
        if action == "set":
            SetSecret(harness.catalog, harness.secrets).execute("credential/x/client_secret", "v")
        else:
            DeleteSecret(harness.catalog, harness.secrets).execute("channel/x/token")


def test_settings_round_trip_keeps_data_dir(harness: Harness) -> None:
    saved = SaveSettings(harness.app_settings).execute(
        {"timezone": "Asia/Kolkata", "max_parallel_runs": 2, "keep_runs_days": 7}
    )
    assert GetSettings(harness.app_settings).execute() == saved
    assert saved.data_dir == "/tmp/autotube" and saved.timezone == "Asia/Kolkata"


def test_settings_reject_unknown_timezone(harness: Harness) -> None:
    with pytest.raises(ValidationFailed) as raised:
        SaveSettings(harness.app_settings).execute({"timezone": "Moon/Base"})
    assert set(raised.value.fields) == {"timezone"}


def test_pipelines_are_listed_and_fetched(harness: Harness) -> None:
    listed = ListPipelines(harness.pipelines).execute()
    assert [d.type_id for d in listed] == ["fake", "fake_kids"]
    assert listed[0].settings_schema["type"] == "object"
    assert listed[0].default_settings["topic"] == "cats"
    assert GetPipeline(harness.pipelines).execute("fake_kids").makes_kids_content
    with pytest.raises(NotFound):
        GetPipeline(harness.pipelines).execute("nope")
