from __future__ import annotations

from pydantic import Field

from automator.domain.model_base import DomainModel


class SecretDefinition(DomainModel):
    name: str = Field(min_length=1)
    title: str
    description: str = ""


class SecretStatus(SecretDefinition):
    is_set: bool
