from __future__ import annotations

from automator.domain.storage import DiskSpace, FileUsage, storage_report
from tests.unit.infrastructure.records import run

DISK = DiskSpace(data_dir="/d", data_dir_bytes=1000, free_bytes=5000, disk_bytes=9000)


def test_usage_is_summed_per_automation_largest_first() -> None:
    small = run("a", automation_id="auto-small", automation_name="Small")
    big_one = run("b", automation_id="auto-big", automation_name="Big")
    big_two = run("c", automation_id="auto-big", automation_name="Big")
    usages = [
        (small, FileUsage(final_bytes=10, intermediate_bytes=5)),
        (big_one, FileUsage(final_bytes=100, intermediate_bytes=50)),
        (big_two, FileUsage(final_bytes=1, intermediate_bytes=2)),
    ]
    report = storage_report(DISK, usages, orphan_bytes=40)
    assert [
        (u.automation_id, u.runs, u.final_bytes, u.intermediate_bytes) for u in report.automations
    ] == [("auto-big", 2, 101, 52), ("auto-small", 1, 10, 5)]
    assert (report.final_bytes, report.intermediate_bytes, report.orphan_bytes) == (111, 57, 40)
    assert report.other_bytes == 1000 - 111 - 57 - 40
    assert (report.free_bytes, report.disk_bytes, report.data_dir) == (5000, 9000, "/d")


def test_an_empty_data_folder_reports_zeroes() -> None:
    report = storage_report(DiskSpace(data_dir="/d"), [], orphan_bytes=0)
    assert report.automations == () and report.other_bytes == 0
    assert report.free_bytes is None


def test_file_usage_totals_both_kinds() -> None:
    assert FileUsage(final_bytes=3, intermediate_bytes=4).total_bytes == 7
