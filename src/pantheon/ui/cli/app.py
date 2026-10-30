"""`pantheon` command line. M0: `pantheon new` creates a timeline."""

from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

from rich.console import Console

from pantheon.config import load_config
from pantheon.engine.opening import draw_opening_gods
from pantheon.engine.rng import RngStreams
from pantheon.storage.db import Database
from pantheon.world.loader import load_world


def _new(args: argparse.Namespace, console: Console) -> int:
    config = load_config(Path(args.config) if args.config else None)
    world = load_world(config.world_dir)
    if world.data is None:
        console.print("[red]world/data/ is missing; cannot draw the opening gods.[/red]")
        return 1
    seed = args.seed or config.seed or secrets.randbelow(2**62) + 1
    rng = RngStreams.from_seed(seed)
    fixed = config.opening_gods
    gods = draw_opening_gods(rng, world.data.god_ids(), fixed=(fixed[0], fixed[1]) if fixed else None)
    with Database.open(Path(args.db) if args.db else config.db_path) as db:
        tid = db.create_timeline(seed=seed, rng_state=rng.state())
        db.append_event(tid, turn=0, type_="opening_gods_drawn", payload={"gods": list(gods)})
    names = {g.id: g.name for g in world.data.gods}
    console.print(f"New timeline [bold]{tid[:8]}[/bold] · seed {seed}")
    console.print(f"Two voices will answer in the dark: {names[gods[0]]} and {names[gods[1]]}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pantheon")
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("new", help="create a timeline")
    new.add_argument("--seed", type=int, default=0, help="seed (0 = config or random)")
    new.add_argument("--db", help="database path (default: data/pantheon.db)")
    new.add_argument("--config", help="config file (default: config.toml)")
    args = parser.parse_args(argv)
    console = Console()
    if args.command == "new":
        return _new(args, console)
    return 2


if __name__ == "__main__":
    sys.exit(main())
