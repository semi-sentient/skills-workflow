"""Parse a Claude Code session transcript into an assertable trajectory.

Output-only grading cannot see the failures this repo actually ships: asking
three questions in one turn, committing before the review gate, reading a diff
the skill promised not to read. Those are properties of the *path*, and the
path is recorded — `claude -p --output-format json` returns a `session_id`, and
that resolves to a JSONL transcript with one record per turn.

Sub-agent turns are marked `isSidechain: true`. `main_*` accessors exclude them
so an orchestrator-side assertion ("never reads source files") is not defeated
by a sub-agent legitimately doing that work.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"


def project_slug(cwd: Path) -> str:
    """Claude Code's on-disk name for a working directory."""
    return re.sub(r"[^a-zA-Z0-9]", "-", str(cwd))


def find_transcript(session_id: str, cwd: Path | None = None) -> Path | None:
    if cwd is not None:
        direct = PROJECTS / project_slug(cwd) / f"{session_id}.jsonl"
        if direct.is_file():
            return direct
    if not PROJECTS.is_dir():
        return None
    hits = sorted(PROJECTS.glob(f"*/{session_id}.jsonl"))
    return hits[0] if hits else None


@dataclass
class ToolCall:
    name: str
    input: dict
    index: int  # position in the ordered stream of all tool calls
    sidechain: bool

    @property
    def command(self) -> str:
        return str(self.input.get("command", ""))

    @property
    def path(self) -> str:
        return str(self.input.get("file_path", self.input.get("path", "")))


class Trace:
    """An ordered view of one session's tool calls and assistant text."""

    def __init__(self, records: list[dict]):
        self.records = records
        self.calls: list[ToolCall] = []
        self.turns: list[tuple[bool, str]] = []  # (sidechain, text) per assistant turn

        idx = 0
        for rec in records:
            if rec.get("type") != "assistant":
                continue
            side = bool(rec.get("isSidechain"))
            content = (rec.get("message") or {}).get("content") or []
            if isinstance(content, str):
                self.turns.append((side, content))
                continue
            text_parts = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    self.calls.append(
                        ToolCall(block.get("name", ""), block.get("input") or {}, idx, side)
                    )
                    idx += 1
                elif block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            if text_parts:
                self.turns.append((side, "\n".join(text_parts)))

    # ------------------------------------------------------------- loading

    @classmethod
    def load(cls, path: Path) -> "Trace":
        records = []
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # a partially-flushed final line is normal
        return cls(records)

    @classmethod
    def empty(cls) -> "Trace":
        return cls([])

    # ------------------------------------------------------------- filters

    def tool_calls(self, name: str | None = None, main_only: bool = False) -> list[ToolCall]:
        out = self.calls
        if main_only:
            out = [c for c in out if not c.sidechain]
        if name is not None:
            out = [c for c in out if c.name == name]
        return out

    def count(self, name: str, main_only: bool = False) -> int:
        return len(self.tool_calls(name, main_only=main_only))

    def bash_commands(self, main_only: bool = False) -> list[str]:
        return [c.command for c in self.tool_calls("Bash", main_only=main_only)]

    def ran(self, pattern: str, main_only: bool = False) -> bool:
        return any(re.search(pattern, cmd) for cmd in self.bash_commands(main_only=main_only))

    def ran_git(self, subcommand: str, main_only: bool = False) -> bool:
        """Whether a `git <subcommand>` ran, tolerating global options.

        `git -C /path diff --cached` and `git --no-pager diff --cached` are the
        same act as `git diff --cached`, and an assertion that only matches the
        bare form reports a false violation the first time an agent passes `-C`.
        """
        prefix = r"git\s+(?:(?:-[cC]\s+\S+|--no-pager|--git-dir(?:=|\s+)\S+|--work-tree(?:=|\s+)\S+|-[a-zA-Z])\s+)*"
        return self.ran(prefix + subcommand, main_only=main_only)

    def reads(self, main_only: bool = False) -> list[str]:
        return [c.path for c in self.tool_calls("Read", main_only=main_only) if c.path]

    def subagents(self) -> list[str]:
        return [
            str(c.input.get("subagent_type", "")) for c in self.tool_calls("Task", main_only=True)
        ]

    @property
    def main_turns(self) -> list[str]:
        return [t for side, t in self.turns if not side]

    @property
    def assistant_text(self) -> str:
        return "\n".join(self.main_turns)

    # -------------------------------------------------------------- order

    def first_index(self, predicate) -> int | None:
        for c in self.calls:
            if predicate(c):
                return c.index
        return None

    def happened_before(self, first, second) -> bool | None:
        """True when `first` occurs before `second`; None when either is absent.

        Ordering assertions are how a gate gets tested: "a Review agent ran
        before the commit" is exactly this shape.
        """
        a, b = self.first_index(first), self.first_index(second)
        if a is None or b is None:
            return None
        return a < b

    # ------------------------------------------------------------ metrics

    def questions_per_turn(self) -> list[int]:
        """Count of question sentences in each main-agent turn.

        The bundling regression (`fc60d33`) was invisible in the final artifact
        and obvious here: turns carrying 2-3 questions instead of one.
        """
        counts = []
        for text in self.main_turns:
            body = re.sub(r"```.*?```", "", text, flags=re.S)
            counts.append(len(re.findall(r"\?(?:\s|$|\*)", body)))
        return counts
