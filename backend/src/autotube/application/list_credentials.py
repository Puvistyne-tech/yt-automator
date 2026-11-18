from __future__ import annotations

from dataclasses import dataclass

from autotube.application.credential_views import CredentialViews
from autotube.domain.credentials import CredentialView
from autotube.domain.ports import CredentialRepository


@dataclass(frozen=True)
class ListCredentials:
    credentials: CredentialRepository
    views: CredentialViews

    def execute(self) -> list[CredentialView]:
        return [self.views.of(credential) for credential in self.credentials.list()]
