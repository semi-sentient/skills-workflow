# run-plan branch register

`run-plan` has branches a normal run never reaches — a repo with a PR bot never
executes `gh pr create`, a plan created by `prd-to-plan` never exercises
standalone `gh-issue:` resolution. Those paths go cold silently, and the first
time anyone notices is when a user hits one.

This register is the shrinking list. It records which branch has been exercised,
by what, and when — so "we think that path is cold" becomes a fact rather than a
hunch. Update it after any run that reaches a new branch.

It lives here rather than in a fixture's `BURN-IN.md` because fixtures are
single-use and get torn down; the coverage record has to outlive them.

## How a branch gets covered

| Instrument | Good for | Cost |
| ---------- | -------- | ---- |
| `evals/run.py` Tier 1 fixture | deterministic branches that abort before any sub-agent | ~$0.20, ~20s |
| `scripts/burn-in.sh` probe | resolution branches needing real git/`gh` state | seconds, no tokens |
| `scripts/burn-in.sh` full run | irreversible git/GH paths end to end | ~300-500K tokens, 30-60 min |
| A production run | everything, with perfect environment fidelity | free, but only covers the paths your repos take |

## Register

Status as of the 2026-07-27 burn-in (fixture `burnin-2026-07-27`, silent repo)
plus the declared-path validation in a production repo.

| Branch | Instrument | Status |
| ------ | ---------- | ------ |
| Step 1b — `gh-sub-issue:` match | production run | exercised |
| Step 1b — `gh-issue:` standalone plan | burn-in probe + full run | exercised ×3 |
| Step 1b — stale footer on a non-plan (resolvable) | `probe stalefooter` | exercised ×2 |
| Step 1b — genuine tie, two plans one issue | `probe tie` | exercised ×2 |
| Step 1b — PRD guard, nothing survives the discard | `probe guard` | exercised ×1 — impure, see note |
| Step 1b — fetch-from-GH fallback (no local file) | — | **cold** |
| Step 1b.1 — no parent epic, `<gh_issue_number>` unset | burn-in full run | exercised |
| Step 1c — local ahead of GH, pre-confirmation push | — | **cold** |
| Step 1e.2 — interrupted-phase detection | — | **cold** |
| Step 1e.2 — untracked plan file, detection skipped | production runs | exercised ×2 (2026-08-16 sitevue.web #303, 2026-08-19 sitevue.server G6 — both repos git-ignore `.agents/plans/`) |
| Step 1e.1 — `--no-branch` on base refused before any tree work | — | **cold** (branch added 2026-08-11) |
| Step 1e.2 — clean tree, triage never reached | — | **cold** (branch added 2026-08-11) |
| Step 1e.2a — paths named as input, Step 1e.4 commits them alone | production runs | exercised ×3 (2026-08-12; 2026-08-16 #303; 2026-08-19 G6) |
| Step 1e.2a — unnamed paths recorded keep-dirty, untouched all run | production runs | exercised ×3 (2026-08-12; 2026-08-16 #303 — 5 skill files, zero leakage across 8 commits; 2026-08-19 G6 — 6 paths across 6 commits) |
| Step 1e.2a — C-quoted path (space in name) unquoted before pathspec | `probe dirty` | **cold** (branch added 2026-08-11) |
| Step 1e.2a — staged keep-dirty path unstaged via `restore --staged` | — | **cold** (branch added 2026-08-11) |
| Step 1e.2a — `stop` / two unresolved replies → run ends, tree unchanged | — | **cold** (branch added 2026-08-11) |
| Step 1e.2a — invocation-implied mapping pre-filled, user confirms | production run | exercised 2026-08-16 (#303 — pre-fill shown against the numbered list, user confirmed) |
| Step 1e.3 — checkout blocked by surviving declared dirt | — | **cold** (branch added 2026-08-11) |
| Step 1e.3 — `recreate` checks out base before `branch -D` | — | **cold** (branch added 2026-08-11) |
| Step 1e.3 — commits-ahead guard names an inputs commit | — | **cold** (branch added 2026-08-11) |
| Step 1e.4 — `git add` fails on a path → stop, no partial commit | — | **cold** (branch added 2026-08-11) |
| Step 1e.4 — nothing staged but paths still dirty → stop | — | **cold** (branch added 2026-08-11) |
| Step 1e.4 — commit hook rejects, unstages before stopping | — | **cold** (branch added 2026-08-11) |
| Step 2 — inputs commit + sha reported, `--no-branch` included | `probe dirty` | **cold** (branch added 2026-08-11) |
| Step 5c.5 — root inputs commit → review scoped past `<inputs_commit_sha>` | production runs | exercised ×2 (2026-08-16 #303, 2026-08-19 G6 — both confirmed branch root via `rev-list --first-parent`) |
| Step 5c.5 — mid-branch inputs commit → base ref kept, commit named out of scope in brief | — | **cold** (branch added 2026-08-11) |
| Step 5e — tracked or keep-dirty plan/PRD file kept | burn-in verify (tracked case) | **cold** live |
| Step 5e — published PRD with unsynced local edits kept (content mismatch) | — | **cold** (branch added 2026-08-11) |
| Step 1e.1 — detached HEAD under `--no-branch` refused | — | **cold** (branch added 2026-08-11) |
| Step 1e.2 — tree-state reload: prior run's keep-dirty honored without re-asking | — | **cold** (branch added 2026-08-11) |
| Step 1e.2 — interrupted-phase prompt lists paths; keep-dirty + plan file exempt from discard | — | **cold** (branch added 2026-08-11) |
| Step 1e.2 — kept partial work bypasses triage, re-enters phase staging | — | **cold** (branch added 2026-08-11) |
| Step 1e.2a — plan file omitted from the triage list | — | **cold** (branch added 2026-08-11) |
| Step 1e.2a — rename entry: both paths named in every command | — | **cold** (branch added 2026-08-11) |
| Step 4 — staging site consults `tree-state.md` when pathspec absent (post-compaction) | — | **cold** (branch added 2026-08-11) |
| Error Handling — retry revert skips a keep-dirty path on the Files-changed list | — | **cold** (branch added 2026-08-11) |
| Error Handling — retry revert consults `tree-state.md` when pathspec absent | — | **cold** (branch added 2026-08-11) |
| Step 1e.4 — pre-staged leftovers unstaged before the inputs commit (rename: both paths) | — | **cold** (branch added 2026-08-11) |
| Step 2 — reloaded `inputs-commit:` sha unreachable → stale line dropped | — | **cold** (branch added 2026-08-11) |
| Step 3 — write-scope snapshot form on any dirty-at-start state (not just keep-dirty) | — | **cold** (trigger extended 2026-08-11) |
| Step 4.5 — scoped re-review exception | production runs (sitevue.server PR #249; sitevue.web #303) | exercised ×5 — ×3 on 2026-08-07 (found the delta-transmission defect this repo then fixed); test-delta form ×2 on 2026-08-16 (#303: comment-only test delta, additive assertion) |
| Step 4.5 — baseline extraction + scoped diff brief | production run (#303) + git-level repro | exercised ×2 live 2026-08-16 — baselines extracted before re-staging both times; scoped reviewer saw a 2-line delta against a 581-line phase |
| Step 4.5 — declared-comment-only production delta admitted to Exception 2's scoped path | — | **cold** (branch added 2026-08-16; the full-review cost it replaces measured in run #285) |
| Step 4.5 — scoped reviewer refutes a comment-only declaration (non-comment line or tool-directive comment) → escalates to full | — | **cold** (branch added 2026-08-16) |
| Step 4.5 — evidence table written to the spawn's own resolved `phase-<n>-review[-k].md` path; return = verdict lines + findings inline, existence-checked per spawn | production run | exercised 2026-08-19 (G6 — pre-c13e95c working tree, all review spawns) |
| Step 2 — `run-conventions.md` written once; skeleton briefs point at it | production run | exercised 2026-08-19 (G6 — pre-c13e95c working tree; briefs stayed phase-specific) |
| Retry protocol — second false rewrite of a comment → deletion ordered (criterion-required comment escalates instead) | — | **cold** (branch added 2026-08-16) |
| Step 4 item 10 — pre-authorized cleanup folded into a later phase, named in both that phase's briefs | — | **cold** (branch added 2026-08-16; the unsanctioned form read as scope creep in run #285) |
| Step 4.7 — fast-path fence strip | — | **cold** (guard added 2026-08-07; the unguarded failure it prevents occurred in production) |
| Step 4.7 — fast-path reuse over a verified comment-only delta (message re-checked, recorded) | — | **cold** (branch added 2026-08-19; both 2026-08-16/19 runs deviated toward exactly this behavior — #303 §5, G6 G2) |
| Retry protocol — message maintenance: fix-cycle agent updates the message file, Step 4.7 treats it as freshly authored | — | **cold** (branch added 2026-08-19) |
| Step 4.5 — Review return carries the weak-criteria flag | — | **cold** (branch added 2026-08-19; the hand-briefed form caught 3 weak criteria in #303) |
| Step 4.5 — zero-hit criterion verified with a positive control | — | **cold** (branch added 2026-08-19; a reviewer invented the control unprompted in #303 after two live false negatives) |
| Step 5e — CONFIRMED-finding draft PR keeps the local files | — | **cold** (branch added 2026-08-19; the pre-rule wrong default fired in #303) |
| Doc budget — false-comment correction: delete first, clause-verify any rewrite | — | **cold** (branch added 2026-08-19; hand-briefed form ran clean in #303) |
| Step 4 item 11 — no turn break between phases | — | **cold** (branch added 2026-08-19; G6's orchestrator stopped after 3 of 4 phases) |
| Exception 2 — changed expected value in an existing assertion escalates to full | production run | exercised 2026-08-19 (G6 — full review taken by instinct, pre-codification) |
| Error Handling — infrastructure death: scratch+tree cleanup, identical re-spawn at no budget, ledger row | production run | exercised 2026-08-19 (G6 — a reviewer death: scratch cleanup + free re-spawn only; the tree-attribution cases are separate rows below) |
| Error Handling — death tree case 1: pre-spawn snapshot delta cleaned | — | **cold** (branch added 2026-08-19) |
| Error Handling — death tree case 2: staged fix cycle, unstaged delta restored from the index | — | **cold** (branch added 2026-08-19) |
| Error Handling — death tree case 3: phase-start tree, observed dirt reverted | — | **cold** (branch added 2026-08-19) |
| Error Handling — second no-return death of the same spawn escalates | — | **cold** (branch added 2026-08-19) |
| Progress flags — counted budgets `(↻ retry n/2, corrective n/2)` | — | **cold** (branch added 2026-08-19; the bare-flag bookkeeping drift it prevents occurred in #303) |
| Step 1e.4 — inputs commit subsumes a dedicated plan phase | production run | exercised 2026-08-19 (G6 Phase 1, git-ignored plans → `(no commit — no changes)` branch; the tracked-plans checkbox-only-commit branch is **cold**) |
| Retry protocol — Message maintenance absent-file arm (`git diff HEAD` authoring in a fix cycle) | — | **cold** (branch added 2026-08-19) |
| Error Handling — any post-verdict no-return death forces the full re-review (index unprovable) | — | **cold** (branch added 2026-08-19) |
| Error Handling — pre-staging fix-agent death: no revert, disclosure line in the re-spawn brief | — | **cold** (branch added 2026-08-19) |
| Step 4.7 — reuse re-check mismatch → fallback | — | **cold** (branch added 2026-08-19) |
| Scoped re-review — weak-criteria flag bounded to re-verified criteria (`None (scoped)`) | — | **cold** (branch added 2026-08-19) |
| Step 4 opening — subsumed-phase criterion fails verification → surfaced to user, not ticked | — | **cold** (branch added 2026-08-19) |
| Step 4 opening — subsumed phase via a prior run's reloaded `inputs-commit:` sha | — | **cold** (branch added 2026-08-19) |
| Step 4 opening — subsumed phase via the user's own between-runs commit (no sha on record) | — | **cold** (branch added 2026-08-19) |
| Step 5e — promote-as-is resolves the finding for the deletion gate | — | **cold** (branch added 2026-08-19) |
| Step 5e — user-requested `--draft` with no unresolved finding still deletes | — | **cold** (branch added 2026-08-19) |
| Step 4.7 — pre-commit hook failure → Debug | — | **cold** |
| Step 5d — declared: poll + `gh pr edit` | production run | exercised |
| Step 5d — declared: poll timeout, report-and-wait | — | **cold** |
| Step 5d — silent: `gh pr create` | burn-in full run | exercised |
| Step 5d — `Refs #` omitted, no parent epic | burn-in full run | exercised |
| Step 5d — provenance footer omitted on silent path | burn-in full run | exercised |
| Step 5a — degraded sync reconciliation | — | **cold** |
| Step 5e — plan file cleanup on complete (untracked plans dir) | — | **cold** — the burn-in fixture tracks its plan file, so it now exercises the keep branch instead; needs a git-ignored-plans fixture |
| Outcome `partial` / `aborted` | — | **cold** |
| `commit` — `Ticket:` footer with leading blank line | burn-in full run + production | exercised |

### Notes

- **The PRD guard result is impure.** `probe guard` passes `#999999`, which does
  not exist on GitHub, so the failure conflates "no such issue" with "the only
  local match is a PRD". The transcript showed the discard logic genuinely firing,
  so it is evidence — but a clean test would publish the PRD as a real issue and
  pass that number. Worth fixing when the probe is next regenerated.
- **Step 1b resolution is the best Tier 1 candidate in the skill.** It is
  deterministic, aborts before any sub-agent, has no side effects, and has already
  demonstrated real run-to-run variance — the original tie-break rule resolved two
  ways across three reps, which is what exposed it. Promoting these three probes
  to fixtures would make them free to re-run on every future edit to Step 1b.
- **Cold is not the same as broken.** Most rows above are cold because reaching
  them requires deliberately breaking something (revoking auth mid-run, killing a
  run between checkbox and commit). Rank them by what a user actually hits: the
  fetch-from-GH fallback is common, the degraded-sync path is not.
- **`commit` ticket inference is unreachable from a GH-mode `run-plan`** (confirmed
  by both 2026-08-16/19 production runs): run-plan passes the ticket explicitly at
  every call site, and `plan/<slug>` branches carry no digits for the branch-name
  pattern. Covering `77aae51` needs an ad-hoc commit outside run-plan on a branch
  like `feat/123-x` or `markus/eng-142-y`.
- **Highest-value untested paths as of 2026-08-19:** `tree-state.md` reload on
  resume, and the compaction re-read clauses (agent-operations.md re-read,
  staging-site tree-state consult). Neither production run hit a resume, a
  compaction, or a reload — the conditions the 08-13 compression cuts most
  plausibly degrade.
