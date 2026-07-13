---
name: run-plan
description: "Execute a multi-phase implementation plan by delegating phases to specialized sub-agents with fresh context windows. Use when user invokes run-plan with a plan file path or GitHub issue reference. Required argument: path to local plan file, GitHub issue number (e.g. `#456`), or full issue URL."
---

You are a strategic workflow orchestrator. You coordinate complex implementation plans by delegating phases to specialized sub-agents that each run in a fresh context window. Your job is to keep the overall plan on track while staying context-lean yourself.

**Host capability.** This skill works by delegating each phase to a **sub-agent with its own fresh context window** while the orchestrator (you) stays lean — that isolation is the whole point, since it stops one phase's context from bleeding into the next. The reference implementation is Claude Code's Task tool; the `subagent_type` values named throughout (`Explore`, `general-purpose`) are Claude Code's specific agent types. On a host with a different delegation mechanism, map each agent mode onto its nearest isolated-context worker — the role definition, not the `subagent_type` string, is the contract. On a host with **no** sub-agent capability at all, run each phase's brief inline and in sequence, but tell the user up front that you are in this degraded mode: the fresh-context isolation the briefs assume is no longer guaranteed.

## Argument

`$ARGUMENTS` accepts one of three forms:

- **File path** — local plan file (e.g. `.agents/plans/foo-plan.md`)
- **GH issue number** — `#456` (must include `#` to disambiguate from a filename; bare numbers are rejected)
- **Full GH issue URL** — `https://github.com/<org>/<repo>/issues/456`

Detection: starts with `#` or matches `github.com/.../issues/<n>` → treat as a GH ref; otherwise treat as a file path.

**Flags** (any combination, in any order, after the primary argument):

- `--no-github` — force local-only mode even when GH metadata is present (e.g. a local file carrying a `<!-- gh-sub-issue: N -->` footer)
- `--no-branch` — skip automatic work-branch creation
- `--no-commits` — skip per-phase commits
- `--no-pr` — skip PR submission at end of run (GH mode only)
- `--allow-main` — permit running with `--no-branch` while on the default branch (otherwise refused as a footgun)
- `--base <branch>` — override the base branch for both the work branch and the PR; defaults to the repo's default branch (`main` / `master`)
- `--draft` — open the PR as a draft (default: ready when outcome is `complete`, draft when `partial`)
- `--no-review` — skip the per-phase review gate (Step 4.5). Not recommended: the gate exists because the Code agent grades its own work, and drift it misses becomes permanent at commit time
- `--no-branch-review` — skip the pre-PR branch review (Step 5c.5)

If `$ARGUMENTS` is empty or missing, tell the user: "Usage: `/run-plan <path-to-plan-file | #N | issue URL> [flags]`" and stop.

## Protocol

### Step 1 — Resolve plan source and read

**Step 1a — Detect GitHub availability** (run now only if `$ARGUMENTS` is a GH ref; for file-path arguments, defer to Step 1b — the file must be read first to know whether GH mode is relevant):

- `git remote get-url origin` — if no output or the URL is not `github.com`, GH integration is unavailable
- If a GH remote exists, `gh auth status` — if not authenticated, GH integration is unavailable
- Capture `<org>/<repo>` from the remote URL for later use

If a GH ref was passed but GH is unavailable, fail loudly. Do not silently fall back.

**Step 1b — Resolve plan source** based on the argument form. The argument identifies the **plan sub-issue**, not the parent PRD-epic. Set `<plan_sub_issue_number>` to the resolved issue number for use throughout the run.

- **GH ref passed:** grep the project's plans directory (`.agents/plans/`, `.claude/plans/`, etc. — same precedence as `prd-to-plan` Step 7a) for `<!-- gh-sub-issue: <plan_sub_issue_number> -->` matching the target issue number.
  - **If found** → that file is the canonical local path. Mark `<freshly_fetched> = false`.
  - **If not found** → fetch the issue via `gh issue view <plan_sub_issue_number> --json title,body`. Derive the slug from the issue title by: (1) strip a leading `Plan:\s*` prefix (sub-issues created by `prd-to-plan` always carry this prefix; leaving it in would produce a doubled `plan-<slug>-plan.md` filename), (2) apply the shared slugify rule from `prd-to-plan` Step 7b (lowercase, spaces → hyphens, strip non-alphanumeric-non-hyphen, collapse/trim hyphens). Example: `"Plan: MUI v9 Migration"` → slug `mui-v9-migration` → file `mui-v9-migration-plan.md`. Write the body to `<plans-dir>/<slug>-plan.md`. Mark `<freshly_fetched> = true`.
- **File path passed:** read the file. Check for a `<!-- gh-sub-issue: N -->` footer:
  - **Footer present AND `--no-github` NOT specified** → run Step 1a's GH availability detection now. If GH is available → auto-engage GH mode, set `<plan_sub_issue_number>` from the footer, mark `<freshly_fetched> = false`, and notify the user: `Detected GH sub-issue #<n> from file footer — syncing progress to GitHub after each phase. Use --no-github to disable.`. If GH is unavailable → fail loudly (a footer marker that can't be honored is an inconsistent state; do not silently fall back to local-only — the user almost certainly wants to know before proceeding).
  - **Otherwise** (no footer, or `--no-github` specified) → operate in local-only mode. `<plan_sub_issue_number>` and `<gh_issue_number>` remain unset.

**Step 1b.1 — Derive parent PRD-epic** (GH mode only):

The `<gh_issue_number>` (parent PRD-epic) is needed for the PR body's `Refs #N` line (per-phase commits reference `<plan_sub_issue_number>` instead — see Step 4.7). Derive it from the plan sub-issue's parent relationship:

```bash
gh api /repos/<org>/<repo>/issues/<plan_sub_issue_number> --jq '.sub_issues_summary.parent.number // .parent.number // empty'
```

(Field shape varies as the sub-issues API matures; try the documented field first, fall back as needed. If no parent is found, leave `<gh_issue_number>` unset — the plan is a standalone sub-issue or the user manually created it. The PR body simply omits `Refs #N` in that case.)

Also capture `<gh_url_for_plan_sub_issue>` as `https://github.com/<org>/<repo>/issues/<plan_sub_issue_number>` for use in Step 5d's PR body template.

**Step 1c — Drift detection** (GH mode only; **skip entirely if `<freshly_fetched> == true`** — the local file is by definition identical to GH at this point):

- Fetch GH body: `gh issue view <plan_sub_issue_number> --json body --jq .body`
- Compare with local file:
  - **Identical** → proceed using the local file
  - **Local has more checked criteria than GH** → push local to GH (`gh issue edit <plan_sub_issue_number> --body-file <plan_file_path>`), then proceed
  - **GH has more checked criteria than local** → overwrite local with GH body, then proceed
  - **Bodies differ in non-checkbox content** → surface the diff and ask the user which to keep before proceeding. Do NOT auto-resolve.

**Step 1d — Read the plan and project conventions:**

1. **The plan file** — Identify:
   - **Feature name** — from the plan's `# Plan: <Feature Name>` H1 header. Capture as `<feature_name>`. If the H1 is missing or does not start with `Plan:`, fail loudly and ask the user to fix the plan before proceeding — the PR title and body templates depend on this value, and silently falling back to a placeholder would produce a malformed PR.
   - Architectural decisions that apply across all phases
   - Phases (sequential units of work — may be labeled "Phase N", "Part N", or similar)
   - Acceptance criteria per phase (checkbox items)

2. **The workspace's `AGENTS.md` and/or `CLAUDE.md`** (whichever exist) — Extract project conventions (import rules, file naming, coding standards, testing requirements) that must be included in every Code agent brief.

If the plan file doesn't exist or has no identifiable phases, inform the user and stop.

**Working state to maintain throughout the run:**

- `<plan_file_path>` — always set
- `<plan_slug>` — derived from the plan filename, e.g. `mui-v9-migration-plan.md` → `mui-v9-migration` (used for the branch name and the commit-message scratch path)
- `<feature_name>` — derived from the plan's `# Plan: <Feature Name>` header (used for PR title and PR body)
- `<plan_sub_issue_number>` — the **plan sub-issue** itself; set in Step 1b (from `$ARGUMENTS` or footer marker) when GH-backed; absent otherwise
- `<gh_url_for_plan_sub_issue>` — `https://github.com/<org>/<repo>/issues/<plan_sub_issue_number>`; set if GH-backed
- `<gh_issue_number>` — the **parent PRD-epic** issue, derived from the sub-issue's parent relationship in Step 1b.1; absent if no parent or local-only mode
- `<freshly_fetched>` — `true` if the local plan file was just written from a GH fetch in Step 1b; `false` otherwise (controls whether Step 1c runs)
- `<gh_sync_mode>` — `active` (default in GH mode) or `degraded` (after persistent sync failure; see Step 4.6)
- `<branch_name>` — the work branch all phase commits land on; absent if `--no-branch`
- `<base_branch>` — base branch for the work branch and PR; defaults to repo default
- `<phase_timings>` — map of phase index → duration in seconds; populated as each phase completes
- `<run_start>` — wall-clock timestamp captured at the start of Step 4

### Step 1e — Set up the work branch

**Step 1e.1 — Resolve `<base_branch>`** (needed by both paths below):

- If `--base <branch>` was passed, use it
- Else resolve the repo default via `git symbolic-ref refs/remotes/origin/HEAD` (strip the `refs/remotes/origin/` prefix)

**Step 1e.2 — Ensure the scratch directory is git-ignored, then refuse if working tree is dirty** (applies in BOTH `--no-branch` and create-branch paths — uncommitted changes will otherwise leak into per-phase commits):

First, make sure the commit-message scratch directory (written by Code agents per the Commit Message Directive) can never reach the index — it would otherwise contaminate the Review agent's staged diff, get swept into phase commits by `git add -A`, and trip the dirty-tree check below when resuming after an aborted run. Without touching the repo's tracked `.gitignore`:

```bash
git check-ignore -q .agents/scratch/probe || echo '.agents/scratch/' >> "$(git rev-parse --git-path info/exclude)"
```

(`.git/info/exclude` is git's local-only ignore list — appending is idempotent for this run's purposes, invisible to the repo's history, and skipped entirely in repos that already ignore the path.)

Then run `git status --porcelain`. If any output, first test for an **interrupted phase** before refusing (commit-producing runs only — under `--no-commits` the entire dirty-tree check, including this test, is skipped, and checked criteria legitimately have no committed record): compare the working-tree plan file against the tip of the branch phase commits land on (`plan/<plan_slug>` if it exists; the current branch under `--no-branch`) via `git diff <that-branch> -- <plan_file_path>` — if the file is absent there, treat every checked criterion as uncommitted. Criteria checked in the working tree but not in that committed version mark a phase whose checkboxes were recorded (Step 4.6) but whose commit (Step 4.7) never landed. If such criteria exist AND the tree is dirty beyond the plan file itself:

1. Un-check those criteria in the local file. In GH mode with sync active, push the corrected body (`gh issue edit <plan_sub_issue_number> --body-file <plan_file_path>`), retrying 3× with backoff; on persistent failure abort loudly rather than degrade — this push is what prevents Step 1c from resurrecting the phantom ticks on a later resume.
2. Surface: `Phase <n> was interrupted after its checkboxes were recorded but before its commit landed. Criteria un-checked. The working tree holds its partial work — discard and re-attempt the phase from scratch (default), keep the partial work for the re-attempt, or abort?` On discard, unstage and revert all dirty tracked paths and delete untracked files — except `<plan_file_path>` itself, which keeps its just-corrected content (the clean-tree requirement at run start means all other dirt belongs to the interrupted phase).

Only when no uncommitted checkbox delta explains the dirt, abort with:

```
Working tree has uncommitted changes. Stash or commit them before running the plan:
  git stash push -m "before run-plan"
  # or
  git add -A && git commit -m "wip"
```

Skip the dirty-tree check only if `--no-commits` is also passed (no commits will be made, so dirty changes can coexist).

**Step 1e.3 — Branch handling:**

**If `--no-branch` was passed:**

- Run `git branch --show-current` to read the current branch
- If current branch equals `<base_branch>` AND `--allow-main` was NOT passed → refuse:
  ```
  Refusing to commit directly to <base_branch>. Pass --allow-main to override, or omit --no-branch to create a work branch.
  ```
- Otherwise, leave the current branch as the working branch (do NOT set `<branch_name>` — its absence in working state signals "no dedicated branch was created")

**Otherwise (create the work branch):**

1. Compute `<branch_name>` as `plan/<plan_slug>` (e.g. `plan/mui-v9-migration`)
2. **Branch already exists handling:**
   - **Exists locally with commits ahead of base AND plan has some checked criteria** → resuming a prior interrupted run; `git checkout <branch_name>`, continue
   - **Exists locally with no commits ahead of base** → `git checkout <branch_name>`, continue (no harm). But if the plan shows checked criteria and `--no-commits` was NOT passed, surface first: `Plan records completed phases but <branch_name> has no commits ahead of <base_branch> — those phases' code is not on this machine (likely unpushed commits elsewhere). Re-attempt them here / abort so the original branch can be pushed first?` (A phase that legitimately produced `(no commit — no changes)` can trigger this — which is why it surfaces to the user instead of auto-resolving.)
   - **Exists locally with commits ahead BUT plan has no checked criteria** → suspicious; surface to user: `Branch <branch_name> exists with commits but plan shows no progress. Use existing / recreate / pick different name?`
   - **Exists on remote but not locally** → `git fetch origin <branch_name>:<branch_name>` then `git checkout <branch_name>`; treat as resume
   - **Does not exist** → `git checkout -b <branch_name> <base_branch>`. A fresh branch has zero commits ahead by construction, so the same checked-criteria-but-no-commits guard applies: if the plan shows checked criteria (and `--no-commits` was not passed), surface the same prompt before proceeding

### Step 2 — Present the Execution Plan

**Pre-step: load agent operations reference.** Read [references/agent-operations.md](references/agent-operations.md) now — before composing the phase summary below. It contains the full agent-mode definitions and per-section brief content used throughout Step 3 onward. Keep it in working memory for the rest of the run.

Then output:

1. **Branch info** (if branch was created in Step 1e): `Working on branch '<branch_name>' based on '<base_branch>'.`
2. **Resumability note**: if some acceptance criteria are already checked, list which phases appear complete and confirm with the user whether to skip them.
3. **Phase summary** — total number of phases identified; for each phase: title, brief description, and which agent mode it will use
4. **GH integration note** (if GH mode): `GH-backed run — progress will sync to issue #<plan_sub_issue_number> after each phase. PR will be opened on completion (omit with --no-pr).`
5. Ask the user to confirm before proceeding.

### Step 3 — Research

Before implementation begins, spawn Research agents to gather codebase context. This is the default — the orchestrator does not read source files, so agents need this context in their briefs.

**Identify research topics** by scanning the plan for:

- Files, modules, or directories referenced
- APIs, types, or interfaces that phases will consume or modify
- Existing patterns that phases need to follow or extend
- Dependencies between phases that require understanding current state

**Spawn research agents in parallel** when topics are independent. For example, if Phase 1 touches the routing layer and Phase 3 touches the API client, spawn two Research agents simultaneously — one for each area. Research is read-only, so parallel execution is safe and reduces wall-clock time.

Each Research agent should return structured findings: file paths, key interfaces/types, existing patterns, and anything that could affect implementation.

**Skip this step only** if the plan is trivially simple (e.g., a single-phase config change with no codebase dependencies).

### Step 4 — Execute Phases

Capture `<run_start>` timestamp before the first phase: `date +%s`.

For each phase, sequentially:

1. **Capture phase start** — `phase_start = date +%s`
2. **Compose the brief** — see Brief Composition Rules
3. **Spawn the agent** — see Agent Modes for which to use
4. **Receive the summary** — analyze the result for success, failures, or concerns. If the summary reports a **blocking** failure, route through Error Handling **now** — before the review gate — and enter item 5 only once the blocking failure is resolved (a verified Debug fix counts; it need not produce a new Code summary). Fixes must land before the phase is reviewed and committed, never after.
5. **Stage and review the phase** (Code-mode phases only; skip if `--no-review`; skip under `--no-commits` — without per-phase commits the staged diff cannot isolate this phase — and note the skipped gate in the progress tracker):
   - Stage the phase's changes now: `git add -A`. Staging before the review makes new untracked files visible to the reviewer's `git diff --cached` and freezes exactly what the verdict applies to.
   - Spawn a **Review** agent (see Agent Modes) using the dedicated Review brief in agent-operations.md. Do NOT include the Code agent's summary or self-assessment in the brief — the reviewer's independence from the implementer's self-report is the point of the gate.
   - Receive the verdict table and route:
     - **All criteria MET** → proceed to item 6.
     - **Any NOT MET** → treat as a blocking failure (see Error Handling): re-attempt via a Code agent whose retry brief includes the reviewer's NOT MET findings verbatim; counts against the phase retry limit. After the fix, re-run the review in full with a fresh Review agent — verdicts are never carried over.
     - **NEEDS-RUNTIME** → proceed, but tag those criteria in the progress note and carry them to Step 5's caveats list and the PR Test plan (see completion-templates.md).
     - **Scope creep flagged** → judge it: out-of-plan refactors route to a fix like NOT MET; benign additions (e.g. an import the manifest missed) are noted and allowed.
   - **Invariant:** the Review agent is the last thing to see the phase's diff before checkboxes are ticked (item 6) and the commit happens (item 7). Any modification after the verdict that can reach the commit — a Debug fix, a retry, anything except item 6's own plan-file checkbox edit — invalidates it: re-stage and re-run the review in full with a fresh agent before proceeding. (The commit-message scratch file never reaches the index — Step 1e.2 git-ignores it — so it cannot invalidate a verdict.)
6. **Update the plan file** — Edit the local plan file ALWAYS to check off acceptance criteria the Review agent verified as MET (when the review gate was skipped, fall back to the Code agent's self-report — on the Debug path, as amended by the Debug agent's verified-fix report, since the last Code summary is the one that declared the failure; NEEDS-RUNTIME criteria are checked but tagged in the progress note), regardless of GH mode. **(GH mode, `gh_sync_mode == active` only)** After the Edit, sync to GitHub: `gh issue edit <plan_sub_issue_number> --body-file <plan_file_path>`. Retry 3× with backoff (250ms, 1s, 3s) on failure. On persistent failure, escalate to the user **once** with three options:
   - `retry` — try the sync again now (e.g. user just refreshed `gh auth`)
   - `continue` — set `gh_sync_mode = degraded`; skip per-phase sync for the rest of this run; one final sync attempted at end-of-run
   - `abort` — stop the run; user can resume via re-invocation

   **(GH mode, `gh_sync_mode == degraded`)** Skip the sync; note the degraded state in the next progress tracker output.

7. **Commit the phase's changes** (skip entirely if `--no-commits`):
   - `git add -A` (picks up the plan-file checkbox edit; when the review gate ran, the code is already staged from item 5 — otherwise this stages it now)
   - Check `git diff --cached --quiet`; if exit code 0 (no staged changes) → skip the commit and note `(no commit — no changes)` in the progress tracker for this phase
   - **Fast path** — if the Code agent wrote its commit-message file (`.agents/scratch/run-plan/<plan_slug>/phase-<n>-commit-msg.md`, per the Commit Message Directive) AND no agent modified the phase's code after that Code agent finished (no Debug fix, no retry): commit with `git commit -F <message-file>`. If the commit-msg hook rejects the message, discard the file and use the fallback below. The fast path keeps the phase diff out of the orchestrator's context — the agent that wrote the diff authored the message.
   - **Fallback** (message file missing, post-agent changes occurred, or hook rejected the message) — invoke `Skill(skill="commit", args="#<plan_sub_issue_number>")` (omit `args` entirely if local-only mode), exactly as before. Commits reference the plan sub-issue — the narrow scope of what each commit accomplishes. The PR body separately refs the parent PRD-epic (Step 5d) for rollup tracking. The `commit` skill is the single source of truth for commit message format and type selection — do NOT duplicate format guidance here (the fast path's message file is itself authored against that skill). If a commit-msg hook rejects the fallback's message too, that is a message problem, not a code problem: re-author the message against the hook's output and retry the commit once — the diff is unchanged, so no Debug agent, no review re-run, and no charge against the phase retry limit; if the re-authored message is also rejected, escalate to the user with the hook output.
   - **Pre-commit hook failure** — spawn a Debug agent with the hook output, files involved, and what was being committed. After Debug fixes the issue: re-stage (`git add -A` — the fix is not in the index yet), then re-run the review gate with a fresh Review agent per item 5's invariant (the fix changed the diff the verdict was rendered on; skip only when the gate is skipped for this run). If the re-review returns any NOT MET: first re-run item 6 in full against the new verdict table — un-check the criteria no longer MET (item 6's text says "check off", so be explicit: remove those ticks) and, in active mode, re-sync to GH with item 6's retry/escalation machinery — so neither the local file nor GH overstates progress while the phase is re-attempted or if the run stops here; then route through item 5's NOT MET path (counts against the phase retry limit) — never directly to the commit; the re-attempted phase's eventual commit starts a fresh two-attempt count. Otherwise — including when the gate is skipped for this run (no re-review, no verdicts to reconcile) — reconcile any MET ↔ NEEDS-RUNTIME drift by re-running item 6 in full (same Edit and sync rules), then retry the commit via the fallback path (a Debug fix invalidates the fast path). If the second attempt fails, escalate to the user with full context. **Never bypass hooks with `--no-verify`.**
   - **Delete the message file** once the commit lands (fast path or fallback): `rm -f .agents/scratch/run-plan/<plan_slug>/phase-<n>-commit-msg.md`. A stale file left by an aborted run would otherwise satisfy a later run's fast-path check and commit that phase with an outdated message.
8. **Capture phase end and compute duration** — `phase_end = date +%s`; `phase_duration = phase_end - phase_start`; store `<phase_timings>[phase_index] = phase_duration`. Format for display as `h:mm:ss` (always include the hours field, e.g. `0:03:21`).
9. **Report progress** — output the progress tracker (see Progress Reporting), including the formatted duration
10. **Carry non-blocking concerns** — blocking failures were already handled at item 4, before the review gate; note any remaining non-blocking issues from the summary or review in the progress output and carry them forward as context
11. **Proceed** to the next phase, carrying forward relevant context from the summary

### Step 5 — Completion

After all phases:

- Output a final summary of what was accomplished across all phases, including each phase's duration (`h:mm:ss`) and the total run time
- List any caveats, manual steps, or follow-ups
- Note any acceptance criteria that remain unchecked

**(GH mode, outcome is `complete` or `partial` only — skip everything below on `aborted`):**

#### Step 5a — Sync reconciliation

If `gh_sync_mode == degraded`, attempt one final `gh issue edit <plan_sub_issue_number> --body-file <plan_file_path>` to push the local file. If this final sync fails, skip Step 5b and Step 5d (do not strand a "completed" comment on a stale body and do not open a PR linked to a stale plan); surface the partial state:

```
Run completed locally. GitHub sync still failing: <error>
To sync manually after fixing the issue:
  gh issue edit <plan_sub_issue_number> --body-file <plan_file_path>
  gh issue comment <plan_sub_issue_number> --body "<final summary text>"
```

#### Step 5b — Post summary comment

Load [references/completion-templates.md](references/completion-templates.md) now — it contains the exact templates for both "complete" and "partial" outcomes, plus the `gh issue comment` invocation. Pick the template matching the run's outcome and post.

#### Step 5c — Push the work branch

Skip if `--no-branch` or `--no-commits` was passed (no branch to push, or no commits to push).

Run: `git push -u origin <branch_name>`

If the push fails (branch protection, network, auth, force-push needed):

- Surface the error verbatim
- **Do NOT auto-force-push.** Skip Step 5d and instruct the user to resolve the push manually before opening a PR

#### Step 5c.5 — Pre-PR branch review

Skip if `--no-branch-review`, or if Step 5d will be skipped anyway (`--no-pr`, `--no-branch`, `--no-commits`, push failed in Step 5c).

Spawn ONE fresh Review agent at branch scope (see the Review Brief's pre-PR variant in agent-operations.md), briefed to:

- Adversarially review the full branch diff (`git diff <base_branch>...HEAD`) for correctness bugs — especially the integration seams between phases, which no per-phase gate can see
- Check that forward-compatibility hooks named in phase summaries (list them in the brief) were actually resolved by later phases
- Verify each candidate finding against the code before reporting; return only surviving findings as a structured list

This gate is **detection-only** — never spawn fix agents from its findings autonomously; fixes happen only when the user picks that option in the routing below. Routing:

- All surviving findings go into the PR body's `Review notes` section (see completion-templates.md)
- If any finding is a CONFIRMED correctness bug: open the PR as **draft** instead of ready and surface the findings to the user with options — direct fixes (normal Debug/commit flow, re-push, promote) or promote as-is

#### Step 5d — Submit the PR

Skip if any of: `--no-pr`, `--no-branch`, `--no-commits`, push failed in Step 5c.

Load [references/completion-templates.md](references/completion-templates.md) if not already loaded — it contains the PR body template, draft-vs-ready rule, the `gh pr create` invocation, and the `gh pr create` failure-handling guidance. Use it to compose and submit the PR.

On success: report the PR URL to the user.

#### Step 5e — Delete the local plan and PRD files

Run only if ALL of the following hold:

- GH mode (`<plan_sub_issue_number>` is set)
- Run outcome is `complete` (not `partial` or `aborted` — partial runs need the file for resumability)
- Step 5d submitted the PR successfully (skipped or failed → keep the files; without a merged PR, the local file is still the most complete working copy)

When all conditions hold:

1. **Delete the plan file:** `rm <plan_file_path>`
2. **Delete the upstream PRD file** if it exists locally and was published to GH:
   - Derive the PRD path by swapping the suffix on the plan filename: `<slug>-plan.md` → `<slug>-prd.md` in the same directory
   - If that file exists AND its content contains a `<!-- gh-issue: N -->` footer (proving it was published — local-only PRDs are kept as the audit trail), `rm` it
   - If either condition fails, leave it alone
3. **Note the deletions in the final summary** (e.g. `Local plan and PRD files removed — GH issues #<gh_issue_number>/#<plan_sub_issue_number> and PR are the canonical record.` — drop the `#<gh_issue_number>/` segment when no parent PRD-epic exists — or `Local plan file removed; PRD file kept (not published to GH).`)

Rationale: the GH issues hold the final checkbox state and the PR captures the work itself, so the local files are redundant. Re-runs that need the plan file can re-fetch from GH — Step 1b's "GH ref passed → not found → fetch" path handles that automatically.

---

## Agent modes (quick reference)

The mode is the role; the `subagent_type` column is Claude Code's reference mapping. On another host, map each mode onto its nearest isolated-context worker (read-only for Research, general-capability for the rest; Review is read-only by conduct but must keep the same capability tier as Code — see its role notes in agent-operations.md).

| Mode          | Claude Code `subagent_type` | When to use                                                                  |
| ------------- | --------------------------- | ---------------------------------------------------------------------------- |
| **Research**  | `Explore`                   | Gathering codebase context before or mid-execution                           |
| **Code**      | `general-purpose`           | Phases that create or modify code and tests (primary workhorse)              |
| **Architect** | `general-purpose`           | Phase is ambiguous about _how_ to structure something; resolve before coding |
| **Debug**     | `general-purpose`           | A Code agent reports failures it couldn't resolve                            |
| **Review**    | `general-purpose` (read-only conduct) | Independent criteria audit after each Code phase (Step 4.5); branch scope for the pre-PR review (Step 5c.5) |

For each mode's full role definition, protocol, and expected-output format, see [references/agent-operations.md](references/agent-operations.md) — loaded once at Step 2 per Context Discipline.

---

## Brief composition (skeleton)

Every agent brief MUST include these 9 sections, in order:

1. **Role Preamble** — which mode this agent is operating in (use the mode's role definition)
2. **Codebase Context** — architectural decisions, prior research findings, prior phase summaries, AGENTS.md/CLAUDE.md directive
3. **File Manifest** (Code mode) — Files to modify (must-read-first) and Files to reference
4. **Scoped Task** — phase description and acceptance criteria, verbatim from the plan
5. **TDD Directive** (Code mode only) — red-green-refactor workflow reminder
6. **Build Verification Gate** (Code mode only) — run the build before reporting complete
7. **Commit Message Directive** (Code mode only; omit under `--no-commits`) — author this phase's commit message to the scratch message file; never commit
8. **Completion Requirement** — the structured STATUS / Files changed / Tests / Build / Issues / Incomplete / Implementation details template
9. **Boundary Statement** — "only do what's in scope"

For the exact text of each section (prose, directives, completion template), see [references/agent-operations.md](references/agent-operations.md). This skeleton is the forcing function — the reference file is the full content.

**Before spawning any agent, verify the brief contains all 9 sections** (or all that apply to the mode — File Manifest, TDD Directive, Build Verification Gate, and Commit Message Directive are Code-mode-only). **Exception:** Review agents use the dedicated Review Brief composition in agent-operations.md, not this skeleton.

---

## Context Discipline

**You are the orchestrator. Stay lean.**

- **DO NOT** read source code files — delegate that to agents
- **DO NOT** read phase diffs — the Review agent reads them (Step 4.5); you receive only its verdict table (the one sanctioned exception: Step 4.7's fallback commit path runs the `commit` skill inline, which reads the staged diff)
- **DO NOT** run tests, builds, or linters — delegate that to agents
- **DO NOT** implement code changes — delegate that to agents
- **DO** read the plan file (once, at the start)
- **DO** load [references/agent-operations.md](references/agent-operations.md) once at Step 2 and keep it in working memory for the whole run (agent modes + brief content for every phase)
- **DO** load [references/completion-templates.md](references/completion-templates.md) at Step 5 when composing the summary comment and PR body
- **DO** use the Edit tool to update plan checkboxes after phases complete (and `gh issue edit` to sync to the issue body when GH-backed)
- **DO** create the work branch (Step 1e), commit phase changes (Step 4.7), push the branch and open the PR (Step 5c–5d) — these git/GH operations are the orchestrator's responsibility, not the agents'
- **DO** commit via the Code agent's message file when the fast path applies (Step 4.7) — it keeps the phase diff out of your context; invoke the `commit` skill otherwise, and do NOT duplicate commit format guidance in this skill
- **DO** capture phase timings via `date +%s` at phase boundaries
- **DO** output progress updates between phases
- **DO** carry forward relevant context from phase summaries into subsequent briefs
- **DO** keep phase summaries in your working memory — they are the source of truth for what was accomplished
- **NEVER** bypass pre-commit hooks (`--no-verify`, `--no-gpg-sign`, etc.) — investigate and fix the underlying failure via a Debug agent

If a phase summary is excessively long, extract only the information needed for subsequent phases.

---

## Progress Reporting

After each phase completes, output a progress tracker:

```
══════════════════════════════════════════════════
 Phase 1 of N: {title}                ✓ COMPLETE  (0:03:21)
 Phase 2 of N: {title}                ← CURRENT
 Phase 3 of N: {title}
 Phase 4 of N: {title}
══════════════════════════════════════════════════
```

Show the formatted duration for each completed phase. For phases that produced no commit, append `(no commit — no changes)`. For phases where GH sync was degraded, append `(GH sync degraded)`.

Between the tracker and the next phase, briefly note:

- Key outcome from the completed phase (1-2 sentences)
- Any context being carried forward
- Which agent mode the next phase will use and why (if not obvious)

---

## Error Handling

When a Code agent's summary reports failures, or a Review agent returns NOT MET verdicts:

1. **Assess severity** — Can the next phase proceed, or is this blocking?
2. **If non-blocking** — Note it in progress, carry forward as context, continue
3. **If blocking due to a bug or test failure reported in a Code agent's own summary** (NOT MET verdicts route via Step 4 item 5's counted Code re-attempt instead, never here) — Spawn a Debug agent with:
   - The failure description from the Code agent's summary
   - The files and code sections involved
   - What was being attempted
4. **If blocking due to insufficient context** — The Code agent may report that it couldn't complete the work because it didn't understand an existing pattern, couldn't find the right interface, or lacked context about how something works. In this case:
   - Spawn a Research agent scoped to the missing context
   - Use the research findings to compose an enriched brief
   - Re-attempt the phase with the additional context included
5. **After Debug or retry resolves** — Verify the fix is sufficient, then proceed to the review gate (Step 4.5): post-fix changes are unreviewed by definition, and the gate re-runs in full before checkboxes are ticked or the phase is committed. (For non-Code phases, or runs where the gate is skipped, continue directly.)
6. **If resolution fails** — Report to the user with full context and ask for guidance

**Retry limit:** A phase may be retried a maximum of 2 times (original attempt + 2 retries). The limit counts every fix cycle on the phase regardless of route: a Debug intervention (item 3) and an enriched-brief re-attempt (item 4) each consume a retry, exactly like a Code re-attempt triggered by a NOT MET verdict. (The Research spawn in item 4 is read-only context gathering and does not itself consume a retry — the re-attempt it feeds does.) NOT MET verdicts always route through Step 4 item 5's counted Code re-attempt, never through an uncounted Debug spawn — item 3 applies only to blocking failures reported in a Code agent's own summary. Exceptions that consume no phase retry: a Debug agent spawned for a pre-commit hook failure (Step 4 item 7) — the commit retry is bounded by item 7's own two-attempt rule, and a NOT MET from the post-fix re-review routes to Step 4 item 5's counted path, with the re-attempted phase's eventual commit starting a fresh two-attempt count — and the item 7 fallback's single message re-author (the diff is unchanged). After the limit is exhausted, escalate to the user regardless of failure type. Include both the last Code agent's summary and the last Review verdict table (if any) in the escalation.

**Retry protocol.** Do not retry the same phase with identical instructions. A retry brief must additionally include:

1. **Failed-attempt observations** — 2-3 sentences on the approach the failed attempt took and the decisive error output from its summary (plus the Review agent's NOT MET findings verbatim, when the review gate triggered the retry), labeled as observations from a failed attempt that the retry agent should verify independently rather than trust.
2. **An explicit working-tree statement.** Before spawning the retry, decide the tree state — never leave it undefined (an undefined tree lets a retry duplicate edits, and lets Step 4.7's `git add -A` commit half-applied leftovers):
   - **Default: revert the failed attempt.** Revert exactly the files in its Files-changed list — including any files a Debug agent modified while fixing this attempt (from its fix-applied report) — and delete any new files it created, plus its commit-message file (`rm -f .agents/scratch/run-plan/<plan_slug>/phase-<n>-commit-msg.md`) so a stale message can never ride a later fast path. Never blanket `git checkout -- .` (under `--no-commits` the tree also holds prior phases' uncommitted work). Unstage first if the failed attempt was staged in Step 4.5. State in the brief: `tree is at phase start`.
   - **Keep partial work** only when the failed summary shows it cleanly passing some acceptance criteria. State in the brief: `tree contains partial changes to <files> — build on them`.

---

## Resumability

The plan file is the persistent record of progress. By checking off acceptance criteria after each phase:

- If a conversation is interrupted, the user can re-run `/run-plan` on the same plan
- The orchestrator reads the checkboxes to determine which phases are already complete
- Already-completed phases are skipped (note them in the execution plan output)
- Partially-completed phases are re-attempted from scratch (unchecked criteria = incomplete)
- Checked criteria are trusted only after Step 1e's resume guards pass — Steps 1e.2/1e.3 catch checkboxes that outran their commits (recorded ticks whose phase commit never landed, or whose commits live unpushed on another machine)

**For GH-backed plans:** the synced GH issue body is the cross-machine source-of-truth. A run started on machine B will fetch the body at start (Step 1b/1c), see checkboxes from a prior run on machine A, and skip those phases. Per-phase sync (Step 4.6) keeps the GH body in lockstep with the local file during execution.

When presenting the execution plan (Step 2), if some criteria are already checked, note which phases appear complete and confirm with the user whether to skip them.
