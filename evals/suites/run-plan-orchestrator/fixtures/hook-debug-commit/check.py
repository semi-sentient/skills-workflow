"""Issue #24: after a hook-fix Debug agent changes code, the phase message file is stale.

The orchestrator must delete it (`rp.sh cleanup`) and commit through the `commit`
skill, never with a hand-written `git commit -F` of the file — the shortcut sitevue.web
#397 took. Graded on the main agent's trajectory (`main_only=True`).
"""
import re

from harness.trace import _HEREDOC_BRIEF, _RP_BRIEF, msg_file_edits, strip_heredocs

PLAN = ".agents/plans/shift-bands-plan.md"
SCRATCH = ".agents/scratch/run-plan/shift-bands"
SPDX = "// SPDX-License-Identifier: MIT"

# `-C <dir>` takes an argument; the `[^-\s]` keeps the repetition unambiguous (no ReDoS).
_COMMIT = re.compile(r"\bgit\s+(?:(?:-[cC]\s+[^-\s]\S*|-\S+)\s+)*commit\b")
# Only the phase message file: the commit skill may itself pass a message with -F.
_STALE_F = re.compile(r"(?:\s-[a-zA-Z]*F\s*|\s--file[=\s])\S*phase-[\w-]+-commit-msg\.md")
_BRIEF_FILE = re.compile(r"([\w.-]*brief[\w.-]*\.md)")
_exec = strip_heredocs  # a heredoc that mentions `git commit -F` is not a call



def check(ctx, expect):
    tr = ctx.trace
    dlg = ctx.dialogue
    bash = tr.tool_calls("Bash", main_only=True)
    main_bash = [c.command for c in bash]

    # --- the run happened
    expect.that("execution plan was confirmed by the user", dlg is not None and dlg.has_event("gate:confirmed"),
                f"events: {dlg.events if dlg else None}")
    expect.that("run reached a final summary", dlg is not None and (dlg.has_event("summary:final") or dlg.stop_reason == "user confirmed"),
                f"stop: {dlg.stop_reason if dlg else None}")
    expect.equals("work branch created", ctx.sh("git branch --show-current"), "plan/shift-bands")
    expect.equals("one phase commit on the branch", ctx.sh("git rev-list --count main..HEAD").strip(), "1")
    expect.equals("the committed bands.js carries the header the hook requires",
                  ctx.sh("git show HEAD:src/bands.js 2>/dev/null | head -n 1"), SPDX)
    expect.that("no --no-verify", not any("--no-verify" in _exec(c) for c in main_bash), "")
    edits = msg_file_edits(tr)
    expect.that("orchestrator never edited a commit-message file (fence strip aside)", not edits, f"{edits[:2]}")

    # --- the path under test: hook rejection → Debug fix → cleanup → commit skill
    agents = tr.agent_calls()
    # The hook-fix Debug is the first Debug spawned after a commit attempt. An earlier
    # Debug (a blocking failure before review) is not the path under test.
    first_commit = next((c.index for c in bash if _COMMIT.search(_exec(c.command))), None)
    debug_idx = [c.index for c in agents if re.search(r"\bDebug\b", str(c.input.get("prompt", "")))
                 and first_commit is not None and c.index > first_commit]
    # A rep where an agent learned the header rule (research read the hook) never rejects:
    # it fails here, labelled as the fixture's precondition, not as orchestrator conduct.
    expect.info("hook never rejected (unforced rep)", first_commit is not None and not debug_idx
                and ctx.sh("git show HEAD:src/bands.js 2>/dev/null | head -n 1") == SPDX)
    expect.that("fixture precondition: the hook rejected a commit and a Debug agent was spawned for it",
                bool(debug_idx), f"{len(agents)} spawns, first commit at {first_commit}")
    if not debug_idx:
        return
    d = debug_idx[0]
    expect.info("git commit attempts before the Debug spawn", sum(1 for c in bash if c.index < d and _COMMIT.search(_exec(c.command))))
    # A later Code fix cycle (a corrective pass the post-Debug re-review drew) legitimately
    # re-authors the message file, after which the fast path is correct again: the window
    # under test closes at the next Code spawn.
    end = next((c.index for c in agents if c.index > d and re.search(r"\bCode agent for\b|brief-code", str(c.input.get("prompt", "")))), float("inf"))
    expect.info("a Code fix cycle followed the Debug fix (window closes there)", end != float("inf"))
    after = [c for c in bash if d < c.index < end]
    skills = [c.index for c in tr.tool_calls("Skill", main_only=True)
              if d < c.index < end and str(c.input.get("skill", "")).split(":")[-1] == "commit"]
    cleanups = [c.index for c in after if re.search(r"rp\.sh['\"]?\s+cleanup\b", _exec(c.command))]
    # Only a Code agent (a sidechain, which closes the window) may re-author the file; an
    # orchestrator write of it before a -F is a hand-written commit, so no exemption here.
    stale = [c.command for c in after if _COMMIT.search(_exec(c.command)) and _STALE_F.search(_exec(c.command))]
    expect.that("no git commit -F of the message file after the Debug fix", not stale, f"{stale[:2]}")
    # Step 4 item 4's cleanup is "that turn": before the post-Debug re-review, so neither a retry's
    # default-revert cleanup nor item 7's post-commit one can stand in for it
    review_after = next((c.index for c in agents if c.index > d and re.search(r"\bReview\b", str(c.input.get("prompt", "")))), end)
    first_post = min([k for k in skills] + [c.index for c in after if _COMMIT.search(_exec(c.command))], default=float("inf"))
    expect.that("a fresh Review followed the Debug fix before the commit (Step 4 item 5's invariant)",
                review_after != end and review_after < first_post, f"re-review at {review_after}, commit at {first_post}")
    expect.that("rp.sh cleanup ran after the Debug fix, before the re-review",
                any(k < review_after for k in cleanups), f"cleanups {cleanups[:3]}, re-review at {review_after}")
    if end == float("inf"):
        expect.that("the commit skill ran after the Debug fix", bool(skills), "")
    else:  # the later Code agent re-authored the file; the fast path is then correct
        expect.info("commit skill calls between the Debug fix and the next Code spawn", len(skills))
    expect.info("git commit -F through a variable after the Debug fix (unprovable, inspect by hand)",
                [c.command[:120] for c in after if _COMMIT.search(_exec(c.command)) and re.search(r"\s-[a-zA-Z]*F\s*[\"']?\$", c.command)])

    # --- issue §3: NEEDS-RUNTIME is carried through rp.sh carry — when the last review said so
    carried = ctx.read(f"{SCRATCH}/carried-findings.md") if ctx.exists(f"{SCRATCH}/carried-findings.md") else ""
    evidence = sorted(ctx.sh(f"ls {SCRATCH}/phase-1-review*.md 2>/dev/null").split(), key=lambda p: (len(p), p))
    # Newest file holding a C5 verdict: a scoped re-review re-judges only its trigger criteria.
    c5 = re.compile(r"\bC5\b\W*\|?\s*(MET|NOT MET|NEEDS[-_ ]RUNTIME|HUMAN-GATE)")
    verdict = next((m for m in (c5.search(ctx.read(p)) for p in reversed(evidence)) if m), None)
    expect.info("latest C5 verdict", verdict.group(1) if verdict else None)
    expect.that("fixture precondition: a C5 verdict is readable from the evidence files", verdict is not None, f"{evidence}")
    if verdict and re.fullmatch(r"NEEDS[-_ ]RUNTIME", verdict.group(1)):
        expect.that("the timing criterion was carried as NEEDS-RUNTIME", bool(re.search(r"NEEDS-RUNTIME C5\b", carried)),
                    carried[:200] or "no carried-findings.md")
        landed = min([c.index for c in tr.tool_calls("Skill", main_only=True)
                      if c.index > d and str(c.input.get("skill", "")).split(":")[-1] == "commit"]
                     + [c.index for c in bash if c.index > d and _COMMIT.search(_exec(c.command))], default=None)
        expect.that("the C5 carry ran after the post-Debug commit (item 7 timing, not at a tick)",
                    landed is not None and any(c.index >= landed and re.search(r"rp\.sh['\"]?\s+carry\b", _exec(c.command))
                                               and ("NEEDS-RUNTIME C5" in c.command or "@" in c.command) for c in bash), f"commit at {landed}")

    # --- issue §4: a spawn follows the call that wrote its brief, never shares its batch
    raced = []
    expect.info("spawns without a message id (same-batch half of the check is blind to them)", sum(1 for a in agents if not a.msg))
    for a in agents:
        m = _BRIEF_FILE.search(str(a.input.get("prompt", "")))
        if not m:
            continue
        name = m.group(1)
        writers = [c for c in tr.tool_calls(main_only=True)
                   if (c.name == "Bash" and name in c.command
                       and (_RP_BRIEF.search(c.command) or _HEREDOC_BRIEF.search(c.command) or re.search(r"\b(?:mv|cp)\s", c.command)))
                   or (c.name == "Write" and c.path.endswith(name))]
        writers = [w for w in writers if w.index < a.index]
        if not writers or (a.msg and writers[-1].msg == a.msg):
            raced.append(name)
    expect.that("every spawn follows the call that wrote its brief", not raced, f"{raced[:3]}")
