from __future__ import annotations

from dataclasses import dataclass, field

from automator.domain.credentials import Credential
from automator.domain.ports import Clock, QuotaLedger
from automator.domain.quota import QuotaPolicy, QuotaUsage


@dataclass(frozen=True)
class QuotaReport:
    ledger: QuotaLedger
    clock: Clock
    quota: QuotaPolicy = field(default_factory=QuotaPolicy)

    def usage(self, credential: Credential) -> QuotaUsage:
        day = self.quota.quota_day(self.clock.now())
        return QuotaUsage(
            credential_id=credential.id,
            name=credential.name,
            used=self.ledger.used_today(credential.id, day),
            limit=credential.daily_quota_units,
        )
