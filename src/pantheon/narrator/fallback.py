"""Engine-written turn text for when the model cannot answer (NAR-07). This path must never raise."""

from __future__ import annotations

from pantheon.engine.timeline import Simulation

_OUTCOME_WORDS = {
    "triumph": "a triumph",
    "success": "a success",
    "success_at_cost": "a success, at a cost",
    "failure": "a failure",
}


def render(sim: Simulation) -> str:
    results = [p for t, p in sim.events if t == "check_resolved"]
    parts = ["The narrator falls silent for a moment. The Ledger records only this:"]
    if results:
        for payload in results:
            outcome = _OUTCOME_WORDS.get(str(payload.get("outcome")), "an unclear result")
            stakes = str(payload.get("stakes") or "your attempt")
            parts.append(f"- {stakes}: {outcome}.")
    else:
        parts.append("- Nothing has changed yet. Try again, or try something else.")
    return "\n".join(parts)
