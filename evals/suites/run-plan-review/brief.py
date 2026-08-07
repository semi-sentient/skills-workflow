"""Compose a Review brief from the skill version under test.

This is the load-bearing part of the suite. The brief is NOT stored in the
fixture — it is extracted from `references/agent-operations.md` in whichever
skill version the arm materialised, then filled in with the fixture's phase.
Edit the Review role, the adversarial mandate, or the diff instruction and the
prompt this eval sends changes with it. A frozen copy of the brief would
measure a snapshot and tell you nothing about the skill.

Every extraction is mandatory. If agent-operations.md is restructured such that
a block can no longer be found, this raises instead of quietly falling back to a
default — a silently stale brief is worse than a failed run. The one exception is
an ablation arm, which removes a block deliberately; see `_ablating`.

The output contract is deliberately overridden to JSON. The skill specifies a
Markdown verdict table, which is right for a human-facing orchestrator and wrong
for automated grading; the original July-2026 benchmark made the same trade.
What it costs: the real table format goes untested here, so a formatting
regression in the verdict output is invisible to this suite.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

OUTPUT_CONTRACT = """## Output contract

Return ONLY a JSON object as your final message (no code fences, no prose before or after):

{"verdicts":[{"criterion":"<verbatim criterion text>","verdict":"MET"|"NOT_MET"|"NEEDS_RUNTIME","evidence":"<file:line + one-line why | the concrete gap and where the fix belongs | why it cannot be verified statically>"}],"scopeCreep":"<changes in the staged diff outside the File Manifest and Scoped Task, or 'None'>","strongestNonFinding":"<when all criteria are MET: the strongest thing you checked that did NOT pan out>"}
"""


def _section(text: str, heading: str) -> str:
    """Body of the heading whose text matches, up to the next heading of equal depth."""
    pattern = rf"^(#{{1,6}})\s+{re.escape(heading)}\s*$"
    m = re.search(pattern, text, re.M)
    if not m:
        raise RuntimeError(f"agent-operations.md has no heading {heading!r}")
    depth = len(m.group(1))
    rest = text[m.end() :]
    nxt = re.search(rf"^#{{1,{depth}}}\s+", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def _ablating() -> bool:
    """True when the runner has deliberately deleted spans from this skill copy.

    Extraction is strict by default: a restructure that hides a block should fail
    the run rather than quietly send a brief missing a section. An ablation arm
    removes a block on purpose, so under it a missing block is the experiment
    rather than a fault — and only then is omission allowed.
    """
    return os.environ.get("SKILLS_EVAL_ABLATED") == "1"


def _quoted(text: str, must_contain: str, label: str) -> str:
    """The double-quoted span containing a landmark phrase.

    Expands outward from the landmark to the nearest quote character on each
    side rather than pairing quotes left-to-right — a short quoted token
    earlier in the section (e.g. an explicit "None") would otherwise consume
    the target span's opening quote.
    """
    quotes = "\"“”"
    lower = text.lower()
    needle = must_contain.lower()
    start = 0
    while (i := lower.find(needle, start)) != -1:
        open_i = max(text.rfind(q, 0, i) for q in quotes)
        closes = [c for q in quotes if (c := text.find(q, i + len(needle))) != -1]
        if open_i != -1 and closes:
            span = text[open_i + 1 : min(closes)].strip()
            if len(span) >= 20:
                return span
        start = i + len(needle)
    if _ablating():
        return ""
    raise RuntimeError(f"could not extract {label} (no quoted span containing {must_contain!r})")


def compose(skill_dir: Path, *, phase: str, criteria: list[str],
            manifest: list[str], pointers: list[str]) -> str:
    ops = skill_dir / "references" / "agent-operations.md"
    if not ops.is_file():
        raise RuntimeError(f"missing {ops} — cannot compose a Review brief from this skill version")
    text = ops.read_text("utf-8")

    review = _section(text, "Review")
    role_m = re.search(r"^\*\*Role:\*\*\s*(.+)$", review, re.M)
    if not role_m:
        raise RuntimeError("could not extract the Review **Role:** line")
    role = role_m.group(1).strip()

    # The compactness rule (added in c9ff6bb) caps evidence at one line per
    # criterion. It is genuinely absent from versions before that commit, so its
    # absence is a version difference rather than a fault and must not raise —
    # which is also what makes an A/B across that commit measurable here.
    compact_m = re.search(r"^For an all-MET phase.*$", review, re.M)
    compactness = compact_m.group(0).strip() if compact_m else ""

    composition = _section(text, "Review Brief (dedicated composition)")
    mandate = _quoted(composition, "Assume the implementation fails", "the adversarial mandate")
    diff_instruction = _quoted(composition, "staged", "the diff instruction")
    evidence_rule = _quoted(composition, "file:line", "the evidence requirement")

    mandate_block = f"\n{mandate}\n" if mandate else ""
    compactness_block = f"\n{compactness}\n" if compactness else ""
    criteria_block = "\n".join(f"- [ ] {c}" for c in criteria)
    manifest_block = "\n".join(f"- `{f}`" for f in manifest)
    pointers_block = "\n".join(f"- {p}" for p in pointers) if pointers else "- None (first phase)."

    return f"""# Review Brief

You are operating as a **Review** agent in a plan-execution workflow.

**Role:** {role}
{mandate_block}
## Scoped Task (verbatim from the plan)

{phase}

### Acceptance criteria

{criteria_block}

## File Manifest

{manifest_block}

## Prior-phase interface pointers

{pointers_block}

## Diff instruction

{diff_instruction}

{OUTPUT_CONTRACT}
{evidence_rule}
{compactness_block}
Keep each `evidence` value to a single line. Emit the object on one line and
check it is valid JSON before sending — a malformed object cannot be graded.
"""
