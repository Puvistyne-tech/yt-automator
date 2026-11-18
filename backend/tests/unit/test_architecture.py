from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE = "automator"
PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "src" / PACKAGE

ALLOWED_IMPORTS: dict[str, frozenset[str]] = {
    "shared": frozenset(),
    "domain": frozenset({"shared"}),
    "application": frozenset({"domain", "shared"}),
    "pipelines": frozenset({"domain", "shared"}),
    "infrastructure": frozenset({"domain", "shared"}),
    "api": frozenset({"application", "domain", "shared"}),
}
FRAMEWORK_FREE_LAYERS = ("shared", "domain", "application")
FORBIDDEN_FRAMEWORKS = frozenset(
    {
        "fastapi",
        "starlette",
        "sqlmodel",
        "sqlalchemy",
        "httpx",
        "requests",
        "subprocess",
        "googleapiclient",
    }
)
MAX_FILE_LINES = 200


def layer_files(layer: str) -> list[Path]:
    return sorted((PACKAGE_ROOT / layer).rglob("*.py"))


def all_files() -> list[Path]:
    return sorted(PACKAGE_ROOT.rglob("*.py"))


def absolute_module(node: ast.ImportFrom, file: Path) -> str:
    if node.level == 0:
        return node.module or ""
    package_parts = file.relative_to(PACKAGE_ROOT.parent).with_suffix("").parts[: -node.level]
    return ".".join([*package_parts, *(node.module or "").split(".")]).strip(".")


def imported_modules(file: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            modules.add(absolute_module(node, file))
    return modules


def imported_layers(file: Path) -> set[str]:
    layers = set()
    for module in imported_modules(file):
        parts = module.split(".")
        if parts[0] == PACKAGE and len(parts) > 1:
            layers.add(parts[1])
    return layers


def display(file: Path) -> str:
    return str(file.relative_to(PACKAGE_ROOT))


@pytest.mark.parametrize("layer", sorted(ALLOWED_IMPORTS))
def test_layer_imports_only_allowed_layers(layer: str) -> None:
    allowed = ALLOWED_IMPORTS[layer] | {layer}
    violations = {
        display(file): sorted(imported_layers(file) - allowed)
        for file in layer_files(layer)
        if imported_layers(file) - allowed
    }
    assert violations == {}


@pytest.mark.parametrize("layer", FRAMEWORK_FREE_LAYERS)
def test_inner_layers_are_framework_free(layer: str) -> None:
    violations = {
        display(file): sorted(roots & FORBIDDEN_FRAMEWORKS)
        for file in layer_files(layer)
        if (roots := {module.split(".")[0] for module in imported_modules(file)})
        & FORBIDDEN_FRAMEWORKS
    }
    assert violations == {}


def test_pipelines_do_not_import_each_other() -> None:
    violations = []
    for file in layer_files("pipelines"):
        own_plugin = file.relative_to(PACKAGE_ROOT / "pipelines").parts[0]
        for module in imported_modules(file):
            parts = module.split(".")
            is_pipeline_import = parts[:2] == [PACKAGE, "pipelines"] and len(parts) > 2
            if is_pipeline_import and parts[2] not in {own_plugin, "registry"}:
                violations.append(f"{display(file)} -> {module}")
    assert violations == []


def test_every_top_level_package_is_a_known_layer() -> None:
    packages = {
        path.name for path in PACKAGE_ROOT.iterdir() if path.is_dir() and path.name != "__pycache__"
    }
    assert packages <= set(ALLOWED_IMPORTS)


def test_no_file_exceeds_line_limit() -> None:
    oversized = {
        display(file): count
        for file in all_files()
        if (count := len(file.read_text(encoding="utf-8").splitlines())) > MAX_FILE_LINES
    }
    assert oversized == {}
