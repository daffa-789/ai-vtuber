"""Architectural verification test: Layer Isolation.

Enforces that:
1. silverwolf/domain has zero imports from application, adapters, infrastructure, voice, ui, or external I/O libraries.
2. silverwolf/application has zero imports from adapters, infrastructure, voice, ui, or external I/O libraries.
Dependencies strictly point inward: adapters/infrastructure -> application -> domain.
"""

import ast
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DOMAIN_DIR = ROOT_DIR / "silverwolf" / "domain"
APPLICATION_DIR = ROOT_DIR / "silverwolf" / "application"

FORBIDDEN_FOR_DOMAIN = {
    "silverwolf.application",
    "silverwolf.adapters",
    "silverwolf.infrastructure",
    "silverwolf.voice",
    "silverwolf.ui",
    "silverwolf.inference",
    "silverwolf.core",
    "webview",
    "httpx",
    "sounddevice",
    "torch",
}

FORBIDDEN_FOR_APPLICATION = {
    "silverwolf.adapters",
    "silverwolf.infrastructure",
    "silverwolf.voice",
    "silverwolf.ui",
    "silverwolf.inference",
    "silverwolf.core",
    "webview",
    "httpx",
    "sounddevice",
    "torch",
}


def get_imports(py_file: Path) -> list[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def test_domain_layer_isolation():
    """Verify that silverwolf/domain does not import any outer layers."""
    domain_files = list(DOMAIN_DIR.rglob("*.py"))
    assert len(domain_files) > 0, "Domain files must exist"

    violations = []
    for py_file in domain_files:
        for imp in get_imports(py_file):
            for forbidden in FORBIDDEN_FOR_DOMAIN:
                if imp == forbidden or imp.startswith(f"{forbidden}."):
                    violations.append(f"{py_file.name}: imports forbidden '{imp}'")

    assert not violations, f"Layer violations in silverwolf/domain: {violations}"


def test_application_layer_isolation():
    """Verify that silverwolf/application does not import adapters or infrastructure."""
    app_files = list(APPLICATION_DIR.rglob("*.py"))
    assert len(app_files) > 0, "Application files must exist"

    violations = []
    for py_file in app_files:
        for imp in get_imports(py_file):
            for forbidden in FORBIDDEN_FOR_APPLICATION:
                if imp == forbidden or imp.startswith(f"{forbidden}."):
                    violations.append(f"{py_file.name}: imports forbidden '{imp}'")

    assert not violations, f"Layer violations in silverwolf/application: {violations}"
