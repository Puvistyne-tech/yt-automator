from __future__ import annotations

from datetime import datetime
from importlib.metadata import PackageNotFoundError, version

from automator.shared.clock import utc_now
from automator.shared.ids import random_id


class SystemClock:
    def now(self) -> datetime:
        return utc_now()


class RandomIds:
    def new(self) -> str:
        return random_id()


def package_version() -> str:
    try:
        return version("automator")
    except PackageNotFoundError:
        return "0.0.0"
