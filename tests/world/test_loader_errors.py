"""WLD-01: each loader error path rejects bad canon with its own message (tmp_path fixtures only)."""

import shutil
from pathlib import Path

import pytest

from pantheon.world.loader import CanonError, load_data, load_world

WORLD = Path(__file__).resolve().parents[2] / "world"
PUBLIC = "---\nid: {id}\ntype: rules\nvisibility: public\ntags: [x]\n---\nBody.\n"


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _data_copy(tmp_path: Path) -> Path:
    """A world with one lore file and a copy of the public data tables."""
    _write(tmp_path / "ok.md", PUBLIC.format(id="ok"))
    shutil.copytree(WORLD / "data", tmp_path / "data")
    return tmp_path


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("---\nid: a\ntype: rules\n", "frontmatter is not closed with ---"),
        ("---\nid: [unclosed\n---\nBody.\n", "frontmatter is not valid YAML"),
        ("---\n- just\n- a list\n---\nBody.\n", "frontmatter must be a mapping"),
        (
            "---\nid: a\ntype: rules\nvisibility: public\ntags: [x]\nreveal_gate: tier >= 1\n---\nBody.\n",
            "public entries must not have a reveal_gate",
        ),
    ],
)
def test_wld01_bad_frontmatter_is_named(tmp_path: Path, text: str, message: str) -> None:
    _write(tmp_path / "a.md", text)
    with pytest.raises(CanonError, match=message):
        load_world(tmp_path)


def test_wld01_duplicate_lore_id_is_rejected(tmp_path: Path) -> None:
    _write(tmp_path / "a.md", PUBLIC.format(id="same"))
    _write(tmp_path / "b.md", PUBLIC.format(id="same"))
    with pytest.raises(CanonError, match="duplicate id 'same'"):
        load_world(tmp_path)


def test_wld01_empty_world_is_rejected(tmp_path: Path) -> None:
    _write(tmp_path / "README.md", "# Not canon\n")
    with pytest.raises(CanonError, match="no canon files found"):
        load_world(tmp_path)


def test_wld01_flag_in_both_registries_is_rejected(tmp_path: Path) -> None:
    root = _data_copy(tmp_path)
    key = next(
        line.split("key:")[1].split(",")[0].strip()
        for line in (root / "data" / "flags.yaml").read_text(encoding="utf-8").splitlines()
        if "key:" in line
    )
    (root / "sealed" / "data").mkdir(parents=True)
    _write(
        root / "sealed" / "data" / "flags.yaml",
        f"flags:\n  - {{key: {key}, kind: bool, set_by: engine, when: w}}\n",
    )
    with pytest.raises(CanonError, match=f"flag '{key}' is registered twice"):
        load_world(root)


def test_wld01_missing_data_table_is_rejected(tmp_path: Path) -> None:
    root = _data_copy(tmp_path)
    (root / "data" / "gods.yaml").unlink()
    with pytest.raises(CanonError, match="gods.yaml"):
        load_data(root / "data")


def test_wld01_unparseable_data_table_is_rejected(tmp_path: Path) -> None:
    root = _data_copy(tmp_path)
    _write(root / "data" / "gods.yaml", "- [unclosed\n")
    with pytest.raises(CanonError, match="gods.yaml"):
        load_data(root / "data")


def test_wld01_invalid_data_table_is_rejected(tmp_path: Path) -> None:
    root = _data_copy(tmp_path)
    _write(root / "data" / "gods.yaml", "- {id: broken}\n")
    with pytest.raises(CanonError, match="validation error"):
        load_data(root / "data")


def test_wld01_first_oath_must_belong_to_its_god(tmp_path: Path) -> None:
    root = _data_copy(tmp_path)
    gods = root / "data" / "gods.yaml"
    _write(gods, gods.read_text(encoding="utf-8").replace("first_oath: open_hand", "first_oath: held_line"))
    with pytest.raises(CanonError, match="god veshra: first_oath held_line is not one of its Oaths"):
        load_data(root / "data")
