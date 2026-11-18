from __future__ import annotations

from dataclasses import dataclass

from automator.domain.credentials import Credential, CredentialInput, credential_secret_name
from automator.domain.ports import Clock, CredentialRepository, IdGenerator, SecretStore


@dataclass(frozen=True)
class CreateCredential:
    credentials: CredentialRepository
    secrets: SecretStore
    ids: IdGenerator
    clock: Clock

    def execute(self, data: CredentialInput) -> Credential:
        credential = Credential(
            id=self.ids.new(),
            name=data.name,
            client_id=data.client_id,
            daily_quota_units=data.daily_quota_units,
            created_at=self.clock.now(),
        )
        self.secrets.set(credential_secret_name(credential.id), data.client_secret)
        self.credentials.save(credential)
        return credential
