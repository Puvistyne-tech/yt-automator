from __future__ import annotations

from dataclasses import dataclass

from autotube.application.quota_report import QuotaReport
from autotube.domain.credentials import Credential, CredentialView, credential_secret_name
from autotube.domain.ports import SecretStore


@dataclass(frozen=True)
class CredentialViews:
    secrets: SecretStore
    quota: QuotaReport

    def of(self, credential: Credential) -> CredentialView:
        return CredentialView(
            **credential.model_dump(),
            has_secret=self.secrets.has(credential_secret_name(credential.id)),
            quota_used_today=self.quota.usage(credential).used,
        )
