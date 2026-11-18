from __future__ import annotations

import io
from pathlib import Path

import pytest

from automator import doctor as doctor_module
from automator.doctor import CANNOT_START, exit_code, main, render
from automator.domain.capabilities import Capability
from automator.domain.diagnostics import CheckStatus, DoctorReport, HealthCheck, ProviderHealth
from automator.domain.secrets import SecretDefinition
from tests.fixtures.fake_diagnostics import UnreadableSecrets, run_doctor, system_facts
from tests.fixtures.fake_runtime import InMemorySecrets

REPORT = DoctorReport(
    can_start=True,
    checks=(HealthCheck(name="python", status=CheckStatus.OK, detail="Python 3.12.4"),),
    capabilities=(
        HealthCheck(name="music", status=CheckStatus.WARNING, detail="no provider is registered"),
    ),
    providers=(
        ProviderHealth(provider_id="fake-llm", capability=Capability.LLM, name="F", available=True),
        ProviderHealth(
            provider_id="cloud-llm",
            capability=Capability.LLM,
            name="C",
            available=False,
            reason="set the key",
        ),
    ),
    missing_secrets=(SecretDefinition(name="cloud_api_key", title="Cloud API key"),),
)


def test_exit_code_is_zero_when_the_app_can_start() -> None:
    assert exit_code(run_doctor().execute()) == 0


def test_exit_code_is_one_when_the_app_cannot_start() -> None:
    assert exit_code(run_doctor(system_facts(data_dir_writable=False)).execute()) == 1


def test_render_prints_every_section_in_order() -> None:
    assert render(REPORT).splitlines() == [
        "System",
        "  OK  python  Python 3.12.4",
        "",
        "Capabilities",
        "  WARNING  music  no provider is registered",
        "",
        "Providers",
        "  llm  fake-llm   available",
        "  llm  cloud-llm  unavailable  set the key",
        "",
        "Missing secrets: cloud_api_key (Cloud API key)",
        "",
        "The app can start.",
    ]


def test_render_says_when_the_app_cannot_start() -> None:
    text = render(run_doctor(system_facts(data_dir_writable=False)).execute())
    assert "  ERROR  data_dir" in text
    assert text.rstrip().endswith("The app cannot start: fix the errors above.")


def test_render_never_shows_secret_values() -> None:
    secrets = InMemorySecrets()
    secrets.set("cloud_api_key", "s3cret-value")
    text = render(run_doctor(secrets=secrets).execute())
    assert "Missing secrets: none" in text
    assert "s3cret-value" not in text


def test_render_without_providers_keeps_the_heading() -> None:
    text = render(run_doctor(secrets=UnreadableSecrets()).execute())
    assert "Providers\n\nMissing secrets: none" in text


def environment(data_dir: Path, **extra: str) -> dict[str, str]:
    return {
        "AUTOMATOR_DATA_DIR": str(data_dir),
        "AUTOMATOR_WEB_DIST_DIR": str(data_dir.parent / "dist"),
        "AUTOMATOR_SECRET_BACKEND": "file",
        **extra,
    }


def test_main_prints_the_report_without_writing_anything(tmp_path: Path) -> None:
    out = io.StringIO()
    assert main((), environment(tmp_path / "data"), out) == 0
    assert "groq_api_key" in out.getvalue()
    assert not (tmp_path / "data").exists()


def test_main_exits_one_when_the_data_dir_is_unusable(tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    out = io.StringIO()
    assert main((), environment(blocker / "data"), out) == 1
    assert "cannot create or write" in out.getvalue()


def test_main_exits_one_on_an_invalid_setting(tmp_path: Path) -> None:
    out = io.StringIO()
    assert main((), environment(tmp_path, AUTOMATOR_PORT="abc"), out) == 1
    assert out.getvalue().startswith("Cannot run the doctor:")
    assert out.getvalue().rstrip().endswith(CANNOT_START)


def test_main_exits_one_when_the_system_refuses_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(_: object) -> None:
        raise PermissionError("keychain access denied")

    monkeypatch.setattr(doctor_module, "build_doctor", refuse)
    out = io.StringIO()
    assert main((), environment(tmp_path), out) == 1
    assert "keychain access denied" in out.getvalue()
    assert out.getvalue().rstrip().endswith(CANNOT_START)


def test_main_prints_the_setup_defaults(tmp_path: Path) -> None:
    out = io.StringIO()
    env = environment(tmp_path / "data", AUTOMATOR_PORT="9000")
    assert main(["--print-defaults"], env, out) == 0
    lines = out.getvalue().splitlines()
    assert f"MUSIC_DIR={tmp_path / 'data' / 'assets' / 'music'}" in lines
    assert "APP_PORT=9000" in lines
    assert "REDIRECT_BASE_URL=http://127.0.0.1:9000" in lines
