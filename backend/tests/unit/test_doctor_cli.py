from __future__ import annotations

import io
from pathlib import Path

from automator.application.run_doctor import RunDoctor
from automator.doctor import exit_code, main, render
from automator.domain.diagnostics import DoctorPolicy
from tests.fixtures.fake_diagnostics import FakeInspector, UnreadableSecrets, system_facts
from tests.fixtures.fake_providers import FakeProviderCatalog
from tests.fixtures.fake_runtime import InMemorySecrets


def fake_doctor(writable: bool = True) -> RunDoctor:
    return RunDoctor(
        catalog=FakeProviderCatalog(),
        secrets=InMemorySecrets(),
        inspector=FakeInspector(system_facts(data_dir_writable=writable)),
        policy=DoctorPolicy(),
    )


def test_exit_code_is_zero_when_the_app_can_start() -> None:
    assert exit_code(fake_doctor().execute()) == 0


def test_exit_code_is_one_when_the_app_cannot_start() -> None:
    assert exit_code(fake_doctor(writable=False).execute()) == 1


def test_render_lists_checks_providers_and_secrets() -> None:
    text = render(fake_doctor().execute())
    assert "python" in text and "Python 3.12.4" in text
    assert "fake-image" in text and "available" in text
    assert "cloud_api_key" in text
    assert text.rstrip().endswith("The app can start.")


def test_render_says_when_the_app_cannot_start() -> None:
    text = render(fake_doctor(writable=False).execute())
    assert "ERROR" in text
    assert text.rstrip().endswith("The app cannot start: fix the errors above.")


def test_render_reports_when_no_secret_is_missing() -> None:
    secrets = InMemorySecrets()
    secrets.set("cloud_api_key", "value")
    doctor = RunDoctor(FakeProviderCatalog(), secrets, FakeInspector(), DoctorPolicy())
    assert "Missing secrets: none" in render(doctor.execute())


def test_render_without_providers_keeps_the_heading() -> None:
    doctor = RunDoctor(FakeProviderCatalog(), UnreadableSecrets(), FakeInspector(), DoctorPolicy())
    text = render(doctor.execute())
    assert "Providers\n\nMissing secrets: none" in text


def environment(data_dir: Path, web_dir: Path) -> dict[str, str]:
    return {
        "AUTOMATOR_DATA_DIR": str(data_dir),
        "AUTOMATOR_WEB_DIST_DIR": str(web_dir),
        "AUTOMATOR_SECRET_BACKEND": "file",
    }


def test_main_prints_the_report_and_exits_zero(tmp_path: Path) -> None:
    out = io.StringIO()
    assert main(environment(tmp_path / "data", tmp_path / "dist"), out) == 0
    assert "groq" in out.getvalue()
    assert "groq_api_key" in out.getvalue()


def test_main_exits_one_when_the_data_dir_is_unusable(tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    out = io.StringIO()
    assert main(environment(blocker / "data", tmp_path / "dist"), out) == 1
    assert "Cannot open the data directory" in out.getvalue()
