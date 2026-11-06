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
from pantheon.world.schemas import Flag, FlagRegistry, GameData


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


@dataclass(frozen=True)
class RegisteredFlag:
    key: str
    kind: str
    set_by: str
    sealed: bool


@dataclass
class World:
    root: Path
    lore: list[LoreEntry] = field(default_factory=list)
    data: GameData | None = None
    flags: dict[str, RegisteredFlag] = field(default_factory=dict)

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
        in_sealed = path.relative_to(root).parts[0] == "sealed"
        if in_sealed != (entry.type == "sealed-lore"):
            raise CanonError(f"{path}: type sealed-lore and the sealed/ folder must go together (WLD-04)")
        if entry.id in seen:
            raise CanonError(f"{path}: duplicate id {entry.id!r} (also in {seen[entry.id]})")
        seen[entry.id] = path
        world.lore.append(entry)
    if not world.lore:
        raise CanonError(f"{root}: no canon files found")
    if (root / "data").is_dir():
        world.data = load_data(root / "data")
    for folder, sealed in ((root / "data", False), (root / "sealed" / "data", True)):
        if (folder / "flags.yaml").is_file():
            for flag in load_flags(folder / "flags.yaml", sealed=sealed):
                if flag.key in world.flags:
                    raise CanonError(f"{folder / 'flags.yaml'}: flag {flag.key!r} is registered twice")
                world.flags[flag.key] = flag
    return world


def load_flags(path: Path, *, sealed: bool) -> list[RegisteredFlag]:
    """Read one part of the flag registry. Sealed flags are set by the engine or beats only (D-012)."""
    try:
        registry = FlagRegistry.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise CanonError(f"{path}: {exc}") from exc
    keys = [f.key for f in registry.flags]
    duplicates = sorted({k for k in keys if keys.count(k) > 1})
    if duplicates:
        raise CanonError(f"{path}: duplicate flag keys {duplicates}")
    if sealed and any(f.set_by == "narrator" for f in registry.flags):
        raise CanonError(f"{path}: sealed flags are set by the engine or authored beats, never the narrator")
    return [_registered(f, sealed) for f in registry.flags]


def _registered(flag: Flag, sealed: bool) -> RegisteredFlag:
    return RegisteredFlag(flag.key, flag.kind, flag.set_by, sealed)


STATE_FIELDS = ("tier", "level")


def gate_path_problems(world: World) -> list[str]:
    """Gate paths that are neither a registered flag nor a state field (NAR-02, D-024)."""
    gods = set(world.data.god_ids()) if world.data else set()
    problems = []
    for entry in world.lore:
        for path in sorted(entry.gate.paths() if entry.gate else ()):
            head, _, rest = path.partition(".")
            ok = (
                path in STATE_FIELDS
                or (head == "flags" and rest in world.flags)
                or (head == "standing" and rest in gods)
            )
            if not ok:
                problems.append(f"{entry.path.name}: {path}")
    return problems


_TABLES = (
    "gods",
    "affinities",
    "oaths",
    "classes",
    "peoples",
    "professions",
    "origins",
    "rewards",
    "clocks",
    "combat",
)
_LATER_TABLES = ("skills", "titles", "evolutions")  # Canon batches in M3.5; the game runs without them.


def load_data(folder: Path) -> GameData:
    raw: dict[str, object] = {}
    later = [name for name in _LATER_TABLES if (folder / f"{name}.yaml").is_file()]
    for name in (*_TABLES, *later):
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
