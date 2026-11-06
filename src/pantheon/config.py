"""Settings from config.toml and the environment (OPS-02). No model identifier lives in code."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Config:
    world_dir: Path = ROOT / "world"
    data_dir: Path = ROOT / "data"
    seed: int = 0
    opening_gods: tuple[str, ...] = ()
    narrator_model: str = ""
    base_url: str = ""
    think: bool = True
    recent_turns: int = 6
    max_tool_rounds: int = 6
    max_tool_retries: int = 2
    violence: str = "moderate"
    permadeath: bool = False
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "pantheon.db"


def load_env_file(path: Path) -> None:
    """Copy KEY=value lines from a .env file into the environment. A real environment variable wins."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and not key.lstrip().startswith("#") and value.strip():
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def load_config(path: Path | None = None) -> Config:
    """Read config.toml (or the given file); fall back to defaults when it is absent."""
    load_env_file(ROOT / ".env")
    path = path or Path(os.environ.get("PANTHEON_CONFIG", ROOT / "config.toml"))
    raw: dict[str, Any] = {}
    if path.exists():
        with path.open("rb") as f:
            raw = tomllib.load(f)
    paths = raw.get("paths", {})
    gameplay = raw.get("gameplay", {})
    models = raw.get("models", {})
    budget = raw.get("budget", {})
    return Config(
        world_dir=ROOT / paths.get("world_dir", "world"),
        data_dir=ROOT / paths.get("data_dir", "data"),
        seed=int(gameplay.get("seed", 0)),
        opening_gods=tuple(gameplay.get("opening_gods", ())),
        narrator_model=str(models.get("narrator", "")),
        base_url=str(models.get("base_url", "")),
        think=bool(models.get("think", True)),
        recent_turns=int(budget.get("recent_turns_verbatim", 6)),
        max_tool_rounds=int(budget.get("max_tool_rounds", 6)),
        max_tool_retries=int(budget.get("max_tool_retries", 2)),
        violence=str(gameplay.get("violence", "moderate")),
        permadeath=bool(gameplay.get("permadeath", False)),
        raw=raw,
    )
