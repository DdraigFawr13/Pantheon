"""`pantheon chronicle`: a timeline's story so far, read from the save, as Markdown or a page.

The chronicle is a reading of the save, never a source of numbers (GAME-03): every Ledger line
comes from a recorded event through the same `ledger_lines` the game shows, and the prose is the
narration the engine accepted. The Markdown form matches the `docs/playtests/` write-ups; the HTML
form is a phone page in the Pantheon Table's style, published by the `/chronicle` skill.
"""

from __future__ import annotations

import html
import io
from collections import defaultdict
from dataclasses import dataclass, field

from rich.console import Console
from rich.text import Text

from pantheon.engine.calendar import date_of, format_date
from pantheon.engine.state import GameState
from pantheon.storage.db import Database
from pantheon.ui.cli.app import ledger_lines, sheet
from pantheon.world.loader import World

_NOTICE = "***"


@dataclass(frozen=True)
class Entry:
    """One committed turn: what the player said, what the narrator wrote, what the engine decided."""

    turn: int
    player_input: str
    narration: str
    ledger: list[str] = field(default_factory=list)
    is_fallback: bool = False


@dataclass(frozen=True)
class Chronicle:
    timeline: str
    name: str
    subtitle: str
    prologue: list[str]
    entries: list[Entry]
    open_threads: list[str]
    settled_threads: list[str]
    sheet: str


def plain(markup: str) -> str:
    """A Ledger line without its Rich markup."""
    return Text.from_markup(markup).plain


def build(db: Database, world: World, timeline_id: str) -> Chronicle:
    """Read one timeline's turns, events and final state into a chronicle."""
    assert world.data is not None
    state = db.load_state(timeline_id)
    by_turn: dict[int, list[str]] = defaultdict(list)
    for event in db.events(timeline_id):
        by_turn[event["turn"]].extend(
            plain(line) for line in ledger_lines([(event["type"], event["payload"])])
        )
    entries = [
        Entry(t.turn, t.player_input, t.narration, by_turn.get(t.turn, []), t.is_fallback)
        for t in db.turns(timeline_id)
    ]
    console = Console(file=io.StringIO(), width=72, record=True, force_terminal=False)
    console.print(sheet(state, world))
    return Chronicle(
        timeline=timeline_id[:8],
        name=state.name or "An unwritten character",
        subtitle=_subtitle(state, world),
        prologue=by_turn.get(0, []),
        entries=entries,
        open_threads=[h.description for h in state.hooks if not h.resolved],
        settled_threads=[h.description for h in state.hooks if h.resolved],
        sheet=console.export_text().rstrip(),
    )


def _subtitle(state: GameState, world: World) -> str:
    assert world.data is not None
    parts: list[str] = []
    if state.class_id:
        current = world.data.class_of(state.class_id)
        parts.append(current.name if current else state.class_id)
    if state.profession:
        parts.append(state.profession.replace("_", " ").capitalize())
    oaths = {o.id: f"sworn to {o.god.replace('_', ' ').title()}" for o in world.data.oaths}
    parts.extend(oaths[o] for o in state.oaths if o in oaths)
    if state.level:
        parts.append(f"Tier {state.tier}, Level {state.level}")
    parts.append(format_date(date_of(state.day)))
    return " · ".join(parts)


def render_markdown(chronicle: Chronicle) -> str:
    """The `docs/playtests/` shape: a heading, the turns, then the threads and the sheet."""
    out = [
        f"# The chronicle of {chronicle.name}",
        "",
        f"{chronicle.subtitle} · timeline `{chronicle.timeline}`",
        "",
    ]
    if chronicle.prologue:
        out += ["## Before the first turn", ""] + [f"- {line}" for line in chronicle.prologue] + [""]
    out += ["## Turns", ""]
    for entry in chronicle.entries:
        out += [f"### Turn {entry.turn}" + (" (fallback)" if entry.is_fallback else ""), ""]
        out += [f"**Player:** {entry.player_input}", "", entry.narration.strip(), ""]
        if entry.ledger:
            out += [f"- `▸ {line}`" for line in entry.ledger] + [""]
    out += ["## Threads", ""]
    out += [f"- Open: {t}" for t in chronicle.open_threads] + [
        f"- Settled: {t}" for t in chronicle.settled_threads
    ]
    out += ["", "## The Ledger now", "", "```", chronicle.sheet, "```", ""]
    return "\n".join(out)


def _paragraphs(narration: str) -> str:
    blocks = []
    for block in narration.strip().split("\n\n"):
        text = block.strip()
        if not text:
            continue
        if text.startswith(_NOTICE) and text.endswith(_NOTICE):
            blocks.append(f'<p class="notice">{html.escape(text.strip("*"))}</p>')
        else:
            blocks.append(f"<p>{html.escape(text).replace(chr(10), '<br>')}</p>")
    return "\n".join(blocks)


def render_html(chronicle: Chronicle) -> str:
    """A reading page in the Pantheon Table's style: one column, the Ledger's voice in mono."""
    e = html.escape
    turns = []
    for entry in chronicle.entries:
        ledger = "".join(f"<li>▸ {e(line)}</li>" for line in entry.ledger)
        turns.append(
            f'<section id="t{entry.turn}"><h2>Turn {entry.turn}'
            + (" <small>fallback</small>" if entry.is_fallback else "")
            + f'</h2>\n<p class="said">{e(entry.player_input)}</p>\n{_paragraphs(entry.narration)}\n'
            + (f'<ul class="ledger">{ledger}</ul>' if ledger else "")
            + "</section>"
        )
    prologue = "".join(f"<li>▸ {e(line)}</li>" for line in chronicle.prologue)
    threads = "".join(f"<li>{e(t)}</li>" for t in chronicle.open_threads) or "<li>None yet.</li>"
    settled = "".join(f'<li class="done">{e(t)}</li>' for t in chronicle.settled_threads)
    before = ""
    if prologue:
        before = f'<h2>Before the first turn</h2><section><ul class="ledger">{prologue}</ul></section>'
    contents = " ".join(f'<a href="#t{x.turn}">{x.turn}</a>' for x in chronicle.entries)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(chronicle.name)} Chronicle</title>
<meta name="description" content="The story so far of {e(chronicle.name)}, read from the Pantheon save.">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Alegreya+SC:wght@500;700&family=Spectral:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Mono:wght@400;600&display=swap">
<style>
:root {{
  --bg: #e8e4ec; --page: #f8f6fa; --ink: #211b27; --muted: #6a6072; --line: #d6cfdc;
  --brass: #8a5a12; --brass-soft: #f3e7d2; --blood: #b0302c; --glow: rgb(214 160 70 / .22);
  --display: "Alegreya SC", "Palatino Linotype", Georgia, serif;
  --prose: "Spectral", Georgia, "Times New Roman", serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #16111a; --page: #211a26; --ink: #efe6dc; --muted: #ab9db0; --line: #3b2f42;
  --brass: #e3b562; --brass-soft: #34281b; --blood: #ea6a5f; --glow: rgb(227 181 98 / .13);
  color-scheme: dark }} }}
:root[data-theme="dark"] {{
  --bg: #16111a; --page: #211a26; --ink: #efe6dc; --muted: #ab9db0; --line: #3b2f42;
  --brass: #e3b562; --brass-soft: #34281b; --blood: #ea6a5f; --glow: rgb(227 181 98 / .13);
  color-scheme: dark }}
* {{ box-sizing: border-box; }}
body {{ background: radial-gradient(120% 60% at 50% 0%, var(--glow), transparent 70%) fixed, var(--bg);
  color: var(--ink); font: 17px/1.6 var(--prose); margin: 0; }}
.wrap {{ max-width: 680px; margin: 0 auto; padding: 24px max(16px, env(safe-area-inset-left, 0px)) 64px; }}
header {{ text-align: center; border-bottom: 1px solid var(--line); padding-bottom: 18px;
  margin-bottom: 24px; }}
header h1 {{ font: 700 2rem/1.1 var(--display); letter-spacing: .03em; margin: 0 0 6px; }}
header .sub {{ font: .78rem/1.5 var(--mono); color: var(--muted); margin: 0; }}
nav {{ font: .78rem var(--mono); color: var(--muted); margin: 14px 0 0; line-height: 2; }}
nav a {{ color: var(--brass); text-decoration: none; border: 1px solid var(--line); border-radius: 999px;
  padding: 2px 9px; margin-right: 4px; }}
h2 {{ font: 700 1.15rem/1.2 var(--display); letter-spacing: .04em; color: var(--brass); margin: 36px 0 8px; }}
h2 small {{ font: .7rem var(--mono); color: var(--muted); letter-spacing: 0; }}
section {{ background: var(--page); border: 1px solid var(--line); border-radius: 14px;
  padding: 4px 18px 14px; margin-top: 18px; }}
p {{ margin: 0 0 1em; overflow-wrap: anywhere; }}
.said {{ font: italic 1rem/1.5 var(--prose); color: var(--muted); border-left: 3px solid var(--brass);
  padding-left: 12px; }}
.notice {{ font: 600 .8rem/1.5 var(--mono); color: var(--brass); background: var(--brass-soft);
  border-radius: 8px; padding: 6px 10px; }}
ul.ledger, ul.threads {{ list-style: none; padding: 0; margin: 0; font: .8rem/1.7 var(--mono);
  color: var(--muted); }}
ul.ledger li {{ padding-left: 1.2em; text-indent: -1.2em; overflow-wrap: anywhere; }}
ul.threads li::before {{ content: "◆ "; color: var(--brass); }}
ul.threads li.done {{ text-decoration: line-through; opacity: .6; }}
pre {{ font: .74rem/1.45 var(--mono); background: var(--page); border: 1px solid var(--line);
  border-radius: 12px; padding: 12px; overflow-x: auto; }}
footer {{ font: .72rem var(--mono); color: var(--muted); text-align: center; margin-top: 40px; }}
</style>
</head>
<body>
<div class="wrap">
<header>
<h1>{e(chronicle.name)}</h1>
<p class="sub">{e(chronicle.subtitle)}</p>
<nav>Turns {contents}</nav>
</header>
{before}
{chr(10).join(turns)}
<h2>Threads</h2>
<section><ul class="threads">{threads}{settled}</ul></section>
<h2>The Ledger now</h2>
<pre>{e(chronicle.sheet)}</pre>
<footer>Timeline {e(chronicle.timeline)} · every number above was decided by the engine</footer>
</div>
</body>
</html>
"""
