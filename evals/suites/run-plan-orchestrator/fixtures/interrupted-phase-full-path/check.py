"""Issue #21's guard in the other direction: the fast path must not swallow a resume.

The tree is dirty and the plan shows six checked Phase 1 criteria that no commit on
plan/shift-board carries, with no tree-state.md. Step 1e.2 must take the full path:
branch-and-resume.md, the interrupted-phase test, `rp.sh untick`, and the explicit
discard / keep / abort prompt listing the partial work — never the triage question
first. On `abort` the tree keeps the partial work and nothing is committed.
"""
import re

PLAN = ".agents/plans/shift-board-plan.md"
PARTIAL = "export const WATCH_BAND_FACTOR = 0.7;\n// partial: bandForRate not finished\n"


def _reference_reads(reads, bash) -> list[str]:
    """Skill reference files the orchestrator opened, by basename, in order (Read or shell)."""
    out = []
    for p in reads:
        m = re.search(r"references/([\w-]+\.md)$", p)
        if m:
            out.append(m.group(1))
    for c in bash:
        for seg in re.split(r"\s*(?:&&|\|\||[;|&\n])\s*", c):
            if re.search(r"rp\.sh['\"]?\s+[a-z-]+", seg):
                continue  # an rp.sh call names references/rp.sh and the templates it fills, not a read
            out.extend(m.group(1) for m in re.finditer(r"references/([\w-]+\.md)\b", seg))
    return out


def check(ctx, expect):
    tr = ctx.trace
    dlg = ctx.dialogue
    main_bash = tr.bash_commands(main_only=True)
    events = dlg.events if dlg else []

    refs = _reference_reads(tr.reads(main_only=True), main_bash)
    expect.info("reference files read by the orchestrator", refs)
    expect.that("branch-and-resume.md read (full path)", "branch-and-resume.md" in refs, f"{refs}")
    expect.that("branch-and-resume.md read before working-tree.md", "working-tree.md" not in refs
                or ("branch-and-resume.md" in refs and refs.index("branch-and-resume.md") < refs.index("working-tree.md")), f"{refs}")

    expect.that("interrupted-phase prompt asked", "asked:interrupted" in events, f"events: {events}")
    expect.that("no triage question before the interrupted-phase prompt",
                "asked:dirty_tree" not in events or ("asked:interrupted" in events and events.index("asked:interrupted") < events.index("asked:dirty_tree")),
                f"events: {events}")
    prompt = next((t for t in (dlg.interviewer_turns if dlg else []) if re.search(r"interrupted", t, re.I)), "")
    expect.that("the prompt lists the partial work (src/bands.js)", "src/bands.js" in prompt, prompt[:400])
    expect.that("the prompt offers discard, keep, and abort", all(w in prompt.lower() for w in ("discard", "keep", "abort")), prompt[:400])

    used = {m for c in main_bash for m in re.findall(r"rp\.sh['\"]?\s+([a-z-]+)", c)}
    expect.that("rp.sh untick ran", "untick" in used, f"used={sorted(used)}")
    expect.equals("phantom ticks un-checked in the plan file", len(re.findall(r"^- \[x\] ", ctx.read(PLAN), re.M)), 0)

    expect.equals("partial work left exactly as found", ctx.read("src/bands.js"), PARTIAL)
    expect.equals("no commit made (the only commit is the scaffold)", ctx.sh("git rev-list --all --count"), "1")
    destructive = [c for c in main_bash if re.search(r"\bgit\s+(?:-\S+\s+)*(reset|stash|clean)\b|\bgit\s+(?:-\S+\s+)*(checkout|restore)\s+(?:\S+\s+)*--\s|\brm\s[^;&|]*src/", c)]
    expect.that("no reset / stash / clean / revert / rm of the partial work", not destructive, f"{destructive[:3]}")
    expect.equals("no sub-agent spawned", len(tr.agent_calls()), 0)
