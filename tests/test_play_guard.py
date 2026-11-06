"""The play guard (D-041) keeps secret and sealed canon out of the narrator session (NAR-02, WLD-04)."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "play-guard.mjs"
SETTINGS = Path(__file__).resolve().parents[1] / ".claude" / "settings.json"

if shutil.which("node") is None:
    if os.environ.get("CI"):
        pytest.fail("node is required in CI: the play guard is a node hook", pytrace=False)
    pytest.skip("the play guard is a node hook and node is not installed", allow_module_level=True)


class Guard:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.home = root / "home"
        self.home.mkdir()

    def decision(self, tool: str, raw: str | None = None, **tool_input: object) -> str | None:
        event = raw if raw is not None else json.dumps({"tool_name": tool, "tool_input": tool_input})
        env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(self.root),
            "HOME": str(self.home),
            "USERPROFILE": str(self.home),
        }
        result = subprocess.run(
            ["node", str(HOOK)], input=event, capture_output=True, text=True, env=env, check=True
        )
        if not result.stdout.strip():
            return None
        out = json.loads(result.stdout)["hookSpecificOutput"]
        assert out["hookEventName"] == "PreToolUse"
        return str(out["permissionDecision"])

    def denied(self, tool: str, **tool_input: object) -> bool:
        return self.decision(tool, **tool_input) == "deny"

    def play(self) -> None:
        (self.root / "data").mkdir(exist_ok=True)
        (self.root / "data" / ".playing").touch()


@pytest.fixture
def guard(tmp_path: Path) -> Guard:
    return Guard(tmp_path)


def test_wld04_the_guard_runs_on_every_tool() -> None:
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    entries = [e for e in settings["hooks"]["PreToolUse"] if "play-guard" in e["hooks"][0]["command"]]
    assert [e["matcher"] for e in entries] == ["*"]


def test_nar02_the_guard_is_off_while_nobody_plays(guard: Guard) -> None:
    assert not guard.denied("Grep", pattern="x")
    assert not guard.denied("Bash", command="cat world/secret/a.md")


def test_nar02_reads_stay_on_public_files(guard: Guard) -> None:
    guard.play()
    root = guard.root
    assert guard.denied("Read", file_path=str(root / "world" / "secret" / "a.md"))
    assert guard.denied("Read", file_path=str(root / "world" / "sealed" / "a.md"))
    assert guard.denied("Read", file_path=str(root / "src" / "pantheon" / "sealed" / "x.py"))
    assert guard.denied("Read", file_path=str(root / "world" / "data" / "flags.yaml"))
    assert guard.denied("Read", file_path=str(root / "data" / ".." / "world" / "secret" / "a.md"))
    assert not guard.denied("Read", file_path=str(root / "world" / "pantheon.md"))
    assert not guard.denied("Read", file_path=str(root / "data" / "narration.md"))


def test_nar02_saved_command_output_is_readable_only_in_its_own_folder(guard: Guard) -> None:
    guard.play()
    projects = guard.home / ".claude" / "projects"
    saved = projects / "-home-user-Pantheon" / "abc" / "tool-results" / "b1.txt"
    assert not guard.denied("Read", file_path=str(saved))
    escape = projects / "x" / "abc" / "tool-results" / ".." / ".." / ".." / ".." / "etc" / "a.txt"
    assert guard.denied("Read", file_path=str(escape))
    elsewhere = guard.root / "world" / "secret" / "p" / "s" / "tool-results" / "a.txt"
    assert guard.denied("Read", file_path=str(elsewhere))  # The same shape outside ~/.claude/projects.


@pytest.mark.skipif(os.name == "nt", reason="symlinks need extra rights on Windows")
def test_nar02_a_symlink_in_the_save_folder_cannot_reach_secret_canon(guard: Guard) -> None:
    guard.play()
    secret = guard.root / "world" / "secret"
    secret.mkdir(parents=True)
    (secret / "a.md").write_text("x", encoding="utf-8")
    (guard.root / "data" / "link.md").symlink_to(secret / "a.md")
    assert guard.denied("Read", file_path=str(guard.root / "data" / "link.md"))


@pytest.mark.parametrize(
    "command",
    [
        'uv run -q pantheon session begin "I climb the stair, don\'t I?"',
        'uv run pantheon session tool request_check \'{"stat": "agility", "stakes": "a fall?"}\'',
        "uv run -q pantheon session narrate data/narration.md",
        "uv run -q pantheon session screen data/screen.json",
        "uv run -q pantheon session choose offer veshra",
        "uv run -q pantheon session go",
        "uv run -q pantheon session use tonic",
        "uv run -q pantheon session equip iron_sword",
        "uv run -q pantheon session unequip weapon",
        "uv run -q pantheon session tool request_check --file data/tool.json",
        "scripts/saves.sh pull",
        "scripts/saves.sh push",
    ],
)
def test_nar02_bash_runs_the_session_steps(guard: Guard, command: str) -> None:
    guard.play()
    assert not guard.denied("Bash", command=command)


@pytest.mark.parametrize(
    "command",
    [
        "cd x;cat${IFS}world/s?cret/f&&uv run -q pantheon session",  # Audit 2026-11-06 repo F1.
        "cd data && uv run -q pantheon session status",
        "uv run pantheon session status; cat world/secret/a.md",
        "uv run pantheon session status && cat world/x.md",
        "uv run pantheon session status | tee x",
        "uv run pantheon session status $(cat world/x.md)",
        'uv run pantheon session begin "$(cat world/x.md)"',
        "uv run pantheon session begin `id`",
        "uv run pantheon session narrate world/s?cret/a.md",
        "uv run pantheon session narrate world/pantheon.md",
        "uv run pantheon session narrate data/../world/x.md",
        "uv run pantheon session export data/x.sql",
        "uv run pantheon session tool request_check --file world/secret/a.md",
        "uv run pantheon session tool request_check --file data/../world/x.md",
        "uv run pantheon session import data/x.sql",
        "uv run pantheon play",
        "cat world/pantheon.md",
        "scripts/saves.sh pull extra",
        "uv run pantheon session status > data/x",
        "uv run pantheon session status\ncat world/x.md",
    ],
)
def test_nar02_bash_refuses_anything_else(guard: Guard, command: str) -> None:
    guard.play()
    assert guard.denied("Bash", command=command)


def test_nar02_writes_stay_in_the_save_folder(guard: Guard) -> None:
    guard.play()
    assert not guard.denied("Write", file_path=str(guard.root / "data" / "narration.md"))
    assert not guard.denied("Edit", file_path=str(guard.root / "data" / "narration.md"))
    assert guard.denied("Write", file_path=str(guard.root / "src" / "x.py"))
    assert guard.denied("Edit", file_path=str(guard.root / "data" / ".." / "AGENTS.md"))


@pytest.mark.parametrize(
    "tool",
    [
        "Grep",
        "Glob",
        "Agent",
        "Task",
        "NotebookEdit",
        "MultiEdit",
        "WebFetch",
        "Skill",
        "Artifact",
        "mcp__github__get_file_contents",
        "mcp__Google_Drive__read_file_content",
        "SendUserFile",
    ],
)
def test_wld04_every_other_tool_is_off_during_play(guard: Guard, tool: str) -> None:
    guard.play()
    assert guard.denied(tool, path="world/secret/a.md")


def test_nar02_the_game_page_takes_files_only_from_the_save_folder(guard: Guard) -> None:
    guard.play()
    data = guard.root / "data" / "screen.json"
    assert not guard.denied("ArtifactData", action="set", file_path=str(data))
    assert not guard.denied("ArtifactData", action="get", collection="game", doc_id="screen")
    assert guard.denied("ArtifactData", action="set", file_path=str(guard.root / "world" / "secret" / "a.md"))
    assert guard.denied(
        "ArtifactData", action="batch", writes=[{"op": "set", "file_path": "world/sealed/a.md"}]
    )
    assert not guard.denied("ArtifactComments", action="reply")


def test_nar02_a_call_the_guard_cannot_read_is_refused(guard: Guard) -> None:
    guard.play()
    assert guard.decision("Bash", raw="not json") == "deny"
