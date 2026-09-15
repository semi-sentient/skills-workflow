"""Mid-run criteria protocol (issue #13): a criterion amended after a reviewer
finding quotes the plan, then a criterion added to a committed phase.

Graded on the main agent's trajectory (`main_only=True`). The invariants are the
ones every live run improvised: no hand-written plan edit (the label-regex and
ticked-anchor failures), `rp.sh amend` / `add-criterion` as the only plan
writers, ticked labels untouched, a full re-review of the reopened phase before
its commit, no `git reset` to separate two phases' work, and the amendment
stretch's resident-context growth recorded and bounded.
"""
import re

PLAN = ".agents/plans/board-lines-plan.md"
PLAN_NAME = "board-lines-plan.md"
# `git -C <path> commit` is the same act as `git commit`; the `-[cC]` argument may not
# start with `-` or the repetition becomes ambiguous (ReDoS, see two-phase-node).
GIT = r"\bgit\s+(?:(?:-[cC]\s+[^-\s]\S*|-\S+)\s+)*"
SCRATCH = ".agents/scratch/run-plan/board-lines"


def _criteria(plan_text: str, phase: str) -> list[str]:
    """Criterion lines of one phase, checkbox stripped, in order."""
    m = re.search(rf"^## Phase {phase}:.*?(?=^## |\Z)", plan_text, re.M | re.S)
    if not m:
        return []
    return [re.sub(r"^- \[[ xX]\] ", "", l) for l in m.group(0).splitlines() if re.match(r"^- \[[ xX]\] ", l)]


def _ticks(plan_text: str, phase: str) -> list[bool]:
    m = re.search(rf"^## Phase {phase}:.*?(?=^## |\Z)", plan_text, re.M | re.S)
    return [l.startswith("- [x]") for l in (m.group(0).splitlines() if m else []) if re.match(r"^- \[[ xX]\] ", l)]


_HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n.*?\n\1\s*(?=\n|$)", re.S)


def _exec(cmd: str) -> str:
    """The command with heredoc bodies removed — a memo written by heredoc that
    *mentions* `rp.sh add-criterion` is not a call to it."""
    return _HEREDOC.sub("<<HEREDOC", cmd)


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
    rp = [_exec(c) for c in main_bash if "rp.sh" in _exec(c)]
    shell = [c for c in main_bash if "rp.sh" not in _exec(c)]
    used = {m for c in rp for m in re.findall(r"rp\.sh['\"]?\s+([a-z-]+)", c)}

    # --- the dialogue happened in the scripted shape
    ev = dlg.events if dlg else None
    expect.that("execution plan was confirmed by the user", dlg is not None and dlg.has_event("gate:confirmed"), f"events: {ev}")
    expect.that("the orchestrator asked the human to decide the 3.4/[amber] contradiction", dlg is not None and dlg.has_event("asked:drift"), f"events: {ev}")
    expect.that("the human answered amend", dlg is not None and dlg.has_event("drift:amend_given"), f"events: {ev}")
    expect.that("the human asked for the new Phase 1 criterion", dlg is not None and dlg.has_event("criterion:add_requested"), f"events: {ev}")
    expect.info("drift question came before Phase 1 was committed (request queued)", dlg is not None and dlg.has_event("drift:asked_before_phase1"))
    expect.that("run reached a final summary", dlg is not None and (dlg.has_event("summary:final") or dlg.stop_reason == "user confirmed"), f"stop: {dlg.stop_reason if dlg else None}")
    expect.that("orchestrator never asked the human to edit the plan or approve pasted plan text", dlg is not None and not dlg.has_event("asked:self_edit"), f"events: {ev}")
    expect.info("dialogue events", ev)
    expect.info("interviewer turns", len(dlg.interviewer_turns) if dlg else 0)

    # --- every plan edit went through rp.sh
    hand_tool_edits = [c for c in tr.tool_calls(main_only=True) if c.name in ("Edit", "Write", "MultiEdit", "NotebookEdit") and c.path.endswith(PLAN_NAME)]
    expect.equals("no Edit/Write of the plan file by the orchestrator", len(hand_tool_edits), 0)
    # Judged on the command with heredoc bodies stripped: a memo that mentions the plan
    # is not an edit of it; `cat > <plan> <<EOF` still is (the redirect alternative).
    write_rx = re.compile(r"\bsed\b[^|;&\n]*\s-i|\btee\b[^|;&\n]*" + re.escape(PLAN_NAME)
                          + r"|\b(cp|mv|install)\b[^|;&\n]*" + re.escape(PLAN_NAME) + r"|>\s*[\"']?\S*" + re.escape(PLAN_NAME) + r"|\bawk\b[^|;&\n]*>|\bed\b\s")
    # An interpreter's script rides in the heredoc body (the live runs' `python3 - <<'PY'`
    # shape), so those are judged on the raw command: interpreter present, plan named anywhere.
    interp_rx = re.compile(r"\bpython3?\b|\bperl\b|\bruby\b|\bnode\b")
    hand_shell_edits = [c for c in shell if (PLAN_NAME in _exec(c) and write_rx.search(_exec(c))) or (PLAN_NAME in c and interp_rx.search(_exec(c)))]
    expect.equals("no hand-written shell edit of the plan (python/heredoc/sed -i/redirect)", len(hand_shell_edits), 0)
    if hand_shell_edits:
        expect.info("hand-written plan edits", [c[:160] for c in hand_shell_edits[:3]])
    amend_cmds = [c for c in rp if re.search(r"rp\.sh['\"]?\s+amend\b", c)]
    add_cmds = [c for c in rp if re.search(r"rp\.sh['\"]?\s+add-criterion\b", c)]
    expect.at_least("rp.sh amend used for the Phase 2 amendment", len(amend_cmds), 1)
    expect.equals("rp.sh add-criterion used once for the Phase 1 criterion", len(add_cmds), 1)
    expect.info("rp.sh amend calls", len(amend_cmds))
    unknown = sorted(used - {"init", "extract", "phases", "criteria", "tick", "untick", "amend", "add-criterion", "ledger", "phase-cost", "stage",
                             "delta", "baselines", "review-path", "evidence", "sync", "drift", "pull", "cleanup", "brief", "wait", "help"})
    expect.info("rp.sh commands that do not exist (guessed)", unknown)
    expect.info("rp.sh commands used", sorted(used))

    # --- the plan: labels stable, suffixes written, everything ticked
    plan = ctx.read(PLAN)
    original = ctx.sh(f"git show main:{PLAN}")
    p1_orig = _criteria(original, "1")
    p1_now = _criteria(plan, "1")
    expect.equals("Phase 1 has exactly one criterion more than it started with", len(p1_now), len(p1_orig) + 1)
    # Labels stable: each original criterion is still at its position (identified by
    # its first backticked identifier); a reworded one carries a suffix from the table.
    SUFFIX = re.compile(r"\((accepted as written|amended mid-run|amended after commit|reopened) — ")
    def ident(c: str) -> str:
        m = re.search(r"`([^`]+)`", c)
        return m.group(1) if m else c[:40]
    misplaced = [(a[:50], b[:50]) for a, b in zip(p1_orig, p1_now) if ident(a) not in b]
    expect.that("Phase 1's original criteria keep their labels (same identifier at each position)", not misplaced, f"{misplaced[:2]}")
    reworded = [b for a, b in zip(p1_orig, p1_now) if a != b]
    expect.that("every reworded Phase 1 criterion carries a suffix from the table", all(SUFFIX.search(b) for b in reworded), f"{[b[-120:] for b in reworded if not SUFFIX.search(b)][:2]}")
    expect.info("Phase 1 criteria reworded after the reopen (beyond the added one)", len(reworded))
    expect.info("plan amendments beyond the two the human decided", max(0, len([c for c in rp if re.search(r"rp\.sh['\"]?\s+amend\b", c)]) - 1))
    new_crit = p1_now[-1] if len(p1_now) > len(p1_orig) else ""
    expect.that("the new criterion is appended last and names RangeError", "RangeError" in new_crit, new_crit[:200])
    expect.that("the new criterion carries the added-mid-run suffix", "(added mid-run" in new_crit, new_crit[:200])
    expect.that("every Phase 1 criterion ticked, the new one included", bool(_ticks(plan, "1")) and all(_ticks(plan, "1")), str(_ticks(plan, "1")))
    p2_now = _criteria(plan, "2")
    expect.equals("Phase 2 still has four criteria (amend rewrote in place)", len(p2_now), 4)
    expect.that("Phase 2 no longer expects 3.4 to render [amber]", not any(re.search(r"3\.4 \[amber\]", c) for c in p2_now), str([c[:120] for c in p2_now if "3.4" in c]))
    expect.that("the amended Phase 2 criterion carries the amended-mid-run suffix", any("(amended mid-run" in c for c in p2_now), str([c[-120:] for c in p2_now if "3.4" in c]))
    expect.that("every Phase 2 criterion ticked", bool(_ticks(plan, "2")) and all(_ticks(plan, "2")), str(_ticks(plan, "2")))
    spec1 = ctx.read(f"{SCRATCH}/phase-1-spec.md") if ctx.exists(f"{SCRATCH}/phase-1-spec.md") else ""
    spec2 = ctx.read(f"{SCRATCH}/phase-2-spec.md") if ctx.exists(f"{SCRATCH}/phase-2-spec.md") else ""
    expect.that("phase-1-spec.md carries the new criterion as C7", re.search(r"^- \[[ x]\] \(C7\) .*RangeError", spec1, re.M) is not None, spec1[-300:])
    expect.that("phase-2-spec.md carries the amendment (re-extracted)", "amended mid-run" in spec2, spec2[-300:])

    # --- no index surgery
    exec_bash = [_exec(c) for c in main_bash]
    resets = [c for c in exec_bash if re.search(GIT + r"(reset|stash)\b", c) or re.search(GIT + r"restore\s+--staged", c)]
    expect.equals("no git reset / stash / restore --staged", len(resets), 0)
    if resets:
        expect.info("index surgery commands", [c[:160] for c in resets[:3]])
    hand_adds = [c for c in exec_bash if re.search(GIT + r"add\b", c)]
    expect.equals("no hand-written git add (rp.sh stage only)", len(hand_adds), 0)

    # --- the reopened phase: Code spawn, then a FULL review, then its commit
    agent_idx = [(c.index, str(c.input.get("prompt", ""))) for c in tr.agent_calls()]
    add_idx = min((c.index for c in bash_calls if re.search(r"rp\.sh['\"]?\s+add-criterion\b", _exec(c.command))), default=None)
    commit_idx = sorted([c.index for c in bash_calls if re.search(GIT + r"commit\b", _exec(c.command))] + [c.index for c in tr.tool_calls("Skill", main_only=True)])
    p1_code_after = [i for i, p in agent_idx if add_idx is not None and i > add_idx and re.search(r"\bCode\b", p) and re.search(r"Phase 1\b", p)]
    p1_review_after = [i for i, p in agent_idx if add_idx is not None and i > add_idx and re.search(r"\bReview\b", p) and re.search(r"Phase 1\b", p)]
    full_brief_after = [c for c in bash_calls if add_idx is not None and c.index > add_idx and re.search(r"rp\.sh['\"]?\s+brief\s+brief-review\.md\s+\S*phase-1-brief-review", c.command)]
    scoped_brief_after = [c for c in bash_calls if add_idx is not None and c.index > add_idx and re.search(r"rp\.sh['\"]?\s+brief\s+brief-rereview\.md\s+\S*phase-1-", c.command)]
    code_brief_after = [c for c in bash_calls if add_idx is not None and c.index > add_idx and re.search(r"rp\.sh['\"]?\s+brief\s+brief-code\.md\s+\S*phase-1-brief-code", c.command)]
    expect.that("a Code agent for Phase 1 spawned after add-criterion", bool(p1_code_after), f"add at {add_idx}, code spawns {[i for i, p in agent_idx if 'Code' in p]}")
    expect.that("the reopen's Code brief did not overwrite phase-1-brief-code.md", bool(code_brief_after) and not any(re.search(r"\sphase-1-brief-code\.md\s", c.command + " ") for c in code_brief_after),
                str([c.command[:120] for c in code_brief_after[:2]]))
    expect.that("a FULL Review (brief-review.md) for Phase 1 was composed after add-criterion", bool(full_brief_after), f"full={len(full_brief_after)} scoped={len(scoped_brief_after)}")
    expect.equals("no scoped re-review of the reopened phase", len(scoped_brief_after), 0)
    expect.that("a Review agent for Phase 1 spawned after add-criterion", bool(p1_review_after), f"review spawns after add: {p1_review_after}")
    last_commit = max(commit_idx) if commit_idx else None
    expect.that("the reopened phase's review preceded its commit (a commit followed the Phase 1 re-review)",
                bool(p1_review_after) and last_commit is not None and any(k > min(p1_review_after) for k in commit_idx),
                f"reviews {p1_review_after}, commits {commit_idx}")
    expect.that("Code preceded Review for the reopen", bool(p1_code_after) and bool(p1_review_after) and min(p1_code_after) < min(p1_review_after), "")
    review_files = ctx.sh(f"ls {SCRATCH} 2>/dev/null | grep -E '^phase-1-review(-[0-9]+)?\\.md$' || true").split()
    expect.at_least("Phase 1 has at least two evidence files (first review + reopen review)", len(review_files), 2)
    ledger = ctx.read(f"{SCRATCH}/ledger.md") if ctx.exists(f"{SCRATCH}/ledger.md") else ""
    p1_rows = [l for l in ledger.splitlines() if re.match(r"^\|\s*1\s*\|", l)]
    reopened_rows = [l for l in p1_rows if re.search(r"(?i)reopened", l)]
    expect.at_least("ledger rows for Phase 1 note the reopen", len(reopened_rows), 1)
    expect.at_least("Phase 1 has two Code rows (original + reopen)", len([l for l in p1_rows if re.match(r"^\|\s*1\s*\|\s*Code\s*\|", l)]), 2)
    expect.info("ledger", ledger.splitlines()[2:])
    expect.info("tracker showed ▶ Reopened", any("▶ Reopened" in t for t in tr.main_turns))
    # The Phase 2 amendment: the phase was in flight, so its next review was full too.
    amend_idx = min((c.index for c in bash_calls if re.search(r"rp\.sh['\"]?\s+amend\b", _exec(c.command))), default=None)
    p2_review_after_amend = [i for i, p in agent_idx if amend_idx is not None and i > amend_idx and re.search(r"\bReview\b", p) and re.search(r"Phase 2\b", p)]
    expect.that("Phase 2 was re-reviewed after its criterion was amended", bool(p2_review_after_amend), f"amend at {amend_idx}, phase-2 reviews after: {p2_review_after_amend}")

    # --- the run closed
    branch = ctx.sh("git branch --show-current")
    expect.equals("work branch created", branch, "plan/board-lines")
    commits = ctx.sh("git rev-list --count main..HEAD").strip()
    expect.that("three phase commits (1, 2, 1 reopened), checkbox-only commits tolerated", commits in {"3", "4", "5"}, f"{commits} commits")
    expect.that("tests pass at the end", ctx.sh("npm test >/dev/null 2>&1 && echo ok") == "ok", "npm test")
    expect.that("the RangeError is implemented", ctx.sh("node -e \"import('./src/bands.js').then(m => { try { m.bandForRate(1, 0); console.log('no-throw') } catch (e) { console.log(e.constructor.name) } })\"").strip() == "RangeError", "")
    expect.that("working tree clean at the end", ctx.sh("git status --porcelain") == "", ctx.sh("git status --porcelain")[:200])

    # --- standing invariants, abbreviated from two-phase-node
    plan_reads = [p for p in main_reads if p.endswith(PLAN_NAME)]
    expect.that("orchestrator never Read the plan file", not plan_reads, f"{plan_reads}")
    plan_dumps = [c for c in shell if PLAN_NAME in c and re.search(r"\b(cat|less|awk)\b", c)]
    expect.that("orchestrator never dumped the plan file in shell", not plan_dumps, f"{plan_dumps[:2]}")
    src_reads = [p for p in main_reads if re.search(r"/(src|test)/", p)]
    expect.that("orchestrator never read source or test files", not src_reads, f"{src_reads[:4]}")
    expect.that("rp.sh init/stage/tick/ledger/brief/review-path ran", {"init", "stage", "tick", "ledger", "brief", "review-path"} <= used, f"used={sorted(used)}")
    review_idx = [i for i, p in agent_idx if re.search(r"\bReview\b", p)]
    expect.that("a review preceded the first commit", bool(review_idx) and bool(commit_idx) and min(review_idx) < min(commit_idx), f"review at {review_idx[:3]}, commits at {commit_idx[:3]}")
    briefs = tr.briefs()
    expect.that("every spawn prompt points at a brief file", bool(briefs) and all(re.search(r"brief[-\w]*\.md", b) for b in briefs), f"{[b[:80] for b in briefs if not re.search(r'brief[-\w]*\.md', b)][:2]}")
    expect.that("no --no-verify", not any("--no-verify" in c for c in main_bash), "")

    # --- the yardstick: the amendment stretch is bounded
    recs = _record_contexts(tr.records)
    ctxs = [n for n, _ in recs if n]
    peak = max(ctxs) if ctxs else 0
    expect.info("peak resident context (tokens)", peak)
    expect.at_most("peak resident context under the sanity ceiling", peak, 200_000)
    # Stretch: from the assistant record carrying the first `rp.sh amend`/`add-criterion`
    # call to the record carrying the first commit after the reopened phase's re-review —
    # everything the two amendments caused (the drift question's own text lands a record
    # or two earlier and is not counted; the commit-skill diff reads are).
    first_amend_rec = None
    add_rec = None
    p1_review_rec = None
    last_commit_rec = None   # the first commit after the reopened phase's re-review
    for ri, (n, uses) in enumerate(recs):
        for b in uses:
            name = b.get("name")
            inp = b.get("input") or {}
            cmd = str(inp.get("command", ""))
            if first_amend_rec is None and name == "Bash" and re.search(r"rp\.sh['\"]?\s+(amend|add-criterion)\b", _exec(cmd)):
                first_amend_rec = ri
            if add_rec is None and name == "Bash" and re.search(r"rp\.sh['\"]?\s+add-criterion\b", _exec(cmd)):
                add_rec = ri
            if add_rec is not None and p1_review_rec is None and name in ("Task", "Agent") and re.search(r"\bReview\b", str(inp.get("prompt", ""))) and re.search(r"Phase 1\b", str(inp.get("prompt", ""))):
                p1_review_rec = ri
            if p1_review_rec is not None and ri > p1_review_rec and last_commit_rec is None and (name == "Skill" or (name == "Bash" and re.search(GIT + r"commit\b", _exec(cmd)))):
                last_commit_rec = ri

    def ctx_at(ri):
        for n, _ in recs[ri:]:
            if n:
                return n
        return 0

    if first_amend_rec is not None and last_commit_rec is not None and last_commit_rec >= first_amend_rec:
        start, end = ctx_at(first_amend_rec), ctx_at(last_commit_rec)
        expect.info("context at first amend/add-criterion call (tokens)", start)
        expect.info("context at the reopened phase's commit (tokens)", end)
        expect.info("amendment stretch growth (tokens)", end - start)
        # First calibration ceiling: two Code spawns, two full reviews, two commit-skill
        # diff reads and the human exchange. The live web run spent 32K on four hand
        # edits alone. Tighten once a baseline exists.
        expect.at_most("amendment stretch growth (first amend → reopened phase's commit) under 90K", end - start, 90_000)
    else:
        expect.that("amendment stretch could be located (amend call, Phase 1 re-review, and its commit found)", False, f"amend_rec={first_amend_rec} review_rec={p1_review_rec} commit_rec={last_commit_rec}")
    expect.info("main-agent bash calls", len(main_bash))
    compactions = sum(
        1 for r in tr.records
        if r.get("type") == "user" and not r.get("isSidechain")
        and (r.get("isCompactSummary") or "continued from a previous conversation" in str((r.get("message") or {}).get("content", "")))
    )
    expect.equals("no compaction", compactions, 0)
