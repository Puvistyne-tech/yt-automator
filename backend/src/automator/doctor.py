from __future__ import annotations

import os
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import TextIO

from automator.domain.diagnostics import DoctorReport, HealthCheck, ProviderHealth
from automator.main import build_doctor, setup_defaults

PRINT_DEFAULTS = "--print-defaults"
CAN_START = "The app can start."
CANNOT_START = "The app cannot start: fix the errors above."


def table(rows: Iterable[Sequence[str]]) -> list[str]:
    materialised = [list(row) for row in rows]
    if not materialised:
        return []
    widths = [max(len(row[index]) for row in materialised) for index in range(len(materialised[0]))]
    return [
        "  "
        + "  ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True)).rstrip()
        for row in materialised
    ]


def check_rows(checks: Iterable[HealthCheck]) -> list[list[str]]:
    return [[check.status.value.upper(), check.name, check.detail] for check in checks]


def provider_rows(providers: Iterable[ProviderHealth]) -> list[list[str]]:
    return [
        [
            health.capability.value,
            health.provider_id,
            "available" if health.available else "unavailable",
            health.reason,
        ]
        for health in providers
    ]


def secrets_line(report: DoctorReport) -> str:
    missing = ", ".join(f"{secret.name} ({secret.title})" for secret in report.missing_secrets)
    return f"Missing secrets: {missing or 'none'}"


def render(report: DoctorReport) -> str:
    lines = [
        "System",
        *table(check_rows(report.checks)),
        "",
        "Capabilities",
        *table(check_rows(report.capabilities)),
        "",
        "Providers",
        *table(provider_rows(report.providers)),
        "",
        secrets_line(report),
        "",
        CAN_START if report.can_start else CANNOT_START,
    ]
    return "\n".join(lines) + "\n"


def exit_code(report: DoctorReport) -> int:
    return 0 if report.can_start else 1


def defaults_text(values: Mapping[str, str]) -> str:
    return "".join(f"{key}={value}\n" for key, value in values.items())


def main(
    argv: Sequence[str] = (), environ: Mapping[str, str] = os.environ, out: TextIO = sys.stdout
) -> int:
    try:
        if PRINT_DEFAULTS in argv:
            out.write(defaults_text(setup_defaults(environ)))
            return 0
        doctor = build_doctor(environ)
    except (ValueError, OSError) as failure:
        out.write(f"Cannot run the doctor: {failure}\n{CANNOT_START}\n")
        return 1
    report = doctor.execute()
    out.write(render(report))
    return exit_code(report)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
