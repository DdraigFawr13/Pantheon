"""Pacing check for the reward tables (M1e, D-014, D-046): how long Tier 1 takes in typical play.

Reads the real tables (`world/data/rewards.yaml`, the canon XP curve) and plays many simulated Tier 1 runs.
The play pattern is an estimate, not a measurement; every input is a flag, so the owner's playtests can
replace it. Run: `uv run python scripts/pacing_sim.py`.
"""

from __future__ import annotations

import argparse
import random
import statistics
from dataclasses import dataclass, field
from pathlib import Path

from pantheon.engine.state import xp_to_next
from pantheon.world.loader import load_data
from pantheon.world.schemas import GameData

TIER_ONE_LEVELS = 10


@dataclass
class Run:
    turns_to_gate: int = 0
    level_turns: list[int] = field(default_factory=list)
    coin_cp: int = 0
    items: int = 0
    fragments: int = 0
    first_shard_turn: int | None = None


def play(data: GameData, args: argparse.Namespace, rng: random.Random) -> Run:
    run, level, xp, turn = Run(), 1, 0, 0
    threats = ("minion", "standard", "elite")
    mix = (args.minion, args.standard, args.elite)
    while turn < 5000:
        turn += 1
        gained = 0
        if rng.random() < args.fight_start:
            foes = [rng.choices(threats, mix)[0] for _ in range(rng.randint(1, args.max_foes))]
            turn += args.exchanges - 1  # One exchange per turn (D-039).
            if rng.random() < args.win:
                gained += sum(data.rewards.foe_xp[t] for t in foes)
                for threat in foes:
                    _loot(data, f"foe:{threat}", run, rng, turn)
        else:
            roll = rng.random()
            if roll < args.milestone:
                gained += data.rewards.xp["milestone"]
            elif roll < args.milestone + args.major:
                gained += data.rewards.xp["major"]
            elif roll < args.milestone + args.major + args.minor:
                gained += data.rewards.xp["minor"]
            if rng.random() < args.cache:
                _loot(data, "cache", run, rng, turn)
        xp += gained
        while level < TIER_ONE_LEVELS and xp >= xp_to_next(level):
            xp -= xp_to_next(level)
            level += 1
            run.level_turns.append(turn)
        if level == TIER_ONE_LEVELS and xp >= xp_to_next(level):
            run.turns_to_gate = turn
            return run
    raise SystemExit("a run never reached the Trial; the tables pay too little")


def _loot(data: GameData, name: str, run: Run, rng: random.Random, turn: int) -> None:
    table = data.rewards.loot[name]
    for _ in range(table.rolls):
        entry = rng.choices(table.entries, [e.weight for e in table.entries])[0]
        if entry.coin_cp:
            run.coin_cp += rng.randint(*entry.coin_cp)
        elif entry.item:
            run.items += 1
        else:
            run.fragments += 1
            if run.fragments == 3 and run.first_shard_turn is None:
                run.first_shard_turn = turn


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--turns-per-hour", type=float, default=20, help="estimate: about 3 minutes a turn")
    parser.add_argument("--session-minutes", type=float, default=30)
    parser.add_argument("--fight-start", type=float, default=0.15, help="free turns that start a fight")
    parser.add_argument("--exchanges", type=int, default=3, help="turns a fight lasts")
    parser.add_argument("--max-foes", type=int, default=3)
    parser.add_argument("--minion", type=float, default=0.4)
    parser.add_argument("--standard", type=float, default=0.45)
    parser.add_argument("--elite", type=float, default=0.15)
    parser.add_argument("--win", type=float, default=0.85)
    parser.add_argument("--minor", type=float, default=0.45, help="share of other turns that earn minor XP")
    parser.add_argument("--major", type=float, default=0.15)
    parser.add_argument("--milestone", type=float, default=0.03)
    parser.add_argument("--cache", type=float, default=0.08, help="share of other turns that find a cache")
    args = parser.parse_args()

    data = load_data(Path(__file__).resolve().parents[1] / "world" / "data")
    rng = random.Random(args.seed)
    runs = [play(data, args, rng) for _ in range(args.runs)]
    hours = sorted(r.turns_to_gate / args.turns_per_hour for r in runs)
    per_session = args.turns_per_hour * args.session_minutes / 60

    def at(q: float) -> float:
        return hours[int(q * (len(hours) - 1))]

    pace = f"{args.turns_per_hour:g} turns an hour"
    print(f"Simulated {args.runs} Tier 1 runs; the play pattern and {pace} are estimates.")
    print(f"Hours to the Tier 2 Trial: median {at(0.5):.1f}, middle half {at(0.25):.1f} to {at(0.75):.1f}.")
    for level in range(2, TIER_ONE_LEVELS + 1):
        turns = statistics.median(r.level_turns[level - 2] for r in runs)
        print(f"  Level {level}: median turn {turns:.0f} (session {turns / per_session + 1:.1f})")
    sessions = statistics.median(r.turns_to_gate for r in runs) / per_session
    coin = statistics.median(r.coin_cp for r in runs) / sessions
    items = statistics.median(r.items for r in runs) / sessions
    session = f"{args.session_minutes:g}-minute session"
    print(f"Per {session}: about {coin / 12:.0f} sp of loot coin, {items:.1f} items.")
    firsts = [r.first_shard_turn for r in runs if r.first_shard_turn]
    if firsts:
        print(f"First shard (3 fragments): median session {statistics.median(firsts) / per_session + 1:.1f}.")


if __name__ == "__main__":
    main()
