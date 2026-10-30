"""NAR-02 and WLD-04: every reveal-gate path is a registered flag or a state field (D-024)."""

from pathlib import Path

import pytest

from pantheon.world.loader import CanonError, gate_path_problems, load_flags, load_world

ROOT = Path(__file__).resolve().parents[2]
WORLD = ROOT / "world"

LORE = "---\nid: {id}\ntype: {type}\nvisibility: public\ntags: [x]\n---\nBody.\n"


def test_nar02_every_gate_path_is_a_registered_flag_or_state_field() -> None:
    assert gate_path_problems(load_world(WORLD)) == []


def test_nar02_every_gate_flag_has_a_setter() -> None:
    world = load_world(WORLD)
    gated = {p.removeprefix("flags.") for e in world.lore if e.gate for p in e.gate.paths() if p.startswith("flags.")}
    assert gated
    assert gated <= set(world.flags)


def test_nar02_unregistered_gate_flag_is_reported() -> None:
    world = load_world(WORLD)
    entry = next(e for e in world.lore if e.gate is not None)
    world.flags.pop(next(p for p in entry.gate.paths() if p.startswith("flags.")).removeprefix("flags."))  # type: ignore[union-attr]
    assert gate_path_problems(world)


def test_wld04_sealed_flags_are_never_set_by_the_narrator() -> None:
    world = load_world(WORLD)
    sealed = [f for f in world.flags.values() if f.sealed]
    assert sealed
    assert all(f.set_by != "narrator" for f in sealed)


def _registry(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "flags.yaml"
    path.write_text("flags:\n" + body, encoding="utf-8")
    return path


def test_flag_registry_rejects_a_narrator_flag_without_an_accept_rule(tmp_path: Path) -> None:
    with pytest.raises(CanonError):
        load_flags(_registry(tmp_path, "  - {key: a, kind: bool, set_by: narrator, when: w}\n"), sealed=False)


def test_flag_registry_rejects_a_narrator_flag_in_the_sealed_part(tmp_path: Path) -> None:
    body = "  - {key: a, kind: bool, set_by: narrator, when: w, accept: r}\n"
    with pytest.raises(CanonError):
        load_flags(_registry(tmp_path, body), sealed=True)


def test_flag_registry_rejects_a_duplicate_key(tmp_path: Path) -> None:
    body = "  - {key: a, kind: bool, set_by: engine, when: w}\n  - {key: a, kind: counter, set_by: engine, when: w}\n"
    with pytest.raises(CanonError):
        load_flags(_registry(tmp_path, body), sealed=False)


@pytest.mark.parametrize(("folder", "kind"), [("sealed", "rules"), ("", "sealed-lore")])
def test_wld04_sealed_type_and_folder_must_agree(tmp_path: Path, folder: str, kind: str) -> None:
    (tmp_path / "ok.md").write_text(LORE.format(id="ok", type="rules"), encoding="utf-8")
    target = tmp_path / folder if folder else tmp_path
    target.mkdir(exist_ok=True)
    (target / "odd.md").write_text(LORE.format(id="odd", type=kind), encoding="utf-8")
    with pytest.raises(CanonError):
        load_world(tmp_path)
