"""Reveal-gate grammar (architecture section 7). Parsed to a tree and evaluated; never passed to eval.

    expr       := or_expr
    or_expr    := and_expr ("or" and_expr)*
    and_expr   := not_expr ("and" not_expr)*
    not_expr   := "not" not_expr | atom
    atom       := "(" expr ")" | value (OP value)?
    value      := path | number | string | "true" | "false"
    OP         := >= <= > < == !=

A bare path is true when its value is set and truthy. A missing path compares as false.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_TOKEN = re.compile(
    r"\s*(?:(?P<num>\d+(?:\.\d+)?)|(?P<str>\"[^\"]*\")|(?P<op>>=|<=|==|!=|>|<)"
    r"|(?P<paren>[()])|(?P<name>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*))"
)
_KEYWORDS = {"and", "or", "not", "true", "false"}


class GateError(ValueError):
    """A reveal gate that does not parse."""


@dataclass(frozen=True)
class Node:
    kind: str  # "or", "and", "not", "cmp", "path", "lit"
    children: tuple[Node, ...] = ()
    value: Any = None

    def paths(self) -> set[str]:
        found = {self.value} if self.kind == "path" else set()
        for child in self.children:
            found |= child.paths()
        return found


def _tokenize(text: str) -> list[tuple[str, str]]:
    tokens, pos = [], 0
    text = text.rstrip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise GateError(f"unexpected text at {pos}: {text[pos : pos + 12]!r}")
        kind = m.lastgroup or ""
        tokens.append((kind, m.group(kind)))
        pos = m.end()
    if not tokens:
        raise GateError("empty gate")
    return tokens


class _Parser:
    def __init__(self, tokens: list[tuple[str, str]]) -> None:
        self.tokens, self.i = tokens, 0

    def peek(self) -> tuple[str, str] | None:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def take(self) -> tuple[str, str]:
        tok = self.peek()
        if tok is None:
            raise GateError("gate ends too early")
        self.i += 1
        return tok

    def keyword(self, word: str) -> bool:
        tok = self.peek()
        if tok == ("name", word):
            self.i += 1
            return True
        return False

    def expr(self) -> Node:
        node = self.and_expr()
        while self.keyword("or"):
            node = Node("or", (node, self.and_expr()))
        return node

    def and_expr(self) -> Node:
        node = self.not_expr()
        while self.keyword("and"):
            node = Node("and", (node, self.not_expr()))
        return node

    def not_expr(self) -> Node:
        if self.keyword("not"):
            return Node("not", (self.not_expr(),))
        return self.atom()

    def atom(self) -> Node:
        if self.peek() == ("paren", "("):
            self.take()
            node = self.expr()
            if self.take() != ("paren", ")"):
                raise GateError("missing closing parenthesis")
            return node
        left = self.value()
        tok = self.peek()
        if tok is not None and tok[0] == "op":
            self.take()
            return Node("cmp", (left, self.value()), tok[1])
        return left

    def value(self) -> Node:
        kind, text = self.take()
        if kind == "num":
            return Node("lit", value=float(text) if "." in text else int(text))
        if kind == "str":
            return Node("lit", value=text[1:-1])
        if kind == "name" and text in ("true", "false"):
            return Node("lit", value=text == "true")
        if kind == "name" and text not in _KEYWORDS:
            return Node("path", value=text)
        raise GateError(f"expected a value, got {text!r}")


def parse(text: str) -> Node:
    parser = _Parser(_tokenize(text))
    node = parser.expr()
    if parser.peek() is not None:
        raise GateError(f"unexpected {parser.peek()[1]!r} after a complete gate")  # type: ignore[index]
    return node


def _lookup(state: dict[str, Any], path: str) -> Any:
    current: Any = state
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _value(node: Node, state: dict[str, Any]) -> Any:
    return _lookup(state, node.value) if node.kind == "path" else node.value


_COMPARE = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def evaluate(node: Node, state: dict[str, Any]) -> bool:
    if node.kind == "or":
        return any(evaluate(c, state) for c in node.children)
    if node.kind == "and":
        return all(evaluate(c, state) for c in node.children)
    if node.kind == "not":
        return not evaluate(node.children[0], state)
    if node.kind == "cmp":
        left, right = (_value(c, state) for c in node.children)
        if left is None or right is None:
            return False
        try:
            return bool(_COMPARE[node.value](left, right))
        except TypeError:
            return False
    return bool(_value(node, state))
