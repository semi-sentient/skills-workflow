#!/usr/bin/env python3
"""Deterministic tests for evals/harness/context_tally.py's reference-load count.

A synthetic main-agent transcript reproduces the command shapes live runs used to read
run-plan's references, including the three the 2026-09-27 tally missed (issue #25 §5):
a path held in a shell variable and sliced with `sed -n "$n,$((n+45))p" $F`, a combined
`cat a.md b.md`, a heredoc that names a reference without reading it, and the
`rp.sh section` reader that replaces the hand-written slices.

    ./evals/deterministic/test-context-tally.py      # exit 0 = all passed
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from context_tally import tally  # noqa: E402

REFERENCES_DIR = Path(__file__).resolve().parents[2] / "universal" / "run-plan" / "references"

REF = ".agents/skills/run-plan/references"
CALLS = [
    # (tool, input, result chars)
    ("Read", {"file_path": f"/repo/{REF}/ledger.md"}, 1000),
    ("Bash", {"command": f"git status --porcelain; cat {REF}/working-tree.md"}, 2000),
    # 2026-09-27 rec 336: the path is a variable, the range is shell arithmetic.
    ("Bash", {"command": f'F={REF}/fix-cycles.md && grep -n "^## " $F; n=$(grep -n "^## Composing" $F | cut -d: -f1); sed -n "$n,$((n+45))p" $F'}, 13495),
    # rec 855: the slice start is a variable too.
    ("Bash", {"command": f'F={REF}/agent-operations.md && n=$(grep -n "Scoped Re-review Exceptions" $F | head -1 | cut -d: -f1) && sed -n "$n,$((n+40))p" "$F"'}, 3929),
    # rec 865: an rp.sh call first, then the read through ${F}.
    ("Bash", {"command": f'bash s/rp.sh ledger 5 Code 1 1 1; F="{REF}/agent-operations.md" && sed -n "1,30p" ${{F}}'}, 5793),
    # 2026-09-25 rec 50: one result for two files.
    ("Bash", {"command": f"cat {REF}/branch-and-resume.md {REF}/human-gate.md"}, 24000),
    # The helper's section reader is a read of the file it names.
    ("Bash", {"command": "bash s/rp.sh section fix-cycles.md 'Corrective-pass budget'"}, 4000),
    # Not a read: a heredoc that names a reference.
    ("Bash", {"command": f"cat > s/tree-state.md <<'EOF'\nkeep-dirty: {REF}/completion-templates.md\nEOF"}, 0),
]


def transcript(path: Path) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for i, (tool, inp, n) in enumerate(CALLS):
            tid = f"t{i}"
            fh.write(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": tid, "name": tool, "input": inp}]}}) + "\n")
            fh.write(json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": tid, "content": "x" * n}]}}) + "\n")


def main() -> int:
    passed = failed = 0

    def check(name: str, ok: bool, evidence: object = "") -> None:
        nonlocal passed, failed
        if ok:
            passed += 1
            print(f"  ok   {name}")
        else:
            failed += 1
            print(f"  FAIL {name}\n       {evidence}")

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "t.jsonl"
        transcript(p)
        loads = tally(p)["reference_loads"]
    by = {r["file"]: (r["loads"], r["chars"]) for r in loads["by_file"]}

    check("a Read and a cat of a literal path count", by.get("ledger.md") == (1, 1000) and by.get("working-tree.md") == (1, 2000), by)
    check("a sed slice of a variable-held path and an rp.sh section call both count (rec 336 form)", by.get("fix-cycles.md") == (2, 13495 + 4000), by)
    check("$F, \"$F\" and ${F} all resolve (rec 855 and 865 forms)", by.get("agent-operations.md") == (2, 3929 + 5793), by)
    b, h = (REFERENCES_DIR / "branch-and-resume.md").stat().st_size, (REFERENCES_DIR / "human-gate.md").stat().st_size
    want_b = round(24000 * b / (b + h))
    check("a combined cat splits its result by each file's size on disk",
          by.get("branch-and-resume.md") == (1, want_b) and by.get("human-gate.md") == (1, round(24000 * h / (b + h))), by)
    check("a heredoc naming a reference is not a read", "completion-templates.md" not in by, by)
    check("eight loads in all", loads["count"] == 8, loads)
    check("totals add up", loads["total_chars"] == sum(c for _, c in by.values()), loads)

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
