"""Orchestrator-level invariants for issue #6 (context diet).

Everything here is graded on the main agent's trajectory (`main_only=True`);
the sub-agents legitimately read the plan, the specs, and the diffs.
"""
import re

PLAN = ".agents/plans/shift-board-plan.md"
SCRATCH = ".agents/scratch/run-plan/shift-board"


def check(ctx, expect):
    tr = ctx.trace
    dlg = ctx.dialogue
    main_bash = tr.bash_commands(main_only=True)
    main_reads = tr.reads(main_only=True)

    # --- the run happened
    expect.that("execution plan was confirmed by the user", dlg is not None and dlg.has_event("gate:confirmed"),
                f"events: {dlg.events if dlg else None}")
    expect.that("run reached a final summary", dlg is not None and (dlg.has_event("summary:final") or dlg.stop_reason == "user confirmed"),
                f"stop: {dlg.stop_reason if dlg else None}")
    plan = ctx.read(PLAN)
    ticked = len(re.findall(r"^- \[x\] ", plan, re.M))
    expect.equals("every acceptance criterion ticked", ticked, 10)
    branch = ctx.sh("git branch --show-current")
    expect.equals("work branch created", branch, "plan/shift-board")
    commits = ctx.sh("git rev-list --count main..HEAD")
    expect.that("two phase commits on the branch", commits.strip() in {"2", "3"}, f"{commits} commits")
    expect.that("tests pass at the end", ctx.sh("npm test >/dev/null 2>&1 && echo ok") == "ok", "npm test")
    expect.that("working tree clean at the end (scratch is ignored)", ctx.sh("git status --porcelain") == "", ctx.sh("git status --porcelain")[:200])

    # --- P3: the orchestrator reads the index, not the plan
    plan_reads = [p for p in main_reads if p.endswith(PLAN) or p.endswith("shift-board-plan.md")]
    # A bulk dump: cat/less/awk/head of the plan, or a `sed -n` range of 20+ lines or
    # to end-of-file. A short `sed -n '1,4p'` to confirm an amendment edit is not one.
    def dumps_plan(c: str) -> bool:
        for seg in re.split(r"\s*(?:&&|\|\||;|\|)\s*", c):
            if "shift-board-plan.md" not in seg:
                continue
            if re.search(r"\b(cat|less|awk)\b", seg):
                return True
            m = re.search(r"\bhead\b(?:\s+-n?\s*(\d+))?", seg)
            if m and (m.group(1) is None or int(m.group(1)) >= 20):
                return True
            m = re.search(r"\bsed\s+-n\s+'?(\d+),(\d+|\$)p", seg)
            if m and (m.group(2) == "$" or int(m.group(2)) - int(m.group(1)) >= 19):
                return True
            if re.search(r"\bsed\s+-n\s+'?p'?", seg):
                return True
        return False

    plan_cats = [c for c in main_bash if dumps_plan(c)]
    expect.that("orchestrator never Read the plan file", not plan_reads, f"{plan_reads}")
    expect.that("orchestrator never dumped the plan file in shell", not plan_cats, f"{plan_cats[:3]}")
    expect.that("orchestrator read plan-index.md", any(p.endswith("plan-index.md") for p in main_reads)
                or any("plan-index.md" in c for c in main_bash), f"reads: {main_reads[:6]}")
    spec_reads = [p for p in main_reads if re.search(r"phase-\d+[A-Za-z]?-spec\.md$", p)]
    expect.info("spec files read by the orchestrator", len(spec_reads))
    src_reads = [p for p in main_reads if re.search(r"/(src|test)/", p)]
    expect.that("orchestrator never read source or test files", not src_reads, f"{src_reads[:4]}")
    # A diff read is sanctioned only inside the commit fallback: the `commit` skill
    # (a Skill tool call) reads `git diff --cached` itself, up to the commit it makes.
    bash_calls = tr.tool_calls("Bash", main_only=True)
    skill_idx = sorted(c.index for c in tr.tool_calls("Skill", main_only=True))
    commit_bash_idx = sorted(c.index for c in bash_calls if re.search(r"git\s+(?:-\S+\s+)*commit\b", c.command))
    diff_rx = re.compile(r"\bgit\s+(?:(?:-[cC]\s+\S+|--no-pager|-\S+)\s+)*diff\b(?![^|;&]*--(?:quiet|name-only|name-status|stat|numstat)\b)")

    def in_fallback(i: int) -> bool:
        prior = [s for s in skill_idx if s < i]
        if not prior:
            return False
        s = prior[-1]
        return not any(s < k < i for k in commit_bash_idx)

    diff_reads = [c.command for c in bash_calls if diff_rx.search(c.command) and not in_fallback(c.index)]
    expect.that("orchestrator never read a diff outside the commit fallback", not diff_reads, f"{diff_reads[:3]}")
    expect.info("commit-skill fallbacks", len(skill_idx))

    # --- P5(d): housekeeping goes through rp.sh
    rp = [c for c in main_bash if "rp.sh" in c]
    used = {m for c in rp for m in re.findall(r"rp\.sh['\"]?\s+([a-z-]+)", c)}
    expect.that("rp.sh init ran", "init" in used, f"rp.sh commands: {sorted(used)}")
    expect.that("rp.sh stage ran (no hand-written git add -A)", "stage" in used and not any(re.search(r"git\s+add\s+-A", c) for c in main_bash),
                f"used={sorted(used)} hand-adds={[c for c in main_bash if 'git add' in c][:3]}")
    tick_edits = [c for c in tr.tool_calls("Edit", main_only=True)
                  if c.path.endswith("shift-board-plan.md")
                  and "- [ ]" in str(c.input.get("old_string", "")) and "- [x]" in str(c.input.get("new_string", ""))]
    expect.that("rp.sh tick ran (no hand-ticking via Edit)", "tick" in used and not tick_edits,
                f"used={sorted(used)} hand-ticks={len(tick_edits)}")
    unknown = sorted(used - {"init", "extract", "phases", "criteria", "tick", "untick", "ledger", "phase-cost", "stage",
                             "delta", "baselines", "review-path", "evidence", "sync", "drift", "pull", "cleanup", "brief", "help"})
    expect.info("rp.sh commands that do not exist (guessed)", unknown)
    expect.that("rp.sh ledger ran", "ledger" in used, f"used={sorted(used)}")
    expect.that("rp.sh brief composed the briefs", "brief" in used, f"used={sorted(used)}")
    expect.that("rp.sh review-path resolved evidence paths", "review-path" in used, f"used={sorted(used)}")
    expect.info("rp.sh commands used", sorted(used))
    expect.that("phase spec files exist", ctx.exists(f"{SCRATCH}/phase-1-spec.md") and ctx.exists(f"{SCRATCH}/phase-2-spec.md"), "")
    ledger = ctx.read(f"{SCRATCH}/ledger.md")
    expect.at_least("ledger rows recorded", len([l for l in ledger.splitlines() if l.startswith("| ") and not l.startswith("| Phase") and not l.startswith("| --")]), 4)
    expect.that("evidence files written by the reviewers", ctx.exists(f"{SCRATCH}/phase-1-review.md") and ctx.exists(f"{SCRATCH}/phase-2-review.md"), "")

    # --- P2: briefs are pointers, not payloads
    briefs = tr.briefs()
    expect.at_least("sub-agents spawned", len(briefs), 4)
    if briefs:
        expect.info("brief sizes (chars)", [len(b) for b in briefs])
        expect.at_most("largest brief (chars)", max(len(b) for b in briefs), 3000)
        expect.at_most("mean brief (chars)", sum(len(b) for b in briefs) // len(briefs), 1500)
        brief_rx = re.compile(r"brief[-\w]*\.md")
        expect.that("every brief points at a brief file", all(brief_rx.search(b) for b in briefs),
                    f"{[b[:80] for b in briefs if not brief_rx.search(b)][:2]}")
        pasted = [b for b in briefs if "bandForRate(rate, target)" in b or "renderBoard(stations, target)" in b]
        expect.that("no brief pastes acceptance criteria", not pasted, f"{len(pasted)} briefs carry criterion text")
    brief_files = ctx.sh(f"ls {SCRATCH} | grep -c brief") or "0"
    expect.at_least("brief files written", int(brief_files.strip() or 0), 4)
    # The spawn prompts above are pointers; the brief bytes the orchestrator actually
    # emitted are the `rp.sh brief` commands (slot values) and any heredoc brief.
    authored = tr.authored_briefs()
    expect.at_least("briefs authored (rp.sh brief or heredoc)", len(authored), 4)
    if authored:
        sizes = [n for _, n in authored]
        expect.info("authored brief sizes (chars)", sizes)
        expect.at_most("mean authored brief (chars)", sum(sizes) // len(sizes), 4000)
        expect.at_most("largest authored brief (chars)", max(sizes), 8000)
        expect.equals("no hand-written brief files (every brief comes from a template)", sum(1 for k, _ in authored if k == "heredoc"), 0)

    # --- the gate held: a review before each commit, review never sees the implementer summary
    agent_idx = [(c.index, str(c.input.get("prompt", ""))) for c in tr.agent_calls()]
    review_idx = [i for i, p in agent_idx if re.search(r"\bReview\b", p)]
    code_idx = [i for i, p in agent_idx if re.search(r"\bCode\b", p)]
    commit_idx = [c.index for c in tr.tool_calls("Bash", main_only=True) if re.search(r"git\s+commit\b", c.command)]
    skill_commit_idx = [c.index for c in tr.tool_calls("Skill", main_only=True)]
    commits_all = sorted(commit_idx + skill_commit_idx)
    expect.at_least("review agents spawned", len(review_idx), 2)
    expect.at_least("code agents spawned", len(code_idx), 2)
    expect.that("a review preceded the first commit", bool(review_idx) and bool(commits_all) and min(review_idx) < min(commits_all),
                f"review at {review_idx[:3]}, commits at {commits_all[:3]}")
    expect.that("each commit followed a review", all(any(r < k for r in review_idx) for k in commits_all), "")
    expect.that("no review brief carries a status summary", not any("STATUS:" in p for _, p in agent_idx if re.search(r"\bReview\b", p)), "")
    expect.that("no --no-verify", not any("--no-verify" in c for c in main_bash), "")

    # --- the yardstick
    ctxs = tr.context_per_turn()
    peak = max(ctxs) if ctxs else 0
    expect.info("main-agent assistant turns", len(tr.main_turns))
    expect.info("main-agent bash calls", len(main_bash))
    expect.info("peak resident context (tokens)", peak)
    expect.info("final resident context (tokens)", ctxs[-1] if ctxs else 0)
    expect.at_most("peak resident context under the sanity ceiling", peak, 200_000)
    compactions = sum(
        1 for r in tr.records
        if r.get("type") == "user" and not r.get("isSidechain")
        and (r.get("isCompactSummary") or "continued from a previous conversation" in str((r.get("message") or {}).get("content", "")))
    )
    expect.info("compactions", compactions)
    expect.equals("no compaction", compactions, 0)
