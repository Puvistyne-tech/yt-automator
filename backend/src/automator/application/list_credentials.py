from __future__ import annotations

from dataclasses import dataclass

from automator.application.quota_report import QuotaReport
from automator.domain.credentials import CredentialView, credential_secret_name
from automator.domain.ports import CredentialRepository, SecretStore


@dataclass(frozen=True)
class ListCredentials:
    credentials: CredentialRepository
    secrets: SecretStore
    quota: QuotaReport

    def execute(self) -> list[CredentialView]:
        return [
            CredentialView(
                **credential.model_dump(),
                has_secret=self.secrets.has(credential_secret_name(credential.id)),
                quota_used_today=self.quota.usage(credential).used,
            )
            for credential in self.credentials.list()
        ]
