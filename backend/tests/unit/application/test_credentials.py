from __future__ import annotations

import pytest

from automator.application.create_credential import CreateCredential
from automator.application.list_credentials import ListCredentials
from automator.application.update_credential import UpdateCredential
from automator.domain.channels import Channel
from automator.domain.credentials import (
    Credential,
    CredentialInput,
    CredentialPatch,
    credential_secret_name,
)
from automator.shared.errors import NotFound, RuleConflict
from tests.fixtures.harness import Harness
from tests.fixtures.use_cases import delete_credential

VIEW = {"has_secret", "quota_used_today"}


def update_credential(harness: Harness) -> UpdateCredential:
    return UpdateCredential(harness.credentials, harness.secrets, harness.credential_views)


def test_create_stores_secret_separately(harness: Harness) -> None:
    created = CreateCredential(
        harness.credentials, harness.secrets, harness.ids, harness.clock, harness.credential_views
    ).execute(
        CredentialInput(name="Main", client_id="cid", client_secret="shh", daily_quota_units=500)
    )
    assert harness.credentials.get(created.id) == Credential(**created.model_dump(exclude=VIEW))
    assert created.has_secret and created.quota_used_today == 0
    assert created.daily_quota_units == 500 and created.created_at == harness.clock.now()
    assert harness.secrets.get(credential_secret_name(created.id)) == "shh"
    assert "shh" not in created.model_dump_json()


@pytest.mark.parametrize(
    ("patch", "name", "secret"),
    [
        (CredentialPatch(name="Renamed"), "Renamed", "s3cret"),
        (CredentialPatch(client_secret="new"), "Project cred-1", "new"),
        (CredentialPatch(), "Project cred-1", "s3cret"),
    ],
)
def test_update_changes_only_given_fields(
    harness: Harness, credential: Credential, patch: CredentialPatch, name: str, secret: str
) -> None:
    updated = update_credential(harness).execute(credential.id, patch)
    assert updated.name == name and updated.client_id == credential.client_id
    assert updated.has_secret and updated.quota_used_today == 0
    assert harness.secrets.get(credential_secret_name(credential.id)) == secret


def test_update_unknown_credential(harness: Harness) -> None:
    with pytest.raises(NotFound):
        update_credential(harness).execute("nope", CredentialPatch())


def test_delete_removes_credential_and_secret(harness: Harness, credential: Credential) -> None:
    delete_credential(harness).execute(credential.id)
    assert harness.credentials.get(credential.id) is None
    assert not harness.secrets.has(credential_secret_name(credential.id))


def test_delete_refused_while_channel_uses_it(harness: Harness, channel: Channel) -> None:
    with pytest.raises(RuleConflict):
        delete_credential(harness).execute(channel.credential_id)
    assert harness.credentials.get(channel.credential_id) is not None


def test_delete_unknown_credential(harness: Harness) -> None:
    with pytest.raises(NotFound):
        delete_credential(harness).execute("nope")


def test_list_reports_secret_presence_and_quota(harness: Harness, credential: Credential) -> None:
    other = credential.model_copy(update={"id": "cred-2"})
    harness.credentials.save(other)
    harness.ledger.record(credential.id, 1650, harness.quota_report.today())
    views = ListCredentials(harness.credentials, harness.credential_views).execute()
    assert [(v.id, v.has_secret, v.quota_used_today) for v in views] == [
        ("cred-1", True, 1650),
        ("cred-2", False, 0),
    ]
