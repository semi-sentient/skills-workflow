"""Compose a Review brief from the skill version under test.

This is the load-bearing part of the suite. The brief is NOT stored in the
fixture — it is the skill's own `references/briefs/brief-review.md` template in
whichever version the arm materialised, filled the way the orchestrator's
`rp.sh brief` fills it, with the fixture's phase. Edit the Review role, the
adversarial mandate, or the diff instruction in the template and the prompt
this eval sends changes with it. A frozen copy would measure a snapshot and
tell you nothing about the skill.

Two ways to hand the reviewer its criteria, selected per fixture:

- ``inline`` (the July-2026 benchmark shape): the phase and its criteria are
  pasted into the brief. Used by the original four fixtures so their numbers
  stay comparable with the recorded baseline.
- ``spec``: the criteria are written to a `phase-<n>-spec.md` file in the
  fixture repo, labelled `(C1)…(Cn)` exactly as `rp.sh extract` labels them,
  and the brief points at it — the transport the skill uses in production.
  The graded question becomes whether the reviewer reads the file and returns
  one verdict per label.

Every extraction is mandatory. If the template is restructured such that a
block can no longer be found, this raises instead of quietly falling back —
a silently stale brief is worse than a failed run. The one exception is an
ablation arm, which removes a block deliberately; see `_ablating`.

The output contract is overridden to JSON. The skill routes the evidence table
to a scratch evidence file and returns `C<k>: VERDICT` lines plus findings —
right for a context-lean orchestrator, wrong for automated grading; the
original benchmark made the same trade. What it costs: the real return shape
goes untested here, so a formatting regression in the verdict lines is
invisible to this suite.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

TEMPLATE = Path("references") / "briefs" / "brief-review.md"

# Tripwire phrases: if the evidence-file rewrite below no-ops because the
# template drifted, the leaked directive almost certainly carries one of these.
_FILE_DIRECTIVE_MARKERS = (
    "evidence file",
    "evidence path",
    "{{EVIDENCE_PATH}}",
    "WRITE the full verdict table",
)

OUTPUT_CONTRACT = """## Output contract

Return ONLY a JSON object as your final message (no code fences, no prose before or after):

{"verdicts":[{"criterion":"<the criterion's label if it has one (C1, C2, …), else its verbatim text>","verdict":"MET"|"NOT_MET"|"NEEDS_RUNTIME","evidence":"<file:line + one-line why | the concrete gap and where the fix belongs | why it cannot be verified statically>"}],"scopeCreep":"<changes in the staged diff outside the File Manifest and Scoped Task, or 'None'>","outOfCriteriaDefects":"<defects in the changes that no criterion's wording covers, each with file:line, or 'None'>","weakCriteria":"<criteria satisfiable without the intended behaviour holding, each with one line on why, or 'None'>","strongestNonFinding":"<when all criteria are MET: the strongest thing you checked that did NOT pan out>"}

For every MET verdict, cite `file:line` evidence you actually verified in that verdict's evidence field — a MET without it is unverified. Keep each `evidence` value to a single line. Emit the object on one line and check it is valid JSON before sending — a malformed object cannot be graded.
"""


def _ablating() -> bool:
    """True when the runner has deliberately deleted spans from this skill copy.

    Extraction is strict by default: a restructure that hides a block should fail
    the run rather than quietly send a brief missing a section. An ablation arm
    removes a block on purpose, so under it a missing block is the experiment
    rather than a fault — and only then is omission allowed.
    """
    return os.environ.get("SKILLS_EVAL_ABLATED") == "1"


def _section(text: str, heading: str) -> str:
    """Body of the `## <heading>` section, up to the next `## `."""
    m = re.search(rf"^## {re.escape(heading)}\s*$", text, re.M)
    if not m:
        if _ablating():
            return ""
        raise RuntimeError(f"brief-review.md has no section {heading!r}")
    rest = text[m.end():]
    nxt = re.search(r"^## ", rest, re.M)
    return (rest[: nxt.start()] if nxt else rest).strip()


def _role_paragraph(text: str) -> str:
    """The first body paragraph — the role preamble with the adversarial mandate."""
    body = text.split("\n", 1)[1] if text.startswith("#") else text
    for para in re.split(r"\n\s*\n", body):
        para = para.strip()
        if para.startswith("You are operating as a **Review** agent"):
            return para
    if _ablating():
        return ""
    raise RuntimeError("could not find the Review role paragraph in brief-review.md")


def _fill(text: str, values: dict[str, str]) -> str:
    for key, val in values.items():
        text = text.replace("{{" + key + "}}", val)
    left = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", text)))
    if left:
        raise RuntimeError(f"unfilled placeholders after composing the Review brief: {left}")
    return text


def _write_spec(repo: Path, phase: str, criteria: list[str], phase_id: str) -> Path:
    """The spec file the orchestrator's `rp.sh extract` would write, labelled the same way."""
    spec_dir = repo / ".claude" / "scratch"
    spec_dir.mkdir(parents=True, exist_ok=True)
    spec_path = spec_dir / f"phase-{phase_id}-spec.md"
    labelled = [f"- [ ] (C{i + 1}) {c}" for i, c in enumerate(criteria)]
    spec_path.write_text(
        "<!-- Extracted by run-plan (rp.sh) from the plan file. The (C<k>) labels on the "
        "criteria exist for the return contract; every other character is the plan's own "
        "text. -->\n\n" + phase.strip() + "\n\n### Acceptance criteria\n\n" + "\n".join(labelled) + "\n",
        "utf-8",
    )
    return spec_path


def compose(skill_dir: Path, *, phase: str, criteria: list[str], manifest: list[str],
            pointers: list[str], repo: Path | None = None, transport: str = "inline",
            phase_id: str = "2") -> str:
    tpl = skill_dir / TEMPLATE
    if not tpl.is_file():
        legacy = skill_dir / "references" / "agent-operations.md"
        if legacy.is_file() and "Review Brief (dedicated composition)" in legacy.read_text("utf-8"):
            return _compose_legacy(legacy.read_text("utf-8"), phase=phase, criteria=criteria,
                                   manifest=manifest, pointers=pointers, repo=repo,
                                   transport=transport, phase_id=phase_id)
        raise RuntimeError(f"missing {tpl} — cannot compose a Review brief from this skill version")
    text = tpl.read_text("utf-8")

    role = _role_paragraph(text)
    if "Assume the implementation fails" not in role and not _ablating():
        raise RuntimeError("the Review role paragraph no longer carries the adversarial mandate")
    # The live role grants a sanctioned evidence-file write this eval cannot host
    # (no orchestrator, no scratch dir) — drop the grant, and fail loudly on drift
    # past the rewrite.
    role = role.replace(" The one sanctioned write is your own evidence file, named below.", "")
    if any(s in role for s in _FILE_DIRECTIVE_MARKERS) and not _ablating():
        raise RuntimeError("the Review role still references the evidence file after rewriting — "
                           "update the rewrite in brief.py to match the template")

    diff_instruction = _section(text, "Diff instruction")
    if "git diff --cached" not in diff_instruction and not _ablating():
        raise RuntimeError("the Diff instruction no longer names `git diff --cached`")
    manifest_section = _section(text, "File Manifest")
    pointers_section = _section(text, "Prior-phase interface pointers")

    manifest_block = "\n".join(f"- `{f}`" for f in manifest)
    pointers_block = "\n".join(f"- {p}" for p in pointers) if pointers else "- None (first phase)."
    if transport == "spec":
        if repo is None:
            raise RuntimeError("spec transport needs the fixture repo path")
        spec_path = _write_spec(repo, phase, criteria, phase_id)
        scoped_task = _fill(_section(text, "Scoped Task"), {"SPEC_PATH": str(spec_path), "HUMAN_FORM": "None"})
    elif transport == "inline":
        scoped_task = (f"{phase.strip()}\n\n### Acceptance criteria\n\n" + "\n".join(f"- [ ] {c}" for c in criteria))
    else:
        raise ValueError(f"unknown transport {transport!r}")

    manifest_filled = _fill(manifest_section, {"MANIFEST": manifest_block, "SANCTIONED": "None"})
    pointers_filled = _fill(pointers_section, {"POINTERS": pointers_block})

    return f"""# Review brief — Phase {phase_id}

{role}

## Scoped Task

{scoped_task}

## File Manifest

{manifest_filled}

## Prior-phase interface pointers

{pointers_filled}

## Diff instruction

{diff_instruction}

{OUTPUT_CONTRACT}"""


# ------------------------------------------------------------------ legacy arm
#
# Skill versions before issue #6 (2026-09) have no brief template: the Review
# brief was composed from prose sections in agent-operations.md. Kept so that
# `--compare HEAD` across that boundary still runs the baseline arm — the two
# compositions send the same role, mandate, diff instruction, and evidence rule,
# transported the way each version transported them.


def _legacy_section(text: str, heading: str) -> str:
    pattern = rf"^(#{{1,6}})\s+{re.escape(heading)}\s*$"
    m = re.search(pattern, text, re.M)
    if not m:
        raise RuntimeError(f"agent-operations.md has no heading {heading!r}")
    depth = len(m.group(1))
    rest = text[m.end():]
    nxt = re.search(rf"^#{{1,{depth}}}\s+", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def _legacy_quoted(text: str, must_contain: str, label: str) -> str:
    quotes = "\"“”"
    lower = text.lower()
    needle = must_contain.lower()
    start = 0
    while (i := lower.find(needle, start)) != -1:
        open_i = max(text.rfind(q, 0, i) for q in quotes)
        closes = [c for q in quotes if (c := text.find(q, i + len(needle))) != -1]
        if open_i != -1 and closes:
            span = text[open_i + 1: min(closes)].strip()
            if len(span) >= 20:
                return span
        start = i + len(needle)
    if _ablating():
        return ""
    raise RuntimeError(f"could not extract {label} (no quoted span containing {must_contain!r})")


def _compose_legacy(text: str, *, phase, criteria, manifest, pointers, repo, transport, phase_id) -> str:
    review = _legacy_section(text, "Review")
    role_m = re.search(r"^\*\*Role:\*\*\s*(.+)$", review, re.M)
    if not role_m:
        raise RuntimeError("could not extract the Review **Role:** line")
    role = role_m.group(1).strip().replace(
        " The one sanctioned write is the reviewer's own evidence file (Expected output below).", "")
    composition = _legacy_section(text, "Review Brief (dedicated composition)")
    mandate = _legacy_quoted(composition, "Assume the implementation fails", "the adversarial mandate")
    diff_instruction = _legacy_quoted(composition, "staged", "the diff instruction")
    manifest_block = "\n".join(f"- `{f}`" for f in manifest)
    pointers_block = "\n".join(f"- {p}" for p in pointers) if pointers else "- None (first phase)."
    if transport == "spec":
        if repo is None:
            raise RuntimeError("spec transport needs the fixture repo path")
        spec_path = _write_spec(repo, phase, criteria, phase_id)
        scoped_task = (f"Read `{spec_path}` in full. It is this phase's section of the plan, verbatim, "
                       "with its acceptance criteria labelled `C1…Cn`; judge every labelled criterion.")
    else:
        scoped_task = f"{phase.strip()}\n\n### Acceptance criteria\n\n" + "\n".join(f"- [ ] {c}" for c in criteria)
    mandate_block = f"\n{mandate}\n" if mandate else ""
    return f"""# Review Brief

You are operating as a **Review** agent in a plan-execution workflow.

**Role:** {role}
{mandate_block}
## Scoped Task (verbatim from the plan)

{scoped_task}

## File Manifest

{manifest_block}

## Prior-phase interface pointers

{pointers_block}

## Diff instruction

{diff_instruction}

{OUTPUT_CONTRACT}"""
