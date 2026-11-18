from __future__ import annotations

from collections.abc import Sequence

from pydantic import Field

from automator.domain.model_base import DomainModel
from automator.domain.runs import Run


class FileUsage(DomainModel):
    final_bytes: int = Field(default=0, ge=0)
    intermediate_bytes: int = Field(default=0, ge=0)

    @property
    def total_bytes(self) -> int:
        return self.final_bytes + self.intermediate_bytes


class DiskSpace(DomainModel):
    data_dir: str
    data_dir_bytes: int = Field(default=0, ge=0)
    free_bytes: int | None = None
    disk_bytes: int | None = None


class AutomationUsage(DomainModel):
    automation_id: str
    automation_name: str
    runs: int
    final_bytes: int
    intermediate_bytes: int


class StorageReport(DomainModel):
    data_dir: str
    data_dir_bytes: int
    free_bytes: int | None
    disk_bytes: int | None
    final_bytes: int
    intermediate_bytes: int
    orphan_bytes: int
    other_bytes: int
    automations: tuple[AutomationUsage, ...]


RunUsage = tuple[Run, FileUsage]


def automation_usage(automation_id: str, usages: Sequence[RunUsage]) -> AutomationUsage:
    return AutomationUsage(
        automation_id=automation_id,
        automation_name=usages[0][0].automation_name,
        runs=len(usages),
        final_bytes=sum(usage.final_bytes for _, usage in usages),
        intermediate_bytes=sum(usage.intermediate_bytes for _, usage in usages),
    )


def usage_by_automation(usages: Sequence[RunUsage]) -> tuple[AutomationUsage, ...]:
    grouped: dict[str, list[RunUsage]] = {}
    for run, usage in usages:
        grouped.setdefault(run.automation_id, []).append((run, usage))
    totals = [automation_usage(key, group) for key, group in grouped.items()]
    return tuple(
        sorted(totals, key=lambda u: (-(u.final_bytes + u.intermediate_bytes), u.automation_name))
    )


def storage_report(disk: DiskSpace, usages: Sequence[RunUsage], orphan_bytes: int) -> StorageReport:
    final = sum(usage.final_bytes for _, usage in usages)
    intermediate = sum(usage.intermediate_bytes for _, usage in usages)
    return StorageReport(
        data_dir=disk.data_dir,
        data_dir_bytes=disk.data_dir_bytes,
        free_bytes=disk.free_bytes,
        disk_bytes=disk.disk_bytes,
        final_bytes=final,
        intermediate_bytes=intermediate,
        orphan_bytes=orphan_bytes,
        other_bytes=max(0, disk.data_dir_bytes - final - intermediate - orphan_bytes),
        automations=usage_by_automation(usages),
    )
