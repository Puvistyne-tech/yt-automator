from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from automator.domain.capabilities import Capability
from automator.domain.model_base import DomainModel
from automator.domain.secrets import SecretDefinition


class CheckStatus(StrEnum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


class HealthCheck(DomainModel):
    name: str
    status: CheckStatus
    detail: str = ""


class ProviderHealth(DomainModel):
    provider_id: str
    capability: Capability
    name: str
    available: bool
    reason: str = ""


class SystemFacts(DomainModel):
    python_version: str
    data_dir: str
    data_dir_writable: bool
    free_bytes: int | None = None
    ffmpeg_version: str = ""
    ffprobe_version: str = ""
    database_path: str
    database_revision: str | None = None
    database_head: str | None = None
    database_revision_known: bool = True
    database_error: str = ""
    web_dist_dir: str
    ui_built: bool


class DoctorPolicy(DomainModel):
    min_python: tuple[int, int] = (3, 12)
    min_free_gb: float = Field(default=10.0, ge=0)


class DoctorReport(DomainModel):
    can_start: bool
    checks: tuple[HealthCheck, ...]
    capabilities: tuple[HealthCheck, ...]
    providers: tuple[ProviderHealth, ...]
    missing_secrets: tuple[SecretDefinition, ...]
