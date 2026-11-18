from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from automator.domain.credentials import Credential
from automator.domain.ports import Clock, QuotaLedger
from automator.domain.quota import QuotaPolicy, QuotaUsage


@dataclass(frozen=True)
class QuotaReport:
    ledger: QuotaLedger
    clock: Clock
    policy: QuotaPolicy = field(default_factory=QuotaPolicy)

    def today(self) -> date:
        return self.policy.quota_day(self.clock.now())

    def usage(self, credential: Credential) -> QuotaUsage:
        return QuotaUsage(
            credential_id=credential.id,
            name=credential.name,
            used=self.ledger.used_today(credential.id, self.today()),
            limit=credential.daily_quota_units,
        )

    def charge(self, credential_id: str, units: int) -> None:
        self.ledger.record(credential_id, units, self.today())
