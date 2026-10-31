"""In-world time (ENG-11, world/00_overview.md). Time moves only through events, never the wall clock.

The state counts minutes from the start of play. Dates, seasons and clocks are worked out from that count.
"""

from __future__ import annotations

from dataclasses import dataclass

from pantheon.engine.state import GameState
from pantheon.engine.timeline import Simulation, change_standing
from pantheon.world.schemas import GameData

MONTHS = (
    "Firstthaw",
    "Mudmonth",
    "Seedtide",
    "Greenmonth",
    "Highsun",
    "Longday",
    "Haymonth",
    "Reaping",
    "Leaffall",
    "Frostcoming",
    "Deepwinter",
    "Lastdark",
)
DAYS_PER_MONTH = 30
COUNTED_DAYS_PER_YEAR = len(MONTHS) * DAYS_PER_MONTH
DAYS_PER_YEAR = COUNTED_DAYS_PER_YEAR + 5  # The Blank Days, which no Ledger records.
START_YEAR = 1140
START_DAY_OF_YEAR = MONTHS.index("Seedtide") * DAYS_PER_MONTH  # Play begins on 1 Seedtide.
SEASON_DAYS = 90
MINUTES_PER_DAY = 1440
REST_MINUTES = 8 * 60


@dataclass(frozen=True)
class GameDate:
    year: int
    month: str | None  # None on a Blank Day.
    day: int

    def view(self) -> dict[str, int | str]:
        return {"day": self.day, "month": self.month or "Blank Day", "year": self.year}


def date_of(elapsed_days: int) -> GameDate:
    years, day_of_year = divmod(START_DAY_OF_YEAR + elapsed_days, DAYS_PER_YEAR)
    year = START_YEAR + years
    if day_of_year >= COUNTED_DAYS_PER_YEAR:
        return GameDate(year, None, day_of_year - COUNTED_DAYS_PER_YEAR + 1)
    month, day = divmod(day_of_year, DAYS_PER_MONTH)
    return GameDate(year, MONTHS[month], day + 1)


def format_date(date: GameDate) -> str:
    place = f"{date.day} {date.month}" if date.month else f"Blank Day {date.day},"
    return f"{place} {date.year:,} AS"


def counted_days(elapsed_days: int) -> int:
    """Days elapsed since the start of play, leaving out Blank Days (D-038)."""
    years, day_of_year = divmod(START_DAY_OF_YEAR + elapsed_days, DAYS_PER_YEAR)
    return years * COUNTED_DAYS_PER_YEAR + min(day_of_year, COUNTED_DAYS_PER_YEAR) - START_DAY_OF_YEAR


def clock_value(state: GameState, data: GameData, clock_id: str) -> int:
    """A clock's segments. It keeps its canon start until an event moves it, so old saves need no event."""
    if clock_id in state.clocks:
        return state.clocks[clock_id]
    return next(c.start for c in data.clocks if c.id == clock_id)


def _season_turns(sim: Simulation, season_end: int) -> None:
    """One segment per clock, and one more if its threads were neglected all season (world/factions.md)."""
    state = sim.state
    for clock in sim.rules.data.clocks:
        value = clock_value(state, sim.rules.data, clock.id)
        engaged = state.clocks_engaged.get(clock.id)
        neglected = engaged is None or engaged < season_end - SEASON_DAYS
        new_value = min(clock.segments, value + 1 + int(neglected))
        if new_value > value:
            sim.emit(
                "clock_advanced",
                {
                    "clock": clock.id,
                    "name": clock.name,
                    "value": new_value,
                    "segments": clock.segments,
                    "neglected": neglected,
                    "filled": new_value == clock.segments,
                },
            )


def _lapse_petitions(sim: Simulation) -> None:
    """A petition past its deadline counts as ignored (world/pantheon.md, Petitions)."""
    state = sim.state
    for hook in state.hooks:
        if hook.petition_god and not hook.resolved and state.day > hook.deadline_day:
            sim.emit("petition_resolved", {"hook_id": hook.id, "granted": False, "reason": "left too long"})
            change_standing(
                sim,
                hook.petition_god,
                -sim.rules.data.rewards.petition.ignored,
                f"ignored a petition: {hook.description}",
            )


def pass_time(sim: Simulation, minutes: int, span: str, reason: str) -> None:
    """Move the calendar, then everything time drives. Oath timers and Boons wait for canon (D-038)."""
    before = counted_days(sim.state.day)
    sim.emit("time_advanced", {"minutes": minutes, "span": span, "reason": reason})
    after = counted_days(sim.state.day)
    for season in range(before // SEASON_DAYS + 1, after // SEASON_DAYS + 1):
        _season_turns(sim, season * SEASON_DAYS)
    _lapse_petitions(sim)
