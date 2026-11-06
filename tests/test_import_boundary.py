"""SPEC section 4: engine/ never imports narrator, llm or ui."""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
ENGINE = SRC / "pantheon" / "engine"
FORBIDDEN = ("pantheon.narrator", "pantheon.llm", "pantheon.ui", "pantheon.memory", "pantheon.storage")


def _forbidden(name: str) -> bool:
    return any(name == f or name.startswith(f + ".") for f in FORBIDDEN)


def _call_name(func: ast.expr) -> str:
    if isinstance(func, ast.Attribute):
        return func.attr
    return func.id if isinstance(func, ast.Name) else ""


def scan_imports(source: str, package: str) -> list[str]:
    """Return the forbidden modules `source` imports. `package` is the dotted package of the file."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = package.split(".")
                parts = parts[: len(parts) - (node.level - 1)]
                base = ".".join([*parts, base] if base else parts)
            names = [base] + [f"{base}.{a.name}" for a in node.names]
        elif (
            isinstance(node, ast.Call)
            and _call_name(node.func) in {"import_module", "__import__"}
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            names = [node.args[0].value]
        found += [n for n in names if _forbidden(n)]
    return found


def test_engine_imports_stay_inside_the_boundary() -> None:
    offenders = []
    for path in ENGINE.rglob("*.py"):
        package = ".".join(path.relative_to(SRC).parent.parts)
        offenders += [f"{path.name}: {n}" for n in scan_imports(path.read_text(encoding="utf-8"), package)]
    assert offenders == []


@pytest.mark.parametrize(
    ("snippet", "expected"),
    [
        ("import pantheon.ui.cli", ["pantheon.ui.cli"]),
        ("from pantheon import ui", ["pantheon.ui"]),
        ("from pantheon.llm.base import X", ["pantheon.llm.base", "pantheon.llm.base.X"]),
        ("from ..ui import x", ["pantheon.ui", "pantheon.ui.x"]),
        ("from .. import narrator", ["pantheon.narrator"]),
        ('importlib.import_module("pantheon.ui")', ["pantheon.ui"]),
        ('__import__("pantheon.storage.db")', ["pantheon.storage.db"]),
        ("from pantheon.engine import tools", []),
        ("from . import tools", []),
        ("import pantheon.uiextras", []),
    ],
)
def test_import_boundary_scanner_flags_bad_snippets(snippet: str, expected: list[str]) -> None:
    assert scan_imports(snippet, "pantheon.engine") == expected
