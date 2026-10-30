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
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "pantheon.db"


def load_config(path: Path | None = None) -> Config:
    """Read config.toml (or the given file); fall back to defaults when it is absent."""
    path = path or Path(os.environ.get("PANTHEON_CONFIG", ROOT / "config.toml"))
    raw: dict[str, Any] = {}
    if path.exists():
        with path.open("rb") as f:
            raw = tomllib.load(f)
    paths = raw.get("paths", {})
    gameplay = raw.get("gameplay", {})
    return Config(
        world_dir=ROOT / paths.get("world_dir", "world"),
        data_dir=ROOT / paths.get("data_dir", "data"),
        seed=int(gameplay.get("seed", 0)),
        opening_gods=tuple(gameplay.get("opening_gods", ())),
        raw=raw,
    )
