"""SPEC section 4: engine/ never imports narrator, llm or ui."""

import ast
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent / "src" / "pantheon" / "engine"
FORBIDDEN = ("pantheon.narrator", "pantheon.llm", "pantheon.ui", "pantheon.memory", "pantheon.storage")


def test_engine_imports_stay_inside_the_boundary() -> None:
    offenders = []
    for path in ENGINE.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            offenders += [f"{path.name}: {n}" for n in names if n.startswith(FORBIDDEN)]
    assert offenders == []
