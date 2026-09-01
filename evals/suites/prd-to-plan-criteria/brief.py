"""Compose a plan-review brief from the prd-to-plan version under test.

The brief is NOT stored in the fixture — the Step 6b checklist and the
reviewer's standing instructions are extracted from `SKILL.md` in whichever
skill version the arm materialised, so editing the checklist changes the prompt
this eval sends. A frozen copy would measure a snapshot.

Extraction is strict: if Step 6b or 6a can no longer be found the run fails
rather than quietly sending a brief without them. An ablation arm that deletes
the Criteria verifiability bullet leaves the 6b block itself intact, so no
ablation exemption is needed here.

The output contract is overridden to JSON for deterministic grading — the
skill's own reviewer returns findings as prose for the author to act on.
"""

from __future__ import annotations

import re
from pathlib import Path

OUTPUT_CONTRACT = """## Output contract

Return ONLY a JSON object as your final message (no code fences, no prose before or after):

{"criteria":[{"criterion":"<verbatim criterion text>","status":"OK"|"FLAG","failed":"<the checklist item (and its sub-check, where the item has them) this criterion fails, stated in the checklist's own words; empty when OK>","today":"<evidence you gathered while verifying this criterion, if any, or n/a>","why":"<one line>"}],"designFindings":"<findings under the other checklist items, each with file:line, or 'None'>","strongestNonFinding":"<the strongest thing you checked that did NOT pan out>"}

One row per acceptance criterion, in plan order. `status` is FLAG when the criterion fails any checklist item. Keep every string to a single line, and truncate each `today` value to at most 80 characters — long output must never be pasted whole. Emit the object on one line and check it is valid JSON before sending — a malformed object cannot be graded.
"""


def _between(text: str, start: str, end: str, label: str) -> str:
    i = text.find(start)
    if i == -1:
        raise RuntimeError(f"SKILL.md has no {label} ({start!r} not found)")
    j = text.find(end, i + len(start))
    if j == -1:
        raise RuntimeError(f"SKILL.md: {label} has no terminator {end!r}")
    return text[i:j].strip()


def compose(skill_dir: Path, repo: Path, plan_relpath: str = "plan-draft.md") -> str:
    skill = skill_dir / "SKILL.md"
    if not skill.is_file():
        raise RuntimeError(f"missing {skill} — cannot compose a plan-review brief from this skill version")
    text = skill.read_text("utf-8")

    checklist = _between(text, "**Step 6b — Verification checklist**", "**Step 6c", "Step 6b checklist")
    reviewer_m = re.search(r"Hand it the plan and the Step 6b checklist.*?it does not edit\.\*\*", text, re.S)
    if not reviewer_m:
        raise RuntimeError("could not extract Step 6a's independent-reviewer instruction")
    reviewer_rule = reviewer_m.group(0).replace("**", "")

    return f"""# Plan review brief

You are the **independent reviewer** in a plan-authoring workflow (`prd-to-plan`, Step 6). The
author has drafted an implementation plan and handed you the plan and the verification checklist
— and nothing else. The author's own instructions about you:

> {reviewer_rule}

You read the plan cold, judge every claim and every acceptance criterion on the evidence in this
repository, and report findings. You do not edit any file. Running a read-only shell command that
a criterion states is expected of you; running the project's tests or build is not.

## The plan

Read `{plan_relpath}` in the repository root in full. Its "What to build" and "Architectural
decisions" sections are the author's specification; its acceptance criteria are what `run-plan`'s
Review agent will later hold the implementation to. Nothing in the plan has been implemented yet —
`src/bands.js`, `src/board.js` and `test/bands.test.js` do not exist. A criterion whose command
fails today because its file does not exist yet is expected and sound; judge each criterion by
what it will do AFTER a correct implementation of the plan.

## Verification checklist (verbatim from the skill)

{checklist}

No PRD is attached: treat PRD coverage and i18n completeness as not applicable and say so.

{OUTPUT_CONTRACT}"""
