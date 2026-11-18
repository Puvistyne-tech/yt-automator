from __future__ import annotations

from datetime import datetime

from automator.shared.clock import utc_now
from automator.shared.ids import random_id


class SystemClock:
    def now(self) -> datetime:
        return utc_now()


class RandomIds:
    def new(self) -> str:
        return random_id()
