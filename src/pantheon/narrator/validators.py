"""Checks on narrator prose (NAR-04, D-022, D-030)."""

from __future__ import annotations

import re

from pantheon.engine.tools import tool_definitions

_NUMBER = re.compile(r"\d[\d,.]*\d|\d")
_NUMBER_WORDS = (
    "one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|hundred"
)
_UNITS = "points?|percent|damage|xp|experience|hit points?|stamina|mana"
_BANNED = (
    (re.compile(r"\b\d*d(?:4|6|8|10|12|20|100)\b", re.I), "dice notation"),
    (re.compile(r"\b(?:you|they|he|she) rolled? (?:a|an|the)\b|\broll of\b", re.I), "a dice roll"),
    (
        re.compile(r"\bskill check\b|\bsaving throw\b|\bdifficulty class\b|\bsuccess at cost\b", re.I),
        "a game term",
    ),
    (re.compile(r"\b(?:HP|XP|DC|STR|AGI|DEX|INT|VIG|RES|PRE)\b"), "a stat abbreviation"),
    (re.compile(rf"\b(?:{_NUMBER_WORDS})\s+(?:{_UNITS})\b", re.I), "a number with a game unit"),
)
_TOOL_NAMES = re.compile(r"\b(?:" + "|".join(t["name"] for t in tool_definitions()) + r")\b")
_LIST_WORDS = r"choose|next action|actions?|options?|choices?"
_ACTION_LIST = re.compile(
    rf"(?:^[^\n]*\b(?:{_LIST_WORDS})\b[^\n]*:[*_ \t]*\n\s*)?"
    r"(?:^[ \t]*(?:\d+[.)]|[-*])[ \t]+.*(?:\n|\Z)){2,}",
    re.I | re.M,
)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_MIN_SENTENCE = 25
_RULE = re.compile(r"^[ \t]*-{3,}[ \t]*$\n?", re.M)
_CLOSING_QUESTION = re.compile(r"\n\s*[*_]*what (?:will|do) you do\??[*_]*\s*\Z", re.I)


def strip_action_list(text: str) -> str:
    """Cut action lists the model wrote into its prose: those go through `suggest_actions` (D-030)."""
    text = re.sub(r"\n{3,}", "\n\n", _RULE.sub("", _ACTION_LIST.sub("", text)))
    return _CLOSING_QUESTION.sub("", text.rstrip()).rstrip()


def repeats_earlier_turn(text: str, recent: list[str]) -> bool:
    """True when a third or more of this reply's sentences appeared word for word in a recent turn."""
    sentences = {s.strip() for s in _SENTENCE.split(text) if len(s.strip()) > _MIN_SENTENCE}
    if not sentences:
        return False
    earlier = " ".join(recent)
    return sum(s in earlier for s in sentences) * 3 >= len(sentences)


def prose_problems(text: str, allowed_numbers: set[int]) -> list[str]:
    """What is wrong with this reply as narration; empty means it may be shown."""
    problems = []
    for match in _NUMBER.finditer(text):
        digits = match.group().replace(",", "").rstrip(".")
        if not digits.isdigit() or int(digits) not in allowed_numbers:
            problems.append(f"the number {match.group()} did not come from the engine this turn")
    problems += [f"it mentions {label}" for pattern, label in _BANNED if pattern.search(text)]
    if _TOOL_NAMES.search(text):
        problems.append("it names a tool in the prose")
    return problems
