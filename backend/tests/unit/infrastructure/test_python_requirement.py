from __future__ import annotations

import pytest

from autotube.infrastructure.runtime.python_requirement import minimum_python, required_python


@pytest.mark.parametrize(
    ("spec", "expected"),
    [(">=3.12", (3, 12)), (">= 3.11, <4", (3, 11)), ("<3.13", None), ("", None)],
)
def test_minimum_python_reads_the_lower_bound(spec: str, expected: tuple[int, int] | None) -> None:
    assert minimum_python(spec) == expected


def test_required_python_comes_from_the_installed_package() -> None:
    assert required_python() == (3, 12)


def test_required_python_of_a_missing_package_is_unknown() -> None:
    assert required_python("no-such-package-autotube") is None
