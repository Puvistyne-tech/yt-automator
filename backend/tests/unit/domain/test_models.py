from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import BaseModel, ValidationError

from autotube.domain.capabilities import Capability
from autotube.domain.channels import channel_token_secret_name
from autotube.domain.connect_state import (
    ConnectState,
    ConnectStatePolicy,
    issue_state,
    read_state,
    verify_state,
)
from autotube.domain.credentials import Credential, credential_secret_name
from autotube.domain.providers import (
    ProviderChoice,
    ProviderConfig,
    provider_config_errors,
)
from autotube.domain.run_parts import Upload
from autotube.domain.settings import AppSettings, AppSettingsInput, app_settings_errors
from autotube.domain.validation import ROOT_FIELD, field_errors, validated_settings
from autotube.shared.errors import ValidationFailed
from tests.fixtures.fake_providers import DESCRIPTORS

NOW = datetime(2026, 1, 5, 10, tzinfo=UTC)


def test_secret_names_follow_the_spec() -> None:
    assert credential_secret_name("c1") == "credential/c1/client_secret"
    assert channel_token_secret_name("ch") == "channel/ch/token"


def test_models_are_frozen_and_reject_unknown_fields() -> None:
    credential = Credential(id="c", name="n", client_id="i", created_at=NOW)
    assert credential.daily_quota_units == 10000
    with pytest.raises(ValidationError):
        Credential.model_validate({**credential.model_dump(), "extra": 1})
    with pytest.raises(ValidationError):
        Credential(id="c", name="n", client_id="i", created_at=datetime(2026, 1, 1))


def choice(provider_id: str) -> ProviderChoice:
    return ProviderChoice(provider_id=provider_id)


@pytest.mark.parametrize(
    ("configs", "errors"),
    [
        (
            [
                ProviderConfig(
                    capability=Capability.LLM, chain=(choice("fake-llm"), choice("cloud-llm"))
                )
            ],
            set(),
        ),
        (
            [ProviderConfig(capability=Capability.LLM, chain=(choice("nope"),))],
            {"0.chain.0.provider_id"},
        ),
        (
            [ProviderConfig(capability=Capability.LLM, chain=(choice("fake-image"),))],
            {"0.chain.0.provider_id"},
        ),
        (
            [
                ProviderConfig(
                    capability=Capability.LLM, chain=(choice("fake-llm"), choice("fake-llm"))
                )
            ],
            {"0.chain.1.provider_id"},
        ),
        (
            [ProviderConfig(capability=Capability.LLM), ProviderConfig(capability=Capability.LLM)],
            {"1.capability"},
        ),
    ],
)
def test_provider_config_errors(configs: list[ProviderConfig], errors: set[str]) -> None:
    assert set(provider_config_errors(configs, DESCRIPTORS)) == errors


@pytest.mark.parametrize(
    ("zone", "valid"), [("UTC", True), ("Europe/Paris", True), ("Nope", False)]
)
def test_app_settings_timezone(zone: str, valid: bool) -> None:
    assert (app_settings_errors(AppSettingsInput(timezone=zone)) == {}) is valid


def test_app_settings_keep_data_dir_when_changed() -> None:
    current = AppSettings(data_dir="/data")
    updated = current.with_input(AppSettingsInput(max_parallel_runs=3))
    assert (updated.data_dir, updated.max_parallel_runs) == ("/data", 3)


class Nested(BaseModel):
    count: int


class Outer(BaseModel):
    inner: Nested


def test_field_errors_build_dotted_paths() -> None:
    model, errors = validated_settings(Outer, {"inner": {"count": "x"}})
    assert model is None and list(errors) == ["settings.inner.count"]
    valid, none = validated_settings(Outer, {"inner": {"count": 1}})
    assert isinstance(valid, Outer) and none == {}
    with pytest.raises(ValidationError) as raised:
        Nested.model_validate("not a dict")
    assert list(field_errors(raised.value)) == [ROOT_FIELD]


POLICY = ConnectStatePolicy()
STATE = ConnectState(credential_id="c1", nonce="n1", issued_at=NOW)


def test_connect_state_round_trip() -> None:
    token = issue_state(STATE, "secret")
    assert read_state(token) == STATE
    verify_state(token, STATE, "secret", NOW + timedelta(minutes=15), POLICY)


@pytest.mark.parametrize(
    ("key", "now", "reason"),
    [
        ("wrong", NOW, "signature mismatch"),
        ("secret", NOW + timedelta(minutes=16), "expired"),
        ("secret", NOW - timedelta(minutes=1), "expired"),
    ],
)
def test_connect_state_rejections(key: str, now: datetime, reason: str) -> None:
    token = issue_state(STATE, "secret")
    with pytest.raises(ValidationFailed) as raised:
        verify_state(token, STATE, key, now, POLICY)
    assert raised.value.fields == {"state": reason}


def test_an_upload_stored_before_audience_fields_loads_them_as_null() -> None:
    legacy = {"target_id": "t", "channel_id": "c", "language": "en", "variant": "v"}

    upload = Upload.model_validate(legacy)

    assert (upload.privacy, upload.made_for_kids) == (None, None)
    assert upload.model_dump(mode="json")["privacy"] is None


@pytest.mark.parametrize("token", ["garbage", "e30.sig", "eyJhIjoiYiJ9.sig"])
def test_malformed_connect_state(token: str) -> None:
    with pytest.raises(ValidationFailed):
        read_state(token)
