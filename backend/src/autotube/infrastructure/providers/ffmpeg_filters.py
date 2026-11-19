from __future__ import annotations

from autotube.infrastructure.providers.process import ProcessRunner, SubprocessRunner
from autotube.shared.errors import UpstreamFailure

FILTER_LISTING_ARGS = ("-hide_banner", "-filters")
NAME_COLUMN = 1
MIN_ROW_COLUMNS = 3


def listed_filters(listing: str) -> frozenset[str]:
    rows = (line.split() for line in listing.splitlines())
    return frozenset(row[NAME_COLUMN] for row in rows if len(row) >= MIN_ROW_COLUMNS)


def ffmpeg_filter_names(
    binary: str, timeout_seconds: float, runner: ProcessRunner | None = None
) -> frozenset[str]:
    command = [binary, *FILTER_LISTING_ARGS]
    try:
        listing = (runner or SubprocessRunner()).run(command, timeout_seconds).stdout
    except UpstreamFailure:
        return frozenset()
    return listed_filters(listing)
