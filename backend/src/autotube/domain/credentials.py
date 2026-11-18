from __future__ import annotations

from pydantic import AwareDatetime, Field

from autotube.domain.model_base import DomainModel

DEFAULT_DAILY_QUOTA_UNITS = 10000


class Credential(DomainModel):
    id: str
    name: str = Field(min_length=1)
    client_id: str = Field(min_length=1)
    daily_quota_units: int = Field(default=DEFAULT_DAILY_QUOTA_UNITS, ge=0)
    created_at: AwareDatetime


class CredentialInput(DomainModel):
    name: str = Field(min_length=1)
    client_id: str = Field(min_length=1)
    client_secret: str = Field(min_length=1, repr=False)
    daily_quota_units: int = Field(default=DEFAULT_DAILY_QUOTA_UNITS, ge=0)


class CredentialPatch(DomainModel):
    name: str | None = Field(default=None, min_length=1)
    client_id: str | None = Field(default=None, min_length=1)
    client_secret: str | None = Field(default=None, min_length=1, repr=False)
    daily_quota_units: int | None = Field(default=None, ge=0)


class CredentialView(Credential):
    has_secret: bool
    quota_used_today: int


def credential_secret_name(credential_id: str) -> str:
    return f"credential/{credential_id}/client_secret"
