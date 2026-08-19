---
name: run-plan
description: "Execute a multi-phase implementation plan by delegating each phase to sub-agents with fresh context windows. Use when the user invokes run-plan with a plan file path, GitHub issue number (e.g. `#456`), or full issue URL."
---

You are a strategic workflow orchestrator. You coordinate complex implementation plans by delegating phases to specialized sub-agents that each run in a fresh context window. Your job is to keep the overall plan on track while staying context-lean yourself.

**Host capability.** This skill delegates each phase to a **sub-agent with its own fresh context window** while the orchestrator (you) stays lean — that isolation stops one phase's context from bleeding into the next. The reference implementation is Claude Code's Task tool; the `subagent_type` values named throughout (`Explore`, `general-purpose`) are its agent types. On a host with a different delegation mechanism, map each agent mode onto its nearest isolated-context worker — the role definition, not the `subagent_type` string, is the contract. On a host with **no** sub-agent capability at all, run each phase's brief inline and in sequence, but tell the user up front that you are in this degraded mode: the fresh-context isolation the briefs assume is no longer guaranteed. Usage figures likewise degrade to whatever metadata the host exposes (and never gate the workflow) — see Run Ledger → Host portability.

## Argument

`$ARGUMENTS` accepts one of three forms:

- **File path** — local plan file (e.g. `.agents/plans/foo-plan.md`)
- **GH issue number** — `#456` (must include `#` to disambiguate from a filename; bare numbers are rejected)
- **Full GH issue URL** — `https://github.com/<org>/<repo>/issues/456`

Detection: starts with `#` or matches `github.com/.../issues/<n>` → treat as a GH ref; otherwise treat as a file path.

**Flags** (any combination, in any order, after the primary argument):

- `--no-github` — force local-only mode even when GH metadata is present (e.g. a local file carrying a `<!-- gh-sub-issue: N -->` footer)
- `--no-branch` — skip automatic work-branch creation
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

- **GH ref passed:** grep the project's plans directory (`.agents/plans/`, `.claude/plans/`, etc. — same precedence as `prd-to-plan` Step 7a) for `<!-- gh-sub-issue: <plan_sub_issue_number> -->` **or** `<!-- gh-issue: <plan_sub_issue_number> -->` matching the target issue number (the latter marks a plan published directly as a standalone issue, not via `prd-to-plan`).
  The grep can return several files, so **reduce to a single candidate before handling anything**, in this order:

  1. Any `gh-sub-issue:` match wins outright — `prd-to-plan` stamps that footer on plans only.
  2. Otherwise, discard every `gh-issue:` match that is **not** a plan (a plan has phase headings and acceptance criteria; published PRDs carry the identical footer). Name each discarded file when reporting the resolution: its footer claims an issue it does not own, which is a data problem worth fixing.
  3. Then: **one candidate** → handle it below. **Two or more plans**, each claiming the same issue → a genuine tie with no principled resolution: stop and ask which is canonical. **Everything discarded as a PRD** → the user passed the PRD-epic's number: fail loudly (`#N is a PRD-epic, not a plan — pass its plan sub-issue, or create one with prd-to-plan`). **Nothing matched at all** → the fetch branch below.

  - **Candidate carries `gh-sub-issue:`** → that file is the canonical local path. Mark `<freshly_fetched> = false`.
  - **Candidate carries `gh-issue:`** → a **standalone plan issue**: that file is the canonical local path, and the single issue serves as `<plan_sub_issue_number>` throughout (sync target, commits, the PR's `Closes`). Mark `<freshly_fetched> = false`. Step 1b.1 will find no parent, so `<gh_issue_number>` stays unset — expected, not an error.
  - **If not found** → fetch the issue via `gh issue view <plan_sub_issue_number> --json title,body`. Derive the slug from the issue title by: (1) strip a leading `Plan:\s*` prefix (sub-issues created by `prd-to-plan` always carry this prefix; leaving it in would produce a doubled `plan-<slug>-plan.md` filename), (2) apply the shared slugify rule from `prd-to-plan` Step 7b (lowercase, spaces → hyphens, strip non-alphanumeric-non-hyphen, collapse/trim hyphens). Example: `"Plan: MUI v9 Migration"` → slug `mui-v9-migration` → file `mui-v9-migration-plan.md`. Write the body to `<plans-dir>/<slug>-plan.md`. Mark `<freshly_fetched> = true`.
- **File path passed:** read the file. Check for a `<!-- gh-sub-issue: N -->` footer (or, on a standalone-published plan, a `<!-- gh-issue: N -->` footer — same handling, standalone semantics as above):
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
  - **Local has more checked criteria than GH** → push local to GH (`gh issue edit <plan_sub_issue_number> --body-file <plan_file_path>`), **report it** (`Reconciled #<n> — pushed <k> criteria an earlier run completed but never synced.`), then proceed. This is one of two remote writes that can precede Step 2's confirmation gate (the other is Step 1e.2's phantom-tick correction), so it must never be silent
  - **GH has more checked criteria than local** → overwrite local with GH body, then proceed
  - **Bodies differ in non-checkbox content** → surface the diff and ask the user which to keep before proceeding. Do NOT auto-resolve.

**Step 1d — Read the plan and project conventions:**

1. **The plan file** — Identify:
   - **Feature name** — from the plan's `# Plan: <Feature Name>` H1 header. Capture as `<feature_name>`. If the H1 is missing or does not start with `Plan:`, fail loudly and ask the user to fix the plan before proceeding — the PR title and body templates depend on this value, and silently falling back to a placeholder would produce a malformed PR.
   - Architectural decisions that apply across all phases
   - Phases (sequential units of work — may be labeled "Phase N", "Part N", or similar)
   - Acceptance criteria per phase (checkbox items)

2. **The workspace's `AGENTS.md` and/or `CLAUDE.md`** (whichever exist) — Extract two things:
   - **Project conventions** (import rules, file naming, coding standards, testing requirements) that must be included in every Code agent brief.
   - **The PR-submission rule, if the instructions state one** — e.g. "do not run `gh pr create`; a CI workflow opens the PR when a branch is pushed". Set `<pr_open_mode> = declared` when such a rule is present, `silent` otherwise. Step 5d's submission gate reads this value; resolving it here means the gate does not depend on those files still being in context many phases later.

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
- `<outcome>` — the run's terminal classification, set once at Step 5 and consumed by the Step 5 GH gate, Step 5e, the summary-comment template, and the draft-vs-ready rule. `complete` = every phase is done (executed this run, or already checked at resume) and every acceptance criterion is ticked; `partial` = the run reached Step 5 with any criterion unticked or any phase BLOCKED/not attempted; `aborted` = the run stopped early (user abort, or retry limit exhausted without a user go-ahead). A resume that executes zero phases because all were already complete is `complete`, not `aborted` — Step 4's loop simply runs zero iterations
- `<branch_name>` — the work branch all phase commits land on; absent if `--no-branch`
- `<base_branch>` — base branch for the work branch and PR; defaults to repo default
- `<pr_open_mode>` — `declared` (the repo's agent instructions say a workflow opens the PR on push, so `gh pr create` is forbidden) or `silent` (no such rule — run-plan opens the PR itself); resolved in Step 1d, consumed by Step 5d
- `<scratch_dir>` — the run's temp-file directory, resolved once in Step 1e.2 (the authority for its layout and fallback); NEVER hardcode `.agents/scratch` — always use the resolved value.
- `<ledger_path>` — `<scratch_dir>/ledger.md`, the append-only usage ledger — see Run Ledger for its contents and rules.
- `<run_start>` — a single wall-clock stamp for the optional labeled "elapsed" line only; capture timing and limits in Step 4's opening.
- `<keep_dirty_pathspec>` — optional; the `':(exclude)<path>'` pathspec entries every staging site applies for paths that stay modified in the working tree but never committed — see Step 1e.2's Keep-dirty paths rule. Absent when none are declared. The in-context value is a cache: the durable record is `<scratch_dir>/tree-state.md`.
- `<precommit_pathspec>` — optional; set by working-tree.md's triage for the paths the user names as this work's **inputs**, committed alone ahead of Phase 1. Holds those literal paths, unquoted, for Step 1e.4 to stage. Absent when the user names none or the tree was clean.
- `<inputs_commit_sha>` — optional; `git rev-parse HEAD` captured immediately after Step 1e.4's commit and recorded in `<scratch_dir>/tree-state.md`. Step 5c.5 scopes the branch review past it; by then it is many commits back and not re-derivable from git alone, so a resume reloads it from the record in Step 1e.2. Absent when no inputs commit was made.

### Step 1e — Set up the work branch

**Step 1e.1 — Resolve `<base_branch>` and clear the deterministic refusals** (needed by both paths below):

- If `--base <branch>` was passed, use it
- Else resolve the repo default via `git symbolic-ref refs/remotes/origin/HEAD` (strip the `refs/remotes/origin/` prefix)
- **Then, under `--no-branch` only:** read the current branch (`git branch --show-current`). Empty output is a detached HEAD — refuse: `--no-branch on a detached HEAD would commit to no branch; the next checkout strands the commits reflog-only.` If it equals `<base_branch>` while `--allow-main` was NOT passed, refuse now — `Refusing to commit directly to <base_branch>. Pass --allow-main to override, or omit --no-branch to create a work branch.` These checks need nothing but the two flags and the branch name, so they belong ahead of Step 1e.2: a run that cannot start must not first prompt the user through a triage, commit their files, or push a corrected issue body.

**Step 1e.2 — Resolve `<scratch_dir>`, ensure it's git-ignored, then resolve a dirty working tree** (applies in BOTH `--no-branch` and create-branch paths — unresolved uncommitted changes will otherwise leak into per-phase commits):

First resolve `<scratch_dir>` (see Working state): the sibling `scratch/run-plan/<plan_slug>/` of the resolved plans directory — `.agents/scratch/run-plan/<plan_slug>/` in this repo, `.claude/scratch/run-plan/<plan_slug>/` for a `.claude/`-layout consumer. If no in-repo plans directory applies, use `${TMPDIR:-/tmp}/run-plan/<plan_slug>/` (outside the repo — no ignore needed, git never sees it). Create it: `mkdir -p <scratch_dir>`.

Then, when `<scratch_dir>` is INSIDE the repo, make sure it can never reach the index — its files (ledger, commit-message, handoff, research) would otherwise contaminate the Review agent's staged diff, get swept into phase commits by `git add -A`, and trip the dirty-tree check below. Without touching the repo's tracked `.gitignore`, add its `scratch/` root (`<scratch_root>`, e.g. `.agents/scratch/` or `.claude/scratch/`) to git's local-only ignore list:

```bash
git check-ignore -q "<scratch_dir>/probe" || echo '<scratch_root>/' >> "$(git rev-parse --git-path info/exclude)"
```

(Appending to `.git/info/exclude` is idempotent for this run's purposes, invisible to the repo's history, and skipped by the guard in repos that already ignore the path. Skip this step entirely for the `${TMPDIR}` fallback, which lives outside the repo.)

**Reload the prior record.** If `<scratch_dir>/tree-state.md` exists, an earlier run of this plan already triaged the tree. Reload every `keep-dirty:` entry that `git -c core.quotePath=false status --porcelain -uall` still shows as dirty into `<keep_dirty_pathspec>` — comparing paths only after unquoting the porcelain side (it C-quotes paths containing spaces, quotes, or backslashes; a naive string match silently drops exactly those entries). Drop entries — `keep-dirty:` and `input:` alike — that are genuinely no longer dirty and rewrite the file to match (the user has since handled them); when a match is merely uncertain, keep the entry. Reload any `inputs-commit:` sha into `<inputs_commit_sha>`. Those entries are the user's own recorded answers: honoring them is what stops a resume from re-asking, or worse, treating the user's files as unexplained dirt.

**Keep-dirty paths.** Files that must stay modified in the working tree but never be committed (a common shape: running a plan while iterating on the harness or steering docs themselves, or carrying local-only config edits). Step 1e.2a's triage is what records them as `<keep_dirty_pathspec>` — `':(exclude)<path>'` pathspec entries. Four consequences for the rest of the run: (1) their `git status` entries are expected dirt — disregard them in every dirty-tree evaluation in this step, and never revert or delete them in the discard path below; (2) every `git add -A` in this skill becomes `git add -A -- . <keep_dirty_pathspec>` (the staging sites in Step 4 items 5 and 7), so these paths can never reach a phase commit or a reviewer's staged diff — and before ANY `git add -A` where `<keep_dirty_pathspec>` is unset, confirm `<scratch_dir>/tree-state.md` is absent or lists no `keep-dirty:` entries; if entries exist, re-read working-tree.md and rebuild `<keep_dirty_pathspec>` from them per its quoting and rename rules before staging anything (a compacted context loses the in-memory value; the file is the authority); (3) Step 3's write-scope check uses its snapshot-and-compare form, since the tree is legitimately dirty from run start; (4) any agent brief whose File Manifest includes a keep-dirty path must say the file carries the user's uncommitted edits — edit surgically, never rewrite wholesale.

Then run `git -c core.quotePath=false status --porcelain -uall` (`-uall` lists files, never collapsed directories — every prompt below must show the user files; with keep-dirty paths declared, disregard their entries — they are expected). If any output, first test for an **interrupted phase** before triaging. The test requires a **tracked** plan file: if `git ls-files --error-unmatch <plan_file_path>` fails (a consumer that git-ignores its plans directory never commits checkbox edits by construction), skip the test — its comparison would read every checked criterion as uncommitted and un-check all of them, a destructive false positive — note that interrupted-phase detection is unavailable (Step 1c's GH-body reconciliation is the cross-run record), and go straight to Step 1e.2a below. Otherwise compare the working-tree plan file against the tip of the branch phase commits land on (`plan/<plan_slug>` if it exists; the current branch under `--no-branch`) via `git diff <that-branch> -- <plan_file_path>` — if the file is absent there, treat every checked criterion as uncommitted. Criteria checked in the working tree but not in that committed version mark a phase whose checkboxes were recorded (Step 4.6) but whose commit (Step 4.7) never landed. If such criteria exist AND the tree is dirty beyond the plan file itself:

1. Un-check those criteria in the local file. In GH mode with sync active, push the corrected body (`gh issue edit <plan_sub_issue_number> --body-file <plan_file_path>`), retrying 3× with backoff; on persistent failure abort loudly rather than degrade — this push is what prevents Step 1c from resurrecting the phantom ticks on a later resume.
2. Surface, listing every path the choice applies to (the dirty set minus `<plan_file_path>` and reloaded keep-dirty paths): `Phase <n> was interrupted after its checkboxes were recorded but before its commit landed. Criteria un-checked. The working tree holds its partial work in: <paths> — discard and re-attempt the phase from scratch, keep the partial work for the re-attempt, or abort?` Act only on an explicit `discard`, `keep`, or `abort`; anything else → re-prompt once, then abort with the tree unchanged — silence or vagueness never selects the destructive option. On discard, unstage and revert those listed tracked paths and delete the listed untracked files — never `<plan_file_path>` (it keeps its just-corrected content) and never a `<keep_dirty_pathspec>` path (the user's own work). The reload explains only the dirt a prior run resolved; anything newer is indistinguishable from phase work — which is exactly why every path is listed and an explicit `discard` is required before anything is touched. On keep, the listed paths are the phase's own tree state: leave them in place to re-enter the re-attempted phase's staging and commit — they are NOT triage material for Step 1e.2a (keep-dirty would exclude the phase's files from its own commit; input would commit unreviewed code as user prose).

**Step 1e.2a — Triage the remaining dirt.** Reached only when dirt remains that nothing above explains: not a reloaded keep-dirty entry, not the interrupted phase's partial work (kept or discarded — item 2 owns that dirt either way), not the plan file's just-corrected content. If no such dirt exists, skip to Step 1e.3. Otherwise a dirty tree does not stop the run and never costs the user work: **read [references/working-tree.md](references/working-tree.md) now and follow it.** It asks which paths are this work's input, records the rest as keep-dirty, and owns Step 1e.4's commit procedure — which is deferred until after Step 1e.3 has settled the branch, so do not run it on arrival. Never improvise a resolution from SKILL.md alone.

**Step 1e.3 — Branch handling:**

**If `--no-branch` was passed:** Step 1e.1 already cleared the base-branch refusal, so leave the current branch as the working branch (do NOT set `<branch_name>` — its absence in working state signals "no dedicated branch was created").

**Otherwise (create the work branch):**

1. Compute `<branch_name>` as `plan/<plan_slug>` (e.g. `plan/mui-v9-migration`)
2. **Branch already exists handling:**
   - **Exists locally with commits ahead of base AND plan has some checked criteria** → resuming a prior interrupted run; `git checkout <branch_name>`, continue
   - **Exists locally with no commits ahead of base** → `git checkout <branch_name>`, continue (no harm). But if the plan shows checked criteria, surface first: `Plan records completed phases but <branch_name> has no commits ahead of <base_branch> — those phases' code is not on this machine (likely unpushed commits elsewhere). Re-attempt them here / abort so the original branch can be pushed first?` (A phase that legitimately produced `(no commit — no changes)` can trigger this — which is why it surfaces to the user instead of auto-resolving.)
   - **Exists locally with commits ahead BUT plan has no checked criteria** → surface to user, naming the commits (`git log <base_branch>..<branch_name> --oneline`): `Branch <branch_name> exists with commits but plan shows no progress. Use existing / recreate / pick different name?` An earlier run that committed declared inputs (Step 1e.4) then stopped at Step 2's gate produces this state legitimately. **`recreate` is destructive — an inputs commit holds files the user wrote and never committed elsewhere, so say plainly that recreating removes them from the working tree and leaves them reachable only via reflog, and require confirmation after the user has seen the commit list.** Then `git checkout <base_branch>` first (`git branch -D` refuses while the branch is checked out, and this run may already be on it), then `git branch -D <branch_name>` and `git checkout -b <branch_name> <base_branch>`, and delete any `inputs-commit:` line from `<scratch_dir>/tree-state.md` — that commit no longer exists, and a reloaded stale sha would misreport in Step 2. If that first checkout fails on any dirty path, stop the same way as the rule below — surface the error verbatim, nothing forced, nothing yet deleted.
   - **Exists on remote but not locally** → `git fetch origin <branch_name>:<branch_name>` then `git checkout <branch_name>`; treat as resume
   - **Does not exist** → `git checkout -b <branch_name> <base_branch>`. A fresh branch has zero commits ahead by construction, so the same checked-criteria-but-no-commits guard applies: if the plan shows checked criteria, surface the same prompt before proceeding

Every `git checkout` above can fail on dirty paths — declared ones, kept partial work, or the plan file's just-corrected content. Surface the error verbatim and stop: no commit has been made and no file content has changed (any triage unstaging was index-only). Never force (`-f`), never stash past it, never re-point the branch to make it succeed. (working-tree.md's Checkout section says the same — this rule must hold even when that file was never loaded.)

**Step 1e.4 — Commit the declared inputs.** Skip when `<precommit_pathspec>` is unset — always the case if working-tree.md was never read. It must run here, before Phase 1, so its commit stays out of every phase commit and reviewer diff. Procedure: [references/working-tree.md](references/working-tree.md) → Step 1e.4.

### Step 2 — Present the Execution Plan

**Pre-step: load agent operations reference.** Read [references/agent-operations.md](references/agent-operations.md) now — before composing the phase summary below. It contains the full agent-mode definitions and per-section brief content used throughout Step 3 onward. Keep it in working memory for the rest of the run; if it is no longer verbatim in context later in the run (compaction), re-read it before composing any brief. Then write `<scratch_dir>/run-conventions.md` per Brief composition's standing-directives rule — before any brief is composed.

Then output:

1. **Branch info** (if branch was created in Step 1e): `Working on branch '<branch_name>' based on '<base_branch>'.`
2. **Working-tree resolution** — **unconditional; never nest under item 1**, because Step 1e.4 runs whether or not a branch was created and under `--no-branch --allow-main` commits to `<base_branch>` itself. Report whichever apply, naming the branch committed to: `Committed <n> declared input file(s) to '<branch>' as <inputs_commit_sha>.` / `Leaving <n> keep-dirty path(s) uncommitted for the whole run.` / `Declared inputs were already committed by a prior run (<inputs_commit_sha>).` (Step 1e.4's cleared-pathspec case, or a reloaded `inputs-commit:` sha; with no sha on record — the user committed them between runs — say `in an earlier commit` instead). Silent only when the tree was clean and nothing was reloaded. It precedes item 6's gate, so if the user declines there: when THIS run made the inputs commit (it is HEAD), say it is already on the branch and `git reset --mixed HEAD~1` returns those files to the working tree unstaged; when the sha was reloaded from a prior run, first confirm it is still on the branch (`git merge-base --is-ancestor <sha> HEAD`) — a declined gate's reset makes it reflog-only, so on failure delete the stale `inputs-commit:` line and report no inputs commit — then just name it; never offer the reset, other commits sit on top of it.
3. **Resumability note**: if some acceptance criteria are already checked, list which phases appear complete and confirm with the user whether to skip them.
4. **Phase summary** — total number of phases identified; for each phase: title, brief description, and which agent mode it will use
5. **GH integration note** (if GH mode): `GH-backed run — progress will sync to issue #<plan_sub_issue_number> after each phase. PR will be opened on completion (omit with --no-pr).`
6. Ask the user to confirm before proceeding.

### Step 3 — Research

Before implementation begins, spawn Research agents to gather codebase context. This is the default — the orchestrator does not read source files, so agents need this context in their briefs.

**Identify research topics** by scanning the plan for:

- Files, modules, or directories referenced
- APIs, types, or interfaces that phases will consume or modify
- Existing patterns that phases need to follow or extend
- Dependencies between phases that require understanding current state

**Consolidate before spawning.** Default to 2–4 research agents per run — needing more is a consolidation signal, not a bigger fan-out. Split topics by the *mental model required*, never by phase or by directory, and merge topics whose findings depend on each other: two agents each half-reconstructing one shared model (say, how the session layer and the route guard interact) is the anti-pattern this rule exists to prevent.

**Pick each topic's tier by its findings' destination** (the two tiers are defined under the Research mode in agent-operations.md), decided when the topic is composed — never by guessing output size:

- **File-backed (`general-purpose`) — the default.** Any phase brief will point at this topic's `research-<topic>.md`, or the topic serves more than one phase. Resolve the concrete file path now (suffix it if the name is already taken), pass it in the brief along with the Write Scope & Search Breadth section, and the agent writes the file itself, returning only a ≤8-line digest plus the path. The full findings never enter your context.
- **Inline lookup (`Explore`) — the exception.** The complete answer is expected to fit the ≤8-line digest and exactly one consumer needs it: inline the returned digest into that single brief as a phase-specific delta (or into your own next decision) — no file is created. If the return shows the size was misjudged, persist it verbatim to `<scratch_dir>/research-<topic>.md` and do not re-read it; a repeat miss means the topic was a survey, not a lookup — file-backed next time.

**Spawn research agents in parallel** when topics are independent. For example, if Phase 1 touches the routing layer and Phase 3 touches the API client, spawn two Research agents simultaneously — one for each area. Research never modifies the repo in either tier, so parallel execution is safe and reduces wall-clock time.

**Verify the write scope after every file-backed return.** Step 1e.2 resolved the working tree and the scratch dir is git-ignored, so on a run that began Step 3 with a clean tree, `git status --porcelain` must return empty. Any output means the agent wrote outside its scope: revert those paths and surface the violation to the user before proceeding. (For mid-run research — Error Handling item 4 — the tree legitimately holds phase work: snapshot `git status --porcelain` before the spawn and compare after instead. Use the same snapshot-and-compare form whenever the tree was NOT clean when Step 3 began — `<keep_dirty_pathspec>` declared, kept partial work, or plan-file dirt riding normal staging — those states keep the tree legitimately dirty from run start, and only the snapshot delta is a violation.)

**Skip this step only** if the plan is trivially simple (e.g., a single-phase config change with no codebase dependencies).

### Step 4 — Execute Phases

Capture `<run_start>` once (`date +%s`) — for the optional, clearly-labeled "elapsed (includes pauses)" line ONLY, never the headline duration; capture it at Step 3 instead when research runs, so the figure covers the whole run. Initialize the run ledger now if Step 3 did not already (see Run Ledger): create `<ledger_path>` with its header row. All reported timing comes from the ledger's summed `duration_ms`, never wall-clock `date` diffs across turns (idle-immune — see Run Ledger).

For each phase, sequentially:

1. **Begin the phase** — no wall-clock capture. This phase's time and cost are derived from the ledger rows its sub-agents produce (item 8), which is idle-immune.
2. **Compose the brief** — see Brief Composition Rules
3. **Spawn the agent** — see agent-operations.md → Agent Modes (full definitions) for which to use
4. **Receive the summary and record its usage row** (see Run Ledger — append a ledger row for EVERY sub-agent return, this step and every other). Analyze the result for success, failures, or concerns. If the summary reports a **blocking** failure, route through Error Handling **now** — before the review gate — and enter item 5 only once the blocking failure is resolved (a verified Debug fix counts; it need not produce a new Code summary). Fixes must land before the phase is reviewed and committed, never after.
5. **Stage and review the phase** (Code-mode phases only; skip if `--no-review` and note the skipped gate in the progress tracker):
   - Stage the phase's changes now: `git add -A` (with keep-dirty paths declared: `git add -A -- . <keep_dirty_pathspec>` — Step 1e.2). Staging before the review makes new untracked files visible to the reviewer's `git diff --cached` and freezes exactly what the verdict applies to.
   - Before every Review spawn for this phase — initial, re-review, or re-spawn — resolve that spawn's own evidence path (`phase-<n>-review.md` for the phase's first review, then `-2`, `-3`, … per later spawn — derive the suffix from disk, never memory: highest existing `phase-<n>-review*.md` suffix + 1, via `ls`; state the path in the brief) and `rm -f` exactly that path: a stale file there from an aborted run would falsely satisfy the existence check below. Then spawn a **Review** agent (see agent-operations.md → Agent Modes) using the dedicated Review brief there. Do NOT include the Code agent's summary or self-assessment in the brief — the reviewer's independence from the implementer's self-report is the point of the gate.
   - Receive the verdict lines and findings (the full evidence table lands at the evidence path this spawn was given — never inline; see the Review mode's return split). Confirm the file at that path exists (`ls` — never read it) before routing — except on a scoped re-review's `ESCALATE` return, which carries no verdicts: `rm -f` the escalated spawn's evidence path (partial evidence is not an audit record) and route straight to a fresh full Review agent (agent-operations.md → Scoped Re-review Exceptions). A verdict return without the file is an incomplete review: re-spawn the reviewer once (counts against no budget); a second miss escalates to the user. Then route:
     - **All criteria MET** → proceed to item 6.
     - **Any NOT MET** → treat as a blocking failure (see Error Handling): re-attempt via a Code agent whose retry brief includes the reviewer's NOT MET findings verbatim; counts against the phase retry limit. After the fix, re-run the review with a fresh Review agent — full by default, scoped only when the invariant's narrow exceptions below apply; verdicts are never carried over without a re-review.
     - **NEEDS-RUNTIME** → proceed, but tag those criteria in the progress note and carry them to Step 5's caveats list and the PR Test plan (see completion-templates.md).
     - **Scope creep flagged** → judge it: out-of-plan refactors route to a fix like NOT MET; benign additions (e.g. an import the manifest missed) are noted and allowed.
     - **Out-of-criteria defects reported** → judge severity: a blocking defect routes to a fix like NOT MET (counts against the retry limit); a non-blocking defect worth fixing before it ships in this phase's commit takes a corrective pass (see Error Handling → Corrective-pass budget); anything else is noted and carried forward (item 10).
   - **Invariant:** the Review agent is the last thing to see the phase's diff before checkboxes are ticked (item 6) and the commit happens (item 7). Any modification after the verdict that can reach the commit — a Debug fix, a retry, anything except item 6's own plan-file checkbox edit — invalidates it: re-stage and re-run the review in full with a fresh agent before proceeding. (The commit-message scratch file never reaches the index — Step 1e.2 git-ignores it — so it cannot invalidate a verdict.) Two narrow exceptions can scope — never skip — the re-review: a post-verdict delta confined to dependency/generated artifacts, or one confined to test files and declared-comment-only production files — dependency/generated artifacts allowed alongside when they meet Exception 1's own conditions (the scoped reviewer verifies the declaration and escalates to full if it fails). Their conditions, the baseline-extraction step that transmits the delta to the scoped reviewer, and the scoped brief variant live in agent-operations.md → Scoped Re-review Exceptions. Timing is load-bearing: the baselines must be extracted BEFORE re-staging — the index preserves the verdict-time state only until `git add` runs — so consult that section the moment a scoped path looks applicable. For both exceptions: record the scoped review as a deviation in the progress note. The re-review still goes to a **fresh** Review agent — only its scope narrows, never its independence. When in doubt, full.
6. **Update the plan file** — Edit the local plan file ALWAYS to check off acceptance criteria the Review agent verified as MET (when the review gate was skipped, fall back to the Code agent's self-report — on the Debug path, as amended by the Debug agent's verified-fix report, since the last Code summary is the one that declared the failure; NEEDS-RUNTIME criteria are checked but tagged in the progress note), regardless of GH mode. **(GH mode, `gh_sync_mode == active` only)** After the Edit, sync to GitHub: `gh issue edit <plan_sub_issue_number> --body-file <plan_file_path>`. Retry 3× with backoff (250ms, 1s, 3s) on failure. On persistent failure, escalate to the user **once** with three options:
   - `retry` — try the sync again now (e.g. user just refreshed `gh auth`)
   - `continue` — set `gh_sync_mode = degraded`; skip per-phase sync for the rest of this run; one final sync attempted at end-of-run
   - `abort` — stop the run; user can resume via re-invocation

   **(GH mode, `gh_sync_mode == degraded`)** Skip the sync; note the degraded state in the next progress tracker output.

7. **Commit the phase's changes:**
   - `git add -A` (with keep-dirty paths declared: `git add -A -- . <keep_dirty_pathspec>` — Step 1e.2; picks up the plan-file checkbox edit; when the review gate ran, the code is already staged from item 5 — otherwise this stages it now)
   - Check `git diff --cached --quiet`; if exit code 0 (no staged changes) → skip the commit and note `(no commit — no changes)` in the progress tracker for this phase
   - **Fast path** — if the Code agent wrote its commit-message file (`<scratch_dir>/phase-<n>-commit-msg.md`, per the Commit Message Directive) AND no agent modified the phase's code after that Code agent finished (no Debug fix, no retry): first check the file's first line — a code fence (```) is never legitimate message content and would become the commit subject verbatim, so strip leading/trailing fence lines in place. Then commit and clean in one step: `git commit -F <message-file> && rm <message-file>`. If the commit-msg hook rejects the message, discard the file and use the fallback below. The fast path keeps the phase diff out of the orchestrator's context — the agent that wrote the diff authored the message.
   - **Fallback** (message file missing, post-agent changes occurred, or hook rejected the message) — invoke `Skill(skill="commit", args="#<plan_sub_issue_number>")` (pass `args="--no-ticket"` if local-only mode — an omitted argument would let the skill infer a ticket this run deliberately has none of). The `commit` skill is the single source of truth for commit message format and type selection — do NOT duplicate format guidance here (the fast path's message file is itself authored against that skill). If a commit-msg hook rejects the fallback's message too, that is a message problem, not a code problem: re-author the message against the hook's output and retry the commit once — the diff is unchanged, so no Debug agent, no review re-run, and no charge against the phase retry limit; if the re-authored message is also rejected, escalate to the user with the hook output.
   - **Pre-commit hook failure** — spawn a Debug agent with the hook output, files involved, and what was being committed. After Debug fixes the issue: re-stage (`git add -A`, exclusion form under keep-dirty paths — the fix is not in the index yet; if a scoped exception applies, extract its baselines BEFORE this re-stage — agent-operations.md → Scoped Re-review Exceptions), then re-run the review gate with a fresh Review agent per item 5's invariant (the fix changed the diff; skip only when the gate is skipped for this run). If the re-review returns any NOT MET: first re-run item 6 in full against the new verdicts — un-check the criteria no longer MET (be explicit: remove those ticks) and, in active mode, re-sync to GH with item 6's retry/escalation machinery, so neither the local file nor GH overstates progress; then route through item 5's NOT MET path (counts against the phase retry limit) — never directly to the commit; the re-attempted phase's eventual commit starts a fresh two-attempt count. Otherwise — including when the gate is skipped for this run (no re-review, no verdicts to reconcile) — reconcile any MET ↔ NEEDS-RUNTIME drift by re-running item 6 in full (same Edit and sync rules), then retry the commit via the fallback path (a Debug fix invalidates the fast path). If the second attempt fails, escalate to the user with full context. **Never bypass hooks with `--no-verify`.**
   - **Delete the phase's scratch files** once the commit lands: the message file (`rm -f <scratch_dir>/phase-<n>-commit-msg.md` — the fast path's `&& rm` already did this; the fallback must do it here) and any scoped-review baselines (`find <scratch_dir> -maxdepth 1 -name 'baseline-*' -delete` — never a bare `rm` glob: in zsh an unmatched glob aborts the whole command line, and a deletion bundled onto it then silently keeps the stale message file). A stale message file left by an aborted run would otherwise satisfy a later run's fast-path check and commit that phase with an outdated message; a stale baseline would hand a later scoped re-review the wrong delta.
8. **Compute phase active time + cost from the ledger** — from this phase's ledger rows, sum `duration_ms` (→ **active time**, `h:mm:ss`; parallel groups contribute their **max**, not sum — see Progress Reporting) and carry each row's `subagent_tokens` into the **Research / Code / Review** columns as its own figure (placed by mode per Progress Reporting, never summed together; **Total** = the phase's sum across all rows). Active time is idle-immune (see Run Ledger). A phase that spawned a Debug agent and a re-review includes those rows in its totals. (Orchestrator-side heavy commands — e.g. the commit's pre-commit hook — are excluded by default; to count one, bracket ONLY that command inside a single bash call — `s=$(date +%s); git commit …; e=$(date +%s)` — which cannot absorb user idle mid-command.)
9. **Report progress** — output the progress tracker (see Progress Reporting), including the formatted duration
10. **Carry non-blocking concerns** — blocking failures were already handled at item 4, before the review gate; note any remaining non-blocking issues from the summary or review in the progress output and carry them forward as context. Every carried defect ends in one of two places, never implicitly dropped: assigned to a later phase that already touches the same file — listed in that phase's Code brief as a **pre-authorized cleanup** AND named as sanctioned in its Review brief; omitting either is a brief-composition error, since the reviewer will read the unnamed cleanup as scope creep — or recorded in the final report and, where applicable, the PR's Review notes. Only polish-class defects (house style, naming, comments, formatting — never behaviour) ride a later phase this way, at no corrective-pass cost; a defect carried because its phase exhausted a budget takes the report route only, and a cleanup the later phase's reviewer reports unapplied reverts to carried status. Under `--no-review` no reviewer exists to verify application, so the assignment route is unavailable — carried defects take the report route only
11. **Proceed** to the next phase, carrying forward relevant context from the summary

### Step 5 — Completion

After all phases:

- **Classify the run first** — set `<outcome>` per its definition in Working state. Every gate below keys off it, so decide it once, explicitly, before composing anything
- Output a final summary of what was accomplished across all phases. Render the final completion table from the ledger (one row per sub-agent grouped under its phase, with phase subtotal lines and a Totals row — format in completion-templates.md, load it now), then a **Total active time** (the subtotal lines summed — idle-immune, parallel groups counted at their max) and total tokens. Optionally add one **Elapsed** line (`now − <run_start>`, `h:mm:ss`) explicitly labeled as including any pauses/idle — never present that wall-clock figure as the run's "duration"
- List any caveats, manual steps, or follow-ups
- Note any acceptance criteria that remain unchecked
- **If `<keep_dirty_pathspec>` is set:** name those paths — they are still uncommitted, were excluded from every phase commit, and are absent from the PR
- **Local-only runs (and only these):** state plainly that the work branch was never pushed and give the command — `git push -u origin <branch_name>`. Everything below this point is GH-mode only, so a run that just ends here would otherwise read as "nothing left to do"

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

Skip if `--no-branch` was passed (no dedicated branch to push).

This step sits inside the GH-mode block **deliberately** — do not "fix" it by hoisting it out. A push is not a neutral local git operation: in a `<pr_open_mode> == declared` repo it is precisely what causes a PR to be opened, so a run the user scoped to local-only must not touch the remote at all.

Run: `git push -u origin <branch_name>`

If the push fails (branch protection, network, auth, force-push needed):

- Surface the error verbatim
- **Do NOT auto-force-push.** Skip Step 5d and instruct the user to resolve the push manually before opening a PR

#### Step 5c.5 — Pre-PR branch review

Skip if `--no-branch-review`, or if Step 5d will be skipped anyway (`--no-pr`, `--no-branch`, push failed in Step 5c, Step 5a's final sync failed). This gate exists to populate a PR body — never spend a branch-scope Review agent when no PR will be opened.

Spawn ONE fresh Review agent at branch scope (see the Review Brief's pre-PR variant in agent-operations.md), briefed to:

- Adversarially review the branch diff for correctness bugs — especially the integration seams between phases, which no per-phase gate can see. **Scope it past the inputs commit — never past phase work:** when `<inputs_commit_sha>` is set AND it is the first commit ahead of base (`git rev-list --first-parent <base_branch>..HEAD | tail -1` prints it), the brief's diff instruction uses `git diff <inputs_commit_sha>...HEAD`, not `git diff <base_branch>...HEAD` (state the substituted ref explicitly in the brief — agent-operations.md's pre-PR variant carries the `<base_branch>` default). A mid-branch inputs commit (a resume committed inputs on top of earlier phases) keeps the `<base_branch>` ref — scoping past it would silently drop every earlier phase from the review — and is instead named in the brief as out of scope. Either way the inputs files are the user's own prose and this gate's routing offers autonomous fixes, so a finding against them is unactionable by construction
- Check that forward-compatibility hooks named in phase summaries (list them in the brief) were actually resolved by later phases
- Verify each candidate finding against the code before reporting; return only surviving findings as a structured list

This gate is **detection-only** — never spawn fix agents from its findings autonomously; fixes happen only when the user picks that option in the routing below. The rule is load-bearing, not caution: a branch-scope finding often sits in the gap between what the plan says and what the user actually meant — a plan can even contradict itself — and only the user can say which behaviour was intended. An autonomous fix at this stage can ship the wrong mechanism fully implemented, tested, reviewed, and green; routing the finding to the user is what surfaces intent. Routing:

- All surviving findings go into the PR body's `Review notes` section (see completion-templates.md)
- If any finding is a CONFIRMED correctness bug: open the PR as **draft** instead of ready and surface the findings to the user with options — direct fixes (normal Debug/commit flow, re-push, promote) or promote as-is

#### Step 5d — Submit the PR

Skip if any of: `--no-pr`, `--no-branch`, push failed in Step 5c. **When this step is skipped and `<pr_open_mode> == declared`, say so in the final summary** — the Step-5c push already triggered the repo's workflow, so a PR exists carrying the workflow's auto-generated body, and run-plan deliberately left it untouched. (`--no-pr` cannot prevent that PR from existing; it only means run-plan does not attach its body.)

Load [references/completion-templates.md](references/completion-templates.md) if not already loaded — it contains the PR body template, draft-vs-ready rule, the PR submission flow (gated on `<pr_open_mode>` from Step 1d: `declared` → poll for the workflow's PR and attach the body via `gh pr edit`, never `gh pr create`; `silent` → `gh pr create` directly), and the PR failure-handling guidance. Use it to compose and submit the PR.

On success: report the PR URL to the user.

#### Step 5e — Delete the local plan and PRD files

Run only if ALL of the following hold: GH mode (`<plan_sub_issue_number>` is set); run outcome is `complete` — not `partial` or `aborted` (partial runs need the file for resumability); Step 5d submitted the PR successfully (skipped or failed → keep the files — without a merged PR, the local file is still the most complete working copy).

When all three hold, follow completion-templates.md → Local file cleanup (Step 5e) — already loaded by Step 5d. It owns the two keep-exemptions, the PRD-file checks, the deletion procedure, and the final-summary wording. Never delete a tracked or keep-dirty file, and never improvise the deletion from SKILL.md alone.

---

## Agent modes

Five modes — **Research** (two tiers: file-backed `general-purpose`, the default / `Explore` inline lookup; tier picked in Step 3), **Code**, **Architect**, **Debug**, **Review** (all `general-purpose`; Research's file-backed tier and Review are read-only toward the repo *by conduct*, not by capability). Full role definitions, protocols, and expected outputs: [references/agent-operations.md](references/agent-operations.md) → Agent Modes (full definitions), loaded once at Step 2 — before any mode decision. On a host without these agent types, map by capability, not type name: inline-lookup Research → read-only worker; every other mode → general-capability worker — and Review keeps the same model tier as Code, never a smaller one.

---

## Brief composition (skeleton)

Every agent brief MUST include these 10 sections, in order:

1. **Role Preamble** — the mode's role definition
2. **Codebase Context** — decisions, prior findings/summaries, AGENTS.md/CLAUDE.md directive
3. **File Manifest** (Code mode) — files to modify (must-read-first) and to reference
4. **Scoped Task** — phase description + acceptance criteria, verbatim
5. **TDD Directive** (Code mode only)
6. **Build Verification Gate** (Code mode only)
7. **Commit Message Directive** (Code mode only) — author to the scratch message file; never commit
8. **Write Scope & Search Breadth** (file-backed Research tier only) — one sanctioned write; search very thoroughly
9. **Completion Requirement** — the structured summary template
10. **Boundary Statement** — "only do what's in scope"

For the exact text of each section (prose, directives, completion template), see [references/agent-operations.md](references/agent-operations.md). This skeleton is the forcing function — the reference file is the full content.

**Standing directives are written once, not re-sent in every brief.** At Step 2's pre-step, write `<scratch_dir>/run-conventions.md` holding the run-static brief content, each block headed by the modes it binds — `All modes:` sections 9 and 10, section 2's static directives (the AGENTS.md/CLAUDE.md read directive and extracted project conventions), and, when keep-dirty paths are declared, this warning naming them: `These paths carry the user's uncommitted edits and stay uncommitted all run: <paths>. Never revert, delete, or commit them.`; `Code mode only:` sections 5–7's full text (ticket form resolved; retry Code agents included, Debug agents excluded); `Code and Debug modes only:` the documentation budget. (Consequence 4's per-file surgical-edit note is NOT run-static — it stays inline in each brief whose File Manifest includes a keep-dirty path.) Each skeleton brief then covers its mode's blocks with a single line — `Read <scratch_dir>/run-conventions.md in full before starting; the blocks labeled for your mode are part of this brief.` — while the phase's concrete resolved paths (commit-message file, handoff file) and everything phase-specific (role preamble, File Manifest, verbatim criteria, deltas) stay inline. Review briefs never use the conventions file — their dedicated composition stays fully inline. On a resume, rewrite the file at Step 2 rather than trusting a prior run's copy (ticket form or keep-dirty facts may have changed).

**Before spawning any agent, verify the brief contains all 10 sections** — inline, or covered by the run-conventions.md pointer for the file-carried ones; a pointer-covered brief must still name its concrete resolved paths (commit-message file, handoff file) inline, and both that and `run-conventions.md`'s existence on disk (`ls`) are verified here too (or all that apply to the mode — File Manifest, TDD Directive, Build Verification Gate, and Commit Message Directive are Code-mode-only; Write Scope & Search Breadth applies only to file-backed Research). **Exception:** Review agents use the dedicated Review Brief composition in agent-operations.md, not this skeleton.

**Keep briefs thin — reference, don't re-embed** (full rule: agent-operations.md §2). Cite the plan section, research files, and prior handoffs by name/path — never paste their contents; inline only the phase's verbatim acceptance criteria and phase-specific deltas. The brief is YOUR output, re-sent as input on every later turn — re-embedding is the orchestrator's biggest self-inflicted context cost.

---

## Context Discipline

**You are the orchestrator. Stay lean.**

- **DO NOT** read source code files — delegate that to agents
- **DO NOT** read phase diffs — the Review agent reads them (Step 4.5); you receive only its verdict lines and findings (the two sanctioned exceptions both run the `commit` skill inline, which reads the staged diff: Step 4.7's fallback commit path, and Step 1e.4's declared-inputs commit)
- **DO NOT** run tests, builds, or linters — delegate that to agents
- **DO NOT** implement code changes — delegate that to agents
- **DO** read the plan file (once, at the start)
- **DO** load [references/agent-operations.md](references/agent-operations.md) once at Step 2 and keep it in working memory for the whole run (agent modes + brief content for every phase)
- **DO** load [references/working-tree.md](references/working-tree.md) at Step 1e.2a — but ONLY when unexplained dirt remains there (Step 1e.2a's own condition). A clean or fully-explained tree never needs it
- **DO** load [references/completion-templates.md](references/completion-templates.md) at Step 5 when rendering the final completion table and composing the summary comment and PR body (it also owns Step 5e's file-cleanup procedure)
- **DO** use the Edit tool to update plan checkboxes after phases complete (and `gh issue edit` to sync to the issue body when GH-backed)
- **DO** create the work branch (Step 1e), commit phase changes (Step 4.7), push the branch and open the PR (Step 5c–5d) — these git/GH operations are the orchestrator's responsibility, not the agents'
- **DO** commit via the Code agent's message file when the fast path applies (Step 4.7) — it keeps the phase diff out of your context; invoke the `commit` skill otherwise, and do NOT duplicate commit format guidance in this skill
- **DO** record every sub-agent's `<usage>` block into the run ledger the moment it returns (see Run Ledger), and derive ALL reported timing from summed `duration_ms`, never wall-clock `date` diffs (idle-immune — see Run Ledger)
- **DO** broker file paths, not content — research findings live in `research-<topic>.md` (written by the file-backed Research agent itself) and each phase's downstream detail in `phase-<n>-handoff.md`, both read directly by the NEXT agent; each review's MET evidence lives in `phase-<n>-review.md`, an audit record nothing re-reads during the run, so keep only judgment-relevant summaries (status, criteria, issues, deviations, précis) in your own context (exception: inline-lookup Research returns arrive inline by design; an oversized one is persisted to `research-<topic>.md` and never re-read — Step 3)
- **DO** output progress updates between phases
- **DO** carry forward only judgment-relevant context: keep each phase's terse returned summary (status/criteria/issues/deviations/précis) as the record of what happened (the ledger holds the cost/time record); the detailed inter-phase handoff lives in `phase-<n>-handoff.md`, which the next brief points its agent to read — you don't hold that detail yourself
- **NEVER** bypass pre-commit hooks (`--no-verify`, `--no-gpg-sign`, etc.) — investigate and fix the underlying failure via a Debug agent

If a phase summary is excessively long, extract only the information needed for subsequent phases.

---

## Run Ledger

Maintain an append-only ledger at `<ledger_path>` (`<scratch_dir>/ledger.md`) — the single source of truth for per-sub-agent cost/time and the data the Progress Reporting table and completion summary render from. Because it is a file, it survives context compaction: late-run reporting stays accurate even after early phases are summarized out of your context.

Initialize it before the run's FIRST sub-agent spawn — that is Step 3 when research runs, Step 4 otherwise. Do not defer it to Step 4 unconditionally: Step 3's research agents return before Step 4 begins, and a row with nowhere to land is a row held in context instead, which is exactly the `setup (research)` data most likely to be summarized away later. **Every time ANY sub-agent returns** — Research, Code, Architect, Debug, Review; every step including retries, the Debug → re-review cycle, the pre-PR branch review, and post-run follow-ups — append one row from its `<usage>` block:

| Phase | Mode | Tokens | Tool uses | duration_ms | Parallel group | Note |
| ----- | ---- | -----: | --------: | ----------: | -------------- | ---- |
| 1 | Research | 68217 | 41 | 113266 | R1 | shared video layer |
| 3 | Research | 59404 | 36 | 98112 | R1 | api client surface |
| 1 | Code | 151579 | 84 | 3057245 |  |  |
| 1 | Review | 78097 | 32 | 350528 |  | all MET |

- **Tokens** = `subagent_tokens`, **Tool uses** = `tool_uses`, **duration_ms** verbatim; **Parallel group** is blank for a solo spawn, and rows spawned concurrently in one batch share a short label (`R1`, `R2`, …) — reported at the group's max, not its sum (see Progress Reporting). Record raw numbers; format only at render time, each row's Tokens as its own figure, never summed (see Progress Reporting).
- Attribute whole-run research to the phase it serves (or `setup`); the pre-PR review to `pre-PR`; post-run fixes to `followup`.
- **`subagent_tokens` is cumulative tokens the agent processed across its internal turns — throughput, not peak context occupancy.** Report it as throughput; do NOT present it as "% of context window" (a long agent can process far more than the window without ever occupying it). Per-agent tokens are a **cost** signal; `tool_uses` is the closest available **occupancy** proxy — nothing evicts within a single sub-agent, so its context grows monotonically with tool-using turns, and a 250-call agent ran far closer to its window than a 30-call one whatever their token figures suggest. True peak occupancy is unmeasured on this host.
- **This is a cost ledger, not a context-health ledger.** It records what each sub-agent spent; it says nothing about what stays resident in the orchestrator's own context — that occupancy is unmeasured (no mid-run signal exposes it) and is the cost Context Discipline exists to bound. Do not read a fully-populated ledger as evidence the run was context-lean.
- All reported timing derives from summed `duration_ms` here (parallel groups counted at their max — see Progress Reporting) — never wall-clock `date` diffs across turns, which absorb laptop-closed / dropped-connection / checkpoint-pause idle and misreport (see also Host portability → Time).

**Host portability.** `subagent_tokens` / `tool_uses` / `duration_ms` are Claude Code's Task-tool `<usage>` fields. On another host, record whatever usage metadata its delegation mechanism returns, and degrade **per column** when a field is absent — the ledger, the file-handoff protocol, and the idle-immune-timing *intent* are host-agnostic; only these field names are Claude Code's:

- **Time** — prefer a duration measured by the **agent runner** (idle-immune: it excludes time the orchestrator turn is suspended). If the host exposes none, the orchestrator MAY bracket the spawn with its own clock, but must label it "wall-clock (may include idle)" — an orchestrator bracket absorbs a closed-laptop / dropped-connection pause while the agent runs, which is the whole failure mode we're avoiding. If neither is available, omit the time column.
- **Tokens** — record per-agent tokens if the host exposes them (they power the Research/Code/Review/Total columns); else omit those columns (or write `n/a`). Never fabricate a number. The same per-column rule covers `tool_uses`: record it when exposed, else `n/a`. Even on Claude Code, some agent types emit no `<usage>` block — the read-only `Explore` type behind inline-lookup Research is one — so an inline-lookup row reading `n/a` across tokens and `duration_ms` alongside fully-populated rows is expected behavior, not a ledger bug (file-backed Research runs on `general-purpose`, which reports usage normally).

None of these figures gate control flow (retries are count-based, phases are criteria-gated), so a host exposing no usage metadata still runs the plan correctly — it just reports fewer columns.

The ledger is one of the few artifacts the orchestrator authors directly (like the plan-file checkbox edits). It lives in scratch (git-ignored) and never enters a commit.

---

## Progress Reporting

After each phase, render progress as a **GitHub-flavored markdown table** (it displays cleanly in the user's terminal — prefer it over ASCII box-art), sourced from the run ledger. The **Research / Code / Review** columns hold **per-agent token figures** — the skill's whole architecture exists to keep each individual sub-agent lean, so the table must show each agent's own cost. A per-mode sum defeats the table's purpose: `354K + 113K + 108K` rendered as `575.1K` reads as one enormous agent, the opposite of what happened:

| # | Phase | Status | Research | Code | Review | Total | Active time |
| - | ----- | ------ | -------: | ---: | -----: | ----: | ----------: |
| — | setup (research) | ✓ | 68K·59K·77K·75K | — | — | 280.0K | 0:08:25 (Σ 0:27:08, 4 parallel) |
| 1 | {short title} | ✓ Complete | — | 151.6K | 78.1K | 229.7K | 0:56:48 |
| 2 | {short title} | ✓ Complete (↻ retried) | — | 354K·113K·108K | 125K·119K·120K | 939.2K | 2:41:12 |
| 3 | {short title} | ▶ Current | — | — | — | — | — |

- **Phase** — the phase `#` plus a **short** title, truncated to ~25 chars with `…` when longer. Keep it terse on purpose: the full title already appears in the between-the-table note and the final `Outcomes` list, and an untruncated title is the one thing that can push this table past a terminal's width into ragged cell-wrapping.
- **Research / Code / Review** — each sub-agent's `subagent_tokens` as its **own figure**, dot-separated in spawn order when the phase had several (`354K·113K·108K` — the retry count is visible at a glance). A lone agent keeps one-decimal precision (`151.6K`); multi-value cells drop to whole-K to stay compact. NEVER sum agents into one figure (rationale in the intro above). The two rarer modes are **placed**, not folded: an Architect value lands in the Research column (non-implementing, pre-code) and a Debug or retry value in the Code column (fix cycles on the phase's code), each still listed individually. Upfront Step-3 research is its own `setup` row; a mid-phase Research agent (Error Handling item 4) lands in that phase's Research cell.
- **Total** — the phase's full token cost: every agent figure in the three cells summed (compute from raw ledger values, then format). This is the one place summing is correct — it reconciles the row without impersonating any single agent's size.
- **Active time** — the phase's summed sub-agent `duration_ms` (idle-immune; Step 4 item 8), `h:mm:ss`. Rows sharing a ledger `Parallel group` label contribute the group's **max**, not its sum — summed concurrent durations overstate elapsed by roughly the fan-out factor. Where a group exists, append the labeled sum: `0:08:25 (Σ 0:27:08, 4 parallel)` — the max approximates elapsed, the Σ is the work figure.
- **Status** — `✓ Complete`, `▶ Current`, `· Pending`; append a flag where relevant: `(no commit — no changes)`, `(GH sync degraded)`, `(⚠ needs-runtime)`, `(↻ retried)`.

The **final completion table** switches shape: one row per **sub-agent**, grouped under its phase with per-phase *subtotal* lines — render the ledger's rows (per-agent figures, as above). It is also where `tool_uses` is reported. Format and example live in completion-templates.md, loaded at Step 5.

Read these figures from the ledger — do NOT hand-tally from memory. **Host portability:** the token columns need host-exposed per-agent token counts; without them, drop Research/Code/Review/Total (likewise `Tool uses` in the final table, and Active time if no duration is exposed) per Run Ledger → Host portability — with no usage metadata at all, the table is just `# | Phase | Status`.

Between the table and the next phase, briefly note:

- Key outcome from the completed phase (1-2 sentences)
- Any context being carried forward, and the `phase-<n>-handoff.md` path the next brief will reference
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
   - Spawn a Research agent scoped to the missing context, tier picked by Step 3's destination rule: findings the re-attempt brief will point at are file-destined — resolve the path first, suffixing it if the filename already exists (an earlier brief may point at the original), and the agent writes the file itself; a single missing fact is an inline lookup, inlined into the retry brief
   - For a file-backed spawn, apply Step 3's write-scope check in its mid-run form: snapshot `git status --porcelain` before the spawn and compare after (the tree legitimately holds phase work)
   - Re-attempt the phase with the additional context included
5. **After Debug or retry resolves** — Verify the fix is sufficient, then proceed to the review gate (Step 4.5): post-fix changes are unreviewed by definition, and the gate re-runs before checkboxes are ticked or the phase is committed — full by default, scoped only when Step 4 item 5's narrow exceptions apply. (For non-Code phases, or runs where the gate is skipped, continue directly.)
6. **If resolution fails** — Report to the user with full context and ask for guidance

**Retry limit:** A phase may be retried a maximum of 2 times (original attempt + 2 retries). The limit counts every **failure-driven** fix cycle on the phase — one triggered by a NOT MET verdict or a blocking failure — regardless of route: a Debug intervention (item 3) and an enriched-brief re-attempt (item 4) each consume a retry, exactly like a Code re-attempt from a NOT MET verdict. (A fix cycle on a phase whose criteria all stand MET draws on the corrective-pass budget below. Item 4's Research spawn is read-only context gathering and consumes nothing — the re-attempt it feeds does.) Exceptions that consume no phase retry: a Debug agent spawned for a pre-commit hook failure (Step 4 item 7 — the commit retry is bounded by item 7's own two-attempt rule; a NOT MET from the post-fix re-review routes to item 5's counted path, and the re-attempted phase's eventual commit starts a fresh two-attempt count), and the item 7 fallback's single message re-author (the diff is unchanged). After the limit is exhausted, escalate to the user regardless of failure type, including the last Code agent's summary and the last Review agent's returned verdicts and findings (if any).

**Corrective-pass budget:** a separately-counted budget of 2 fix cycles per phase for correcting findings surfaced while every criterion stands MET — an out-of-criteria defect (Step 4 item 5's routing), a test gap, a small fix the phase would otherwise commit as a known flaw. The counting rule is mechanical, never a judgment call: a fix cycle triggered by a NOT MET verdict or a blocking failure counts against the retry limit; every other pre-commit fix cycle counts against the corrective budget. Neither budget draws on or refreshes the other. A corrective pass is a post-verdict change like any other — Step 4 item 5's invariant applies unchanged: fresh re-review, full by default, scoped when its narrow exceptions hold (an additive test pass or a comment-only fix qualifies for Exception 2's scoped path). If that re-review returns any NOT MET, the phase has genuinely regressed: route through the failure path, subsequent cycles counting against the retry limit. When the corrective budget is exhausted, stop fixing: note the remaining findings in the progress output and carry them forward (phase report, and the PR's Review notes where applicable) — without the split, polish on a passing phase would consume the failure budget, exactly backwards.

**Retry protocol.** Do not retry the same phase with identical instructions. In any fix cycle — retry or corrective pass alike — the pass corrects the code *and its comments* to describe current behaviour only, never a record of the attempt it replaces (git history holds that), and the brief must not ask the agent to preserve it. When a rewritten comment is itself found false by the re-review, the next fix cycle's brief orders the comment that finding names **deleted**, nothing written in its place — a missing comment is a smaller defect than a false one, and in production a rewrite of a rewrite repeats the failure while deletions survived review first-time. One exception: a comment an acceptance criterion explicitly requires cannot be deleted — escalate to the user with the reviewers' findings from both failed attempts instead. The deletion pass's re-review brief names the deletion as ordered via the Review Brief's sanctioned-changes slot (agent-operations.md, Review Brief §3): an absent comment the orchestrator ordered removed is not a defect. A retry brief must additionally include:

1. **Failed-attempt observations** — 2-3 sentences on the approach the failed attempt took and the decisive error output from its summary (plus the Review agent's NOT MET findings verbatim, when the review gate triggered the retry), labeled as observations from a failed attempt that the retry agent should verify independently rather than trust.
2. **An explicit working-tree statement.** Before spawning the retry, decide the tree state — never leave it undefined (an undefined tree lets a retry duplicate edits, and lets Step 4.7's `git add -A` commit half-applied leftovers):
   - **Default: revert the failed attempt.** Revert exactly the files in its Files-changed list — including any files a Debug agent modified while fixing this attempt (from its fix-applied report) — **minus any `<keep_dirty_pathspec>` path, which is never reverted or deleted (Step 1e.2); a keep-dirty path on a Files-changed list holds the user's own uncommitted edits, so leave it and note it in the retry brief — and when `<keep_dirty_pathspec>` is absent from working memory, consult `<scratch_dir>/tree-state.md` before reverting or deleting anything, exactly as staging sites must (Step 1e.2 consequence 2)** — and delete any new files it created, plus its commit-message file and any scoped-review baselines (`rm -f <scratch_dir>/phase-<n>-commit-msg.md`, then `find <scratch_dir> -maxdepth 1 -name 'baseline-*' -delete` — separate commands; unmatched-glob hazard, Step 4 item 7) so a stale message can never ride a later fast path nor a stale baseline mislead a later scoped review. Never blanket `git checkout -- .` (the tree legitimately holds the plan file's checkbox edits and any keep-dirty paths). Unstage first if the failed attempt was staged in Step 4.5. State in the brief: `tree is at phase start`.
   - **Keep partial work** only when the failed summary shows it cleanly passing some acceptance criteria. State in the brief: `tree contains partial changes to <files> — build on them`.

---

## Resumability

The plan file is the persistent record of progress: checked acceptance criteria mark completed phases. If a conversation is interrupted, re-running `/run-plan` on the same plan skips already-completed phases (noted and confirmed with the user at Step 2) and re-attempts partially-completed phases from scratch (unchecked criteria = incomplete). Checked criteria are trusted only after Step 1e's resume guards pass — Steps 1e.2/1e.3 catch checkboxes that outran their commits (recorded ticks whose phase commit never landed, or whose commits live unpushed on another machine). 1e.2's check needs a tracked plan file — where the plans directory is git-ignored, the GH body is the only cross-run record.

**For GH-backed plans:** the synced GH issue body is the cross-machine source-of-truth — a run started on machine B fetches it at Step 1b/1c and skips the phases a prior machine completed; per-phase sync (Step 4.6) keeps it in lockstep with the local file.
