from __future__ import annotations

from dataclasses import dataclass

from automator.application.lookups import require_credential
from automator.domain.credentials import Credential, CredentialPatch, credential_secret_name
from automator.domain.ports import CredentialRepository, SecretStore


@dataclass(frozen=True)
class UpdateCredential:
    credentials: CredentialRepository
    secrets: SecretStore

    def execute(self, credential_id: str, patch: CredentialPatch) -> Credential:
        current = require_credential(self.credentials, credential_id)
        changes = patch.model_dump(exclude_none=True, exclude={"client_secret"})
        updated = current.model_copy(update=changes)
        if patch.client_secret is not None:
            self.secrets.set(credential_secret_name(credential_id), patch.client_secret)
        self.credentials.save(updated)
        return updated
