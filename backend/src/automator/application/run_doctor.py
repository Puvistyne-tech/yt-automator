from __future__ import annotations

from dataclasses import dataclass

from automator.domain.diagnostic_rules import (
    capability_checks,
    is_startable,
    provider_health,
    system_checks,
    warning,
)
from automator.domain.diagnostics import (
    DoctorPolicy,
    DoctorReport,
    HealthCheck,
    ProviderHealth,
)
from automator.domain.ports import ProviderCatalog, SecretStore, SystemInspector
from automator.domain.secrets import SecretDefinition
from automator.shared.errors import AppError


@dataclass(frozen=True)
class ProviderFindings:
    providers: tuple[ProviderHealth, ...] = ()
    missing_secrets: tuple[SecretDefinition, ...] = ()
    problems: tuple[HealthCheck, ...] = ()


@dataclass(frozen=True)
class RunDoctor:
    catalog: ProviderCatalog
    secrets: SecretStore
    inspector: SystemInspector
    policy: DoctorPolicy

    def provider_findings(self) -> ProviderFindings:
        try:
            providers = provider_health(self.catalog.descriptors())
            missing = [s for s in self.catalog.secrets() if not self.secrets.has(s.name)]
        except AppError as failure:
            return ProviderFindings(problems=(warning("secrets", failure.message),))
        return ProviderFindings(tuple(providers), tuple(missing))

    def execute(self) -> DoctorReport:
        findings = self.provider_findings()
        checks = [*system_checks(self.inspector.facts(), self.policy), *findings.problems]
        return DoctorReport(
            can_start=is_startable(checks),
            checks=tuple(checks),
            capabilities=tuple(capability_checks(findings.providers)),
            providers=findings.providers,
            missing_secrets=findings.missing_secrets,
        )
