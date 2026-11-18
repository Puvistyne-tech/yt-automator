from __future__ import annotations

from dataclasses import dataclass

from automator.application.credential_views import CredentialViews
from automator.domain.credentials import CredentialView
from automator.domain.ports import CredentialRepository


@dataclass(frozen=True)
class ListCredentials:
    credentials: CredentialRepository
    views: CredentialViews

    def execute(self) -> list[CredentialView]:
        return [self.views.of(credential) for credential in self.credentials.list()]
