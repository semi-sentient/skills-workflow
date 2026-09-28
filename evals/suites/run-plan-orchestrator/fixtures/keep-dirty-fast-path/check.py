"""Issue #21: the dirty-tree fast path at Step 1e.2.

A first run (no tree-state.md, no checked criterion) on a tree dirty only with the
operator's own edits must read working-tree.md alone — branch-and-resume.md's
Step 1e.2 has nothing to do there. The reference-load assertion is what tells the
old routing from the new; the stretch ceiling sits between the two arms' measured
growth. This repo is tiny, so the fixture cannot reproduce live bootstrap numbers —
only the mechanism.
"""
import re

SCRATCH = ".agents/scratch/run-plan/shift-board"
KEEP = ["AGENTS.md", "notes/design draft.md"]


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

    expect.that("triage question asked", dlg is not None and dlg.has_event("asked:dirty_tree"), f"events: {dlg.events if dlg else None}")
    expect.that("Step 2 gate reached", dlg is not None and dlg.has_event("gate:presented"), f"events: {dlg.events if dlg else None}")
    expect.that("no interrupted-phase prompt", dlg is not None and not dlg.has_event("asked:interrupted"), "")

    # --- the routing: working-tree.md alone
    refs = _reference_reads(tr.reads(main_only=True), main_bash)
    expect.info("reference files read by the orchestrator", refs)
    expect.that("working-tree.md read", "working-tree.md" in refs, f"{refs}")
    expect.that("branch-and-resume.md never read (fast path)", "branch-and-resume.md" not in refs, f"{refs}")
    expect.that("human-gate.md never read (no human-form criteria)", "human-gate.md" not in refs, f"{refs}")

    # --- the triage outcome is unchanged: both paths keep-dirty, unquoted, untouched
    state = ctx.read(f"{SCRATCH}/tree-state.md")
    lines = {l.strip() for l in state.splitlines() if l.strip()}
    for p in KEEP:
        expect.that(f"tree-state.md records keep-dirty: {p} (unquoted)", f"keep-dirty: {p}" in lines, state[:300])
    expect.that("tree-state.md records no input", not any(l.startswith("input:") for l in lines), state[:300])
    expect.that("AGENTS.md still carries the operator's edit", "Local note: prefer small commits." in ctx.read("AGENTS.md"), "")
    expect.equals("draft note unchanged", ctx.read("notes/design draft.md"), "Draft: board colours, not for this run.\n")
    status = ctx.sh("git -c core.quotePath=false status --porcelain -uall")
    expect.that("AGENTS.md still dirty", re.search(r"^\s*M AGENTS\.md$", status, re.M) is not None, status[:300])
    expect.that("draft note still untracked", '?? "notes/design draft.md"' in status, status[:300])
    expect.equals("no commit made (the only commit is the scaffold)", ctx.sh("git rev-list --all --count"), "1")
    destructive = [c for c in main_bash if re.search(r"\bgit\s+(?:-\S+\s+)*(reset|stash|clean)\b|\bgit\s+(?:-\S+\s+)*checkout\s+--\s|\brm\s[^;&|]*(AGENTS\.md|notes/)", c)]
    expect.that("no reset / stash / clean / checkout -- / rm of a keep-dirty path", not destructive, f"{destructive[:3]}")

    # --- the yardstick: first turn → end (the Step 2 gate, then a short stop)
    ctxs = tr.context_per_turn()
    if ctxs:
        expect.info("context at the first turn (tokens)", ctxs[0])
        expect.info("bootstrap stretch growth (first turn → end, tokens)", ctxs[-1] - ctxs[0])
        # First compare run (3 reps per arm): main 19,084-19,373, fast path 14,729-15,854.
        expect.at_most("bootstrap stretch growth under the 17K ceiling", ctxs[-1] - ctxs[0], 17_000)
    else:
        expect.that("context per turn recorded", False, "no usage blocks")
    expect.info("main-agent bash calls", len(main_bash))
