from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.setup_script import folder_name, logged, mlx_host, mlx_run, planned

KLEIN = "black-forest-labs/FLUX.2-klein-4B"

pytestmark = pytest.mark.integration


def klein_folder(data: Path) -> Path:
    return data / "models" / folder_name(KLEIN)


def test_images_plan_installs_mflux_and_downloads_flux_klein(tmp_path: Path) -> None:
    plan = planned(tmp_path, "--images", "--no-base")
    data = tmp_path / "home" / "data"
    assert "uv tool install --python 3.12 mflux" in plan
    assert f"download {KLEIN} --local-dir {klein_folder(data)}" in plan
    assert "FLUX.2 klein 4B weights are roughly 16 GB" in plan
    assert "hf auth login" in plan


def test_images_links_flux_klein_from_the_models_folder(tmp_path: Path) -> None:
    data = mlx_host(tmp_path, ready=True)
    source = tmp_path / "bakeoff" / "local" / folder_name(KLEIN)
    source.mkdir(parents=True)
    extra = {"AUTOTUBE_MODELS_FROM": str(tmp_path / "bakeoff")}
    result = mlx_run(tmp_path, "--images", extra=extra)
    assert result.returncode == 0, result.stderr
    assert klein_folder(data).readlink() == source
    assert "--local-dir" not in logged(tmp_path)


def test_images_downloads_flux_klein_once(tmp_path: Path) -> None:
    data = mlx_host(tmp_path, ready=True)
    assert mlx_run(tmp_path, "--images").returncode == 0
    assert f"hf download {KLEIN} --local-dir {klein_folder(data)}" in logged(tmp_path)
    rerun = mlx_run(tmp_path, "--images")
    assert f"model {KLEIN} is already present" in rerun.stdout
    assert logged(tmp_path).count(f"download {KLEIN}") == 1
