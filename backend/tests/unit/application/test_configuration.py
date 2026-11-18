from __future__ import annotations

import pytest

from automator.application.delete_secret import DeleteSecret
from automator.application.get_pipeline import GetPipeline
from automator.application.get_providers import GetProviders
from automator.application.get_settings import GetSettings
from automator.application.list_pipelines import ListPipelines
from automator.application.list_secrets import ListSecrets
from automator.application.save_provider_config import SaveProviderConfig
from automator.application.save_settings import SaveSettings
from automator.application.set_secret import SetSecret
from automator.domain.capabilities import Capability
from automator.domain.providers import ProviderChoice, ProviderConfig
from automator.domain.settings import AppSettingsInput
from automator.shared.errors import NotFound, ValidationFailed
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
        AppSettingsInput(timezone="Asia/Kolkata", max_parallel_runs=2, keep_runs_days=7)
    )
    assert GetSettings(harness.app_settings).execute() == saved
    assert saved.data_dir == "/tmp/automator" and saved.timezone == "Asia/Kolkata"


def test_settings_reject_unknown_timezone(harness: Harness) -> None:
    with pytest.raises(ValidationFailed) as raised:
        SaveSettings(harness.app_settings).execute(AppSettingsInput(timezone="Moon/Base"))
    assert set(raised.value.fields) == {"timezone"}


def test_pipelines_are_listed_and_fetched(harness: Harness) -> None:
    listed = ListPipelines(harness.pipelines).execute()
    assert [d.type_id for d in listed] == ["fake", "fake_kids"]
    assert listed[0].settings_schema["type"] == "object"
    assert listed[0].default_settings["topic"] == "cats"
    assert GetPipeline(harness.pipelines).execute("fake_kids").makes_kids_content
    with pytest.raises(NotFound):
        GetPipeline(harness.pipelines).execute("nope")
