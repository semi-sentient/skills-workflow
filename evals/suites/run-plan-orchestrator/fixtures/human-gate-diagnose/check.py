"""Human-gate operations (issue #12): a human-form criterion fails for an
environmental reason the repo does not explain.

Graded on the main agent's trajectory (`main_only=True`). The Diagnose agent
legitimately reads the log, the env file, and the source; the orchestrator must
not. The gate stretch is measured as resident-context growth from the last
Phase 1 commit to the final turn — the number that was 121,815 tokens across
four agentless phases in the third live run on #6.
"""
import json
import re

PLAN = ".agents/plans/healthcheck-cutover-plan.md"
SCRATCH = ".agents/scratch/run-plan/healthcheck-cutover"
CONSOLE = re.compile(r"logs/service\.log")
ENV_FILE = re.compile(r"\.env\.local")
HEALTHCHECK = re.compile(r"scripts/healthcheck\.mjs")


def _record_contexts(records):
    """Per main-agent assistant record: (resident context, [tool_use blocks])."""
    out = []
    for rec in records:
        if rec.get("type") != "assistant" or rec.get("isSidechain"):
            continue
        msg = rec.get("message") or {}
        u = msg.get("usage") or {}
        n = int(u.get("cache_read_input_tokens") or 0) + int(u.get("cache_creation_input_tokens") or 0) + int(u.get("input_tokens") or 0)
        content = msg.get("content") or []
        uses = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"] if isinstance(content, list) else []
        out.append((n, uses))
    return out


def check(ctx, expect):
    tr = ctx.trace
    dlg = ctx.dialogue
    main_bash = tr.bash_commands(main_only=True)
    main_reads = tr.reads(main_only=True)
    bash_calls = tr.tool_calls("Bash", main_only=True)
    read_calls = [c for c in tr.tool_calls("Read", main_only=True) if c.path]
    # The `rp.sh brief` fill legitimately carries the human's report and command list
    # (`cat logs/service.log`, `cat .env.local`) as slot values; the read scans below
    # look at shell the orchestrator composed itself, never at rp.sh calls.
    shell = [c for c in main_bash if "rp.sh" not in c]

    # --- the dialogue happened in the scripted shape
    expect.that("execution plan was confirmed by the user", dlg is not None and dlg.has_event("gate:confirmed"),
                f"events: {dlg.events if dlg else None}")
    expect.that("the human reported the gate failure", dlg is not None and dlg.has_event("gate:failed_report"),
                f"events: {dlg.events if dlg else None}")
    expect.that("the human confirmed C1 passed after the recovery", dlg is not None and dlg.has_event("gate:passed"),
                f"events: {dlg.events if dlg else None}")
    expect.that("run reached a final summary", dlg is not None and (dlg.has_event("summary:final") or dlg.stop_reason == "user confirmed"),
                f"stop: {dlg.stop_reason if dlg else None}")
    expect.that("orchestrator never asked the human to paste output or investigate", dlg is not None and not dlg.has_event("asked:paste_output"),
                f"events: {dlg.events if dlg else None}")
    expect.info("dialogue events", dlg.events if dlg else None)
    expect.info("interviewer turns", len(dlg.interviewer_turns) if dlg else 0)

    # --- one Diagnose spawn, briefed from the template
    agent_idx = [(c.index, str(c.input.get("prompt", ""))) for c in tr.agent_calls()]
    diagnose_idx = [i for i, p in agent_idx if re.search(r"\bDiagnose\b", p)]
    debug_idx = [i for i, p in agent_idx if re.search(r"\bDebug\b", p)]
    expect.equals("exactly one Diagnose agent spawned", len(diagnose_idx), 1)
    expect.equals("no Debug agent spawned (the report named no committed file)", len(debug_idx), 0)
    rp = [c for c in main_bash if "rp.sh" in c]
    used = {m for c in rp for m in re.findall(r"rp\.sh['\"]?\s+([a-z-]+)", c)}
    diag_brief_cmds = [c for c in rp if re.search(r"rp\.sh['\"]?\s+brief\s+brief-diagnose\.md", c)]
    expect.equals("rp.sh brief filled brief-diagnose.md once", len(diag_brief_cmds), 1)
    brief_files = ctx.sh(f"ls {SCRATCH} 2>/dev/null | grep -E '^phase-2-brief-diagnose' || true").split()
    expect.that("diagnose brief file written under the phase", bool(brief_files), ctx.sh(f"ls {SCRATCH}"))
    if brief_files:
        brief = ctx.read(f"{SCRATCH}/{brief_files[0]}")
        expect.that("diagnose brief carries the human's report verbatim", "ECONNREFUSED 127.0.0.1:4010" in brief, brief[:300])
        expect.that("diagnose brief carries the closed command list", "cat logs/service.log" in brief and "cat .env.local" in brief, "")
        expect.that("diagnose brief has no unfilled placeholder", "{{" not in brief, "")
        expect.info("diagnose brief bytes", len(brief))
    digest_files = ctx.sh(f"ls {SCRATCH} 2>/dev/null | grep -E '^phase-2-diagnose' || true").split()
    expect.that("digest file written by the Diagnose agent", bool(digest_files), "")
    if digest_files:
        digest = ctx.read(f"{SCRATCH}/{digest_files[0]}")
        expect.that("digest file holds a recommendation and an evidence appendix",
                    re.search(r"(?im)^\W*recommend", digest) is not None and re.search(r"(?im)^\W*##\s*evidence", digest) is not None, digest[:400])
        digest_reads = [p for p in main_reads if re.search(r"phase-2-diagnose", p)] + [c for c in shell if re.search(r"\b(cat|less|head|sed|awk)\b[^|;&\n]*phase-2-diagnose", c)]
        expect.that("orchestrator never read the digest file", not digest_reads, f"{digest_reads[:2]}")
    ledger = ctx.read(f"{SCRATCH}/ledger.md") if ctx.exists(f"{SCRATCH}/ledger.md") else ""
    diag_rows = [l for l in ledger.splitlines() if re.search(r"^\|\s*2\s*\|\s*Research\s*\|", l) and "diagnose" in l.lower()]
    expect.equals("ledger row: phase 2, Mode Research, note diagnose", len(diag_rows), 1)
    expect.info("ledger", ledger.splitlines()[2:])

    # --- the orchestrator did not diagnose
    spawn_at = min(diagnose_idx) if diagnose_idx else None
    console_reads = [p for p in main_reads if CONSOLE.search(p)] + [c for c in shell if CONSOLE.search(c)]
    expect.that("orchestrator never read the console log (Read or shell)", not console_reads, f"{console_reads[:3]}")
    src_reads = [p for p in main_reads if re.search(r"/(src|test|scripts)/", p)]
    expect.that("orchestrator never read source, test, or script files", not src_reads, f"{src_reads[:4]}")
    pre_spawn = [c for c in bash_calls if (spawn_at is None or c.index < spawn_at) and "rp.sh" not in c.command]
    env_before = [c.command for c in pre_spawn if ENV_FILE.search(c.command)]
    env_reads = [c.path for c in read_calls if ENV_FILE.search(c.path) and (spawn_at is None or c.index < spawn_at)]
    expect.that("orchestrator never touched .env.local before the Diagnose spawn", not env_before and not env_reads, f"{(env_before + env_reads)[:3]}")
    check_before = [c.command for c in pre_spawn if HEALTHCHECK.search(c.command)]
    expect.that("orchestrator ran no diagnostic command before the Diagnose spawn", not check_before, f"{check_before[:3]}")
    check_after = [c.command for c in bash_calls if spawn_at is not None and c.index > spawn_at and HEALTHCHECK.search(c.command) and "rp.sh" not in c.command]
    expect.info("delegated health-check runs after the recovery (at the human's direction)", len(check_after))
    expect.equals("no Monitor stream", tr.count("Monitor", main_only=True), 0)
    task_output_reads = [p for p in main_reads if re.search(r"\.output$|/tasks/", p)]
    expect.equals("no background-task output reads", len(task_output_reads), 0)

    # --- the digest was relayed with one recommendation
    turns_after = []
    if dlg is not None:
        seen_report = False
        for t in dlg.turns:
            if t.role == "user" and "gate:failed_report" in t.events:
                seen_report = True
                continue
            if seen_report and t.role == "interviewer":
                turns_after.append(t.text)
    relay = [t for t in turns_after if re.search(r"(?i)\bcause\b", t) and re.search(r"(?i)\brecommend", t)]
    expect.that("digest relayed to the human with a cause and a recommendation",
                bool(relay) and dlg is not None and dlg.has_event("diagnose:relayed"),
                f"events={dlg.events if dlg else None}; turns_after={[t[:120] for t in turns_after[:3]]}")
    expect.that("no options list went out without a recommendation", dlg is not None and not dlg.has_event("diagnose:no_recommendation"), "")

    # --- the recovery is on record in the plan, and the run closed
    plan = ctx.read(PLAN)
    c1 = [l for l in plan.splitlines() if l.startswith("- [") and "healthcheck.mjs" in l]
    expect.that("the human-form criterion carries a gate amendment", bool(c1) and re.search(r"\(gate:", c1[0]) is not None, f"{c1[:1]}")
    expect.that("the amendment names the digest path", bool(c1) and "diagnose" in c1[0], f"{c1[:1]}")
    spec2 = ctx.read(f"{SCRATCH}/phase-2-spec.md") if ctx.exists(f"{SCRATCH}/phase-2-spec.md") else ""
    expect.that("rp.sh extract re-ran after the amendment (spec carries it)", "(gate:" in spec2, spec2[-300:])
    ticked = len(re.findall(r"^- \[x\] ", plan, re.M))
    expect.equals("every acceptance criterion ticked", ticked, 4)
    expect.that("rp.sh tick ticked C1 (no hand edit)", "tick" in used and not any(
        c.path.endswith("healthcheck-cutover-plan.md") and "- [ ]" in str(c.input.get("old_string", "")) and "- [x]" in str(c.input.get("new_string", ""))
        for c in tr.tool_calls("Edit", main_only=True)), f"used={sorted(used)}")
    branch = ctx.sh("git branch --show-current")
    expect.equals("work branch created", branch, "plan/healthcheck-cutover")
    commits = ctx.sh("git rev-list --count main..HEAD")
    expect.that("phase 1 and the checkbox-only gate commit on the branch", commits.strip() in {"2", "3", "4"}, f"{commits} commits")
    expect.that("tests pass at the end", ctx.sh("npm test >/dev/null 2>&1 && echo ok") == "ok", "npm test")
    expect.that("working tree clean at the end", ctx.sh("git status --porcelain") == "", ctx.sh("git status --porcelain")[:200])
    env_now = ctx.read(".env.local") if ctx.exists(".env.local") else ""
    expect.info("recovery applied to .env.local (HEALTH_PORT=4020)", "HEALTH_PORT=4020" in env_now)

    # --- standing invariants from two-phase-node, abbreviated
    plan_reads = [p for p in main_reads if p.endswith("healthcheck-cutover-plan.md")]
    expect.that("orchestrator never Read the plan file", not plan_reads, f"{plan_reads}")
    expect.that("rp.sh init/stage/ledger/brief ran", {"init", "stage", "ledger", "brief"} <= used, f"used={sorted(used)}")
    expect.that("no hand-written git add -A", not any(re.search(r"git\s+add\s+-A", c) for c in main_bash), "")
    review_idx = [i for i, p in agent_idx if re.search(r"\bReview\b", p)]
    commit_idx = sorted([c.index for c in bash_calls if re.search(r"git\s+commit\b", c.command)] + [c.index for c in tr.tool_calls("Skill", main_only=True)])
    expect.that("a review preceded the first commit", bool(review_idx) and bool(commit_idx) and min(review_idx) < min(commit_idx),
                f"review at {review_idx[:3]}, commits at {commit_idx[:3]}")
    briefs = tr.briefs()
    expect.that("every spawn prompt points at a brief file", bool(briefs) and all(re.search(r"brief[-\w]*\.md", b) for b in briefs),
                f"{[b[:80] for b in briefs if not re.search(r'brief[-\w]*\.md', b)][:2]}")
    expect.that("no --no-verify", not any("--no-verify" in c for c in main_bash), "")

    # --- the yardstick: the gate stretch is bounded
    recs = _record_contexts(tr.records)
    ctxs = [n for n, _ in recs if n]
    peak = max(ctxs) if ctxs else 0
    expect.info("peak resident context (tokens)", peak)
    expect.at_most("peak resident context under the sanity ceiling", peak, 200_000)
    # Locate the last Phase 1 commit (a `git commit` Bash call or a Skill call) that
    # precedes the Diagnose spawn, and the spawn itself, by assistant record.
    last_commit_rec = None
    spawn_rec = None
    for ri, (n, uses) in enumerate(recs):
        for b in uses:
            name = b.get("name")
            inp = b.get("input") or {}
            if name in ("Task", "Agent") and re.search(r"\bDiagnose\b", str(inp.get("prompt", ""))) and spawn_rec is None:
                spawn_rec = ri
            if spawn_rec is None and (name == "Skill" or (name == "Bash" and re.search(r"git\s+commit\b", str(inp.get("command", ""))))):
                last_commit_rec = ri
    def ctx_at(ri):
        for n, _ in recs[ri:]:
            if n:
                return n
        return 0
    final_ctx = ctxs[-1] if ctxs else 0
    if last_commit_rec is not None and spawn_rec is not None:
        start = ctx_at(last_commit_rec)
        at_spawn = ctx_at(spawn_rec)
        expect.info("context at last Phase 1 commit (tokens)", start)
        expect.info("context at Diagnose spawn (tokens)", at_spawn)
        expect.info("gate stretch growth: commit → spawn (tokens)", at_spawn - start)
        expect.info("gate stretch growth: spawn → end (tokens)", final_ctx - at_spawn)
        expect.at_most("gate stretch growth (last Phase 1 commit → end of run) under 60K", final_ctx - start, 60_000)
    else:
        expect.that("gate stretch could be located (commit and Diagnose spawn found)", False, f"commit_rec={last_commit_rec} spawn_rec={spawn_rec}")
    expect.info("main-agent bash calls", len(main_bash))
    compactions = sum(
        1 for r in tr.records
        if r.get("type") == "user" and not r.get("isSidechain")
        and (r.get("isCompactSummary") or "continued from a previous conversation" in str((r.get("message") or {}).get("content", "")))
    )
    expect.equals("no compaction", compactions, 0)
