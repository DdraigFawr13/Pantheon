"""Load and validate the canon in world/ (WLD-01, WLD-02, WLD-04).

Every Markdown file except README.md carries YAML frontmatter. Files are read-only at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from pantheon.world.gates import GateError, Node, parse
from pantheon.world.schemas import GameData


class CanonError(ValueError):
    """A canon file that does not meet WLD-01."""


class Frontmatter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    type: str = Field(min_length=1)
    visibility: Literal["public", "secret"]
    tags: list[str] = Field(min_length=1)
    reveal_gate: str | None = None

    @model_validator(mode="after")
    def _gate_matches_visibility(self) -> Frontmatter:
        if self.visibility == "secret" and not self.reveal_gate:
            raise ValueError("secret entries need a reveal_gate")
        if self.visibility == "public" and self.reveal_gate:
            raise ValueError("public entries must not have a reveal_gate")
        return self


@dataclass(frozen=True)
class LoreEntry:
    id: str
    type: str
    visibility: str
    tags: tuple[str, ...]
    reveal_gate: str | None
    gate: Node | None
    body: str
    path: Path


@dataclass
class World:
    root: Path
    lore: list[LoreEntry] = field(default_factory=list)
    data: GameData | None = None

    def by_id(self, entry_id: str) -> LoreEntry:
        return next(e for e in self.lore if e.id == entry_id)


def _split(text: str, path: Path) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        raise CanonError(f"{path}: missing YAML frontmatter")
    end = text.find("\n---", 4)
    if end == -1:
        raise CanonError(f"{path}: frontmatter is not closed with ---")
    try:
        meta = yaml.safe_load(text[4:end])
    except yaml.YAMLError as exc:
        raise CanonError(f"{path}: frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(meta, dict):
        raise CanonError(f"{path}: frontmatter must be a mapping")
    return meta, text[end + 4 :].lstrip("\n")


def load_entry(path: Path) -> LoreEntry:
    meta, body = _split(path.read_text(encoding="utf-8"), path)
    try:
        fm = Frontmatter.model_validate(meta)
    except ValidationError as exc:
        raise CanonError(f"{path}: {exc}") from exc
    try:
        gate = parse(fm.reveal_gate) if fm.reveal_gate else None
    except GateError as exc:
        raise CanonError(f"{path}: reveal_gate does not parse: {exc}") from exc
    return LoreEntry(fm.id, fm.type, fm.visibility, tuple(fm.tags), fm.reveal_gate, gate, body, path)


def load_world(root: Path) -> World:
    world = World(root=root)
    seen: dict[str, Path] = {}
    for path in sorted(root.rglob("*.md")):
        if path.name == "README.md":
            continue
        entry = load_entry(path)
        if entry.id in seen:
            raise CanonError(f"{path}: duplicate id {entry.id!r} (also in {seen[entry.id]})")
        seen[entry.id] = path
        world.lore.append(entry)
    if not world.lore:
        raise CanonError(f"{root}: no canon files found")
    if (root / "data").is_dir():
        world.data = load_data(root / "data")
    return world


_TABLES = ("gods", "affinities", "oaths", "classes", "peoples", "professions")


def load_data(folder: Path) -> GameData:
    raw: dict[str, object] = {}
    for name in _TABLES:
        path = folder / f"{name}.yaml"
        try:
            raw[name] = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise CanonError(f"{path}: {exc}") from exc
    try:
        data = GameData.model_validate(raw)
    except ValidationError as exc:
        raise CanonError(f"{folder}: {exc}") from exc
    _check_references(data, folder)
    return data


def _check_references(data: GameData, folder: Path) -> None:
    affinities = set(data.affinities.all_named())
    classes = {c.id for c in data.classes}
    oaths = {o.id: o for o in data.oaths}
    problems = []
    for god in data.gods:
        problems += [f"god {god.id}: unknown affinity {a}" for a in god.affinities if a not in affinities]
        problems += [f"god {god.id}: unknown class {c}" for c in god.favoured_classes if c not in classes]
        oath = oaths.get(god.first_oath)
        if oath is None or oath.god != god.id:
            problems.append(f"god {god.id}: first_oath {god.first_oath} is not one of its Oaths")
    for oath in data.oaths:
        if oath.affinity not in affinities:
            problems.append(f"oath {oath.id}: unknown affinity {oath.affinity}")
    special = {"any_basic", "birth_rift"}
    for people in data.peoples:
        problems += [
            f"people {people.id}: unknown affinity {a}"
            for a in people.innate_affinity
            if a not in affinities and a not in special
        ]
    if problems:
        raise CanonError(f"{folder}: " + "; ".join(problems))
