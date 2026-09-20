# Completion Templates and the Step 5 procedure

Read this once, whole, at Step 5, once `<outcome>` is classified. It owns the Step 5 procedure (below), the summary comment, the push and pre-PR review routing, the PR body and submission flow, and the local-file cleanup Step 5e follows. The completion table is `rp.sh totals` output (format and example in references/ledger.md); on a host exposing no usage metadata its cells read `n/a` — drop the figures rather than fabricate them.

---

## Step 5 procedure

**Final summary** (every run): what was accomplished across all phases; the completion table — `rp.sh totals <phase>=<Status> …`, one pair per phase carrying the tracker's Status cell, pasted verbatim (its Totals row is the run's active time and token cost; never hand-render it or read `ledger.md`); optionally one **Elapsed** line (`now − RUN_START` from `run.env`, `h:mm:ss`) explicitly labelled as including any pauses/idle — never presented as the run's "duration"; caveats, manual steps, follow-ups; the carried findings — read `<scratch_dir>/carried-findings.md` once here (absent means none were carried) and reuse it for the PR's Review notes; acceptance criteria that remain unchecked (`rp.sh criteria <n>` lists a phase's labelled criteria with their ticks); every amendment marker the run wrote — `(accepted as written — …)`, `(amended mid-run — …)`, `(amended after commit — …)`, `(added mid-run — …)`, `(reopened — …)` (fix-cycles.md's suffix table); and, when keep-dirty paths were declared, those paths — still uncommitted, excluded from every phase commit, absent from the PR. **Local-only runs (and only these):** state plainly that the work branch was never pushed and give the command — `git push -u origin <branch_name>`. Everything below is GH-mode only, so a run that just ends here would otherwise read as "nothing left to do".

**(GH mode, outcome `complete` or `partial` only — skip everything below on `aborted`.)**

### Step 5a — Sync reconciliation

If `<gh_sync_mode> == degraded`, run `rp.sh sync` once more. If it still fails, skip Step 5b and Step 5d (do not strand a "completed" comment on a stale body and do not open a PR linked to a stale plan) and surface the partial state:

```
Run completed locally. GitHub sync still failing: <error>
To sync manually after fixing the issue:
  gh issue edit <plan_sub_issue_number> --body-file <plan_file_path>
  gh issue comment <plan_sub_issue_number> --body "<final summary text>"
```

### Step 5b — Post the summary comment

Pick the template below matching the run's outcome and post it.

### Step 5c — Push the work branch

Skip if `--no-branch` was passed (no dedicated branch to push). This step sits inside the GH-mode block **deliberately** — in a `<pr_open_mode> == declared` repo the push is what opens the PR, so a run scoped to local-only must not touch the remote at all.

**Order under `<pr_open_mode> == declared`:** run Step 5c.5 BEFORE this push — a review that follows the push can no longer decide whether the PR opens as draft. Under `silent` the order as written stands.

Run `git push -u origin <branch_name>`. If the push fails (branch protection, network, auth, force-push needed): surface the error verbatim; **do NOT auto-force-push**; skip Step 5d and instruct the user to resolve the push manually before opening a PR.

### Step 5c.5 — Pre-PR branch review

Skip if `--no-branch-review`, or if Step 5d will be skipped anyway (`--no-pr`, `--no-branch`, push failed in Step 5c, Step 5a's final sync failed). This gate exists to populate a PR body — never spend a branch-scope Review agent when no PR will be opened.

Spawn ONE fresh Review agent at branch scope: `rp.sh brief brief-prepr.md pre-pr-brief-review.md …` (slots in SKILL.md's Brief recipes — `HOOKS` is the forward-compatibility hooks the phase summaries named; `POINTERS` the handoff paths) and the one-line pointer prompt; the template carries the mandate and the output contract (surviving findings only, CONFIRMED/PLAUSIBLE, no evidence file). The orchestrator's one decision is `SCOPE_REF` — **scope it past the inputs commit, never past phase work:** when `<inputs_commit_sha>` is set AND it is the first commit ahead of base (`git rev-list --first-parent <base_branch>..HEAD | tail -1` prints it), `SCOPE_REF` is `<inputs_commit_sha>...HEAD`, not `<base_branch>...HEAD`. A mid-branch inputs commit (a resume committed inputs on top of earlier phases) keeps `<base_branch>...HEAD` — scoping past it would silently drop every earlier phase from the review — and is named in `OUT_OF_SCOPE` instead. Either way the inputs files are the user's own prose and this gate's routing offers autonomous fixes, so a finding against them is unactionable by construction.

Record its ledger row under `pre-PR`. This gate is **detection-only** — never spawn fix agents from its findings autonomously; fixes happen only when the user picks that option in the routing below (a branch-scope finding often sits in the gap between what the plan says and what the user meant, and only the user can say which was intended). Routing:

- All surviving findings go into the PR body's `Review notes` section
- If any finding is a CONFIRMED correctness bug: open the PR as **draft** instead of ready and surface the findings to the user with options — direct fixes (normal Debug/commit flow, re-push, promote) or promote as-is (under `declared`, where this review preceded the push, surface the findings BEFORE pushing — the user chooses fix-first, in which case re-run this step on the fixed branch before pushing — but only when the fixes changed executable behaviour or config; after a fix round confined to documentation files (Exception 2's path-based class), push without a further branch review — or promote-as-is, in which case push, do NOT apply the draft rule for that finding — the user has accepted it — and record it in the PR's Review notes)

### Step 5d — Submit the PR

Skip if any of: `--no-pr`, `--no-branch`, push failed in Step 5c. **When this step is skipped and `<pr_open_mode> == declared`, say so in the final summary** — the Step 5c push already triggered the repo's workflow, so a PR exists carrying the workflow's auto-generated body, and run-plan deliberately left it untouched. (`--no-pr` cannot prevent that PR from existing; it only means run-plan does not attach its body.) Compose and submit per the PR body section below. On success, report the PR URL to the user.

### Step 5e — Delete the local plan and PRD files

Run only if ALL of the following hold: GH mode (`<plan_sub_issue_number>` is set); run outcome is `complete` — not `partial` or `aborted` (partial runs need the file for resumability); Step 5d submitted the PR successfully (skipped or failed → keep the files — without a merged PR, the local file is still the most complete working copy); and no CONFIRMED Step 5c.5 finding remains unresolved — a draft-for-findings PR has follow-up pending, and deleting the run's local record while its own gate holds unresolved correctness findings is the wrong default (resolved = the user's Step 5c.5 routing choice concluded it — fixes landed and the PR promoted, or the user chose promote-as-is, which ships the finding deliberately; a user-requested `--draft` with no such finding still deletes). When all four hold, follow the Local file cleanup section below. Never delete a tracked or keep-dirty file, and never improvise the deletion.

---

## Summary comment (Step 5b)

Write the comment text to a temp file (avoids shell-escaping issues with multi-line markdown and embedded backticks), then run:

```bash
gh issue comment <plan_sub_issue_number> --body-file <temp-comment-body.md>
```

Pick the template matching the run's outcome.

### Complete outcome

```markdown
## Plan execution complete ✓

**Phases:** N of N complete
**Acceptance criteria:** M of M met
**Total active time:** <the Totals row's Active time — idle-immune; wall-clock elapsed only as a clearly-labeled "elapsed, incl. pauses" aside, never the headline>
**Total cost:** <the Totals row's Tokens> across <N> sub-agents

### Outcomes

- **Phase 1: <title>** — <one-line distillation> (<h:mm:ss> active, <tokens>)
- **Phase 2: <title>** — <one-line distillation> (<h:mm:ss> active, <tokens>)
- ...

### Notes

- <caveat / manual step / follow-up, if any>
```

### Partial outcome

```markdown
## Plan execution partial ⚠

**Phases:** X of N complete
**Acceptance criteria:** Y of M met
**Total active time:** <the Totals row's Active time — idle-immune>
**Total cost:** <the Totals row's Tokens> across <N> sub-agents

### Completed (with active time + cost)

- **Phase 1: <title>** — (<h:mm:ss> active, <tokens>)
- **Phase 2: <title>** — (<h:mm:ss> active, <tokens>)
- ...

### Incomplete

- **Phase X+1:** BLOCKED — <reason>
- **Phase X+2:** Not attempted (<reason>)
- **Phase Y:** Human gate deferred — <n> criteria await the human's report (agent work committed)

### Resume

Re-run `/run-plan #<plan_sub_issue_number>` to retry from Phase X+1 (a deferred human gate re-presents its checklist instead of re-attempting the phase).
```

Do not include file lists or code snippets in the comment — the synced body has the full plan with checkboxes; the comment is the milestone marker.

---

## PR body (Step 5d)

Determine draft vs. ready:

- `--draft` flag passed → draft
- Outcome is `partial` → draft (with a "Partial execution" warning at the top of the body) — EXCEPT when every unticked criterion is human-form (references/human-gate.md): then ready, with the warning kept, because a plan may require this PR merged before its human gate can run
- Pre-PR branch review (Step 5c.5) returned a CONFIRMED correctness finding the user has NOT already accepted → draft (surface the findings to the user alongside the PR URL). A finding the user accepted as promote-as-is at Step 5c.5 does not draft; it is recorded in Review notes.
- Otherwise → ready

The branch is already pushed at this point (Step 5c). How the PR gets *created* depends on the repo, and **`<pr_open_mode>`** — resolved in Step 1d from the repo's own agent instructions (CLAUDE.md / AGENTS.md) — is the signal. If it is somehow unset, re-read those files now rather than guessing:

- **`declared`** — the instructions state an auto-open workflow, e.g. "do not run `gh pr create` — a CI workflow opens the PR when a branch is pushed" (common where the default branch is protected and self-approval is disallowed, so a bot must author the PR for a human to be able to approve it). The Step-5c push has already triggered that workflow. **Honor the rule: never run `gh pr create` in these repos** — it would author the PR as the engineer and re-block self-approval. Poll for the auto-opened PR and attach the rich body to it.
- **`silent`** — no PR appears on its own; create it directly with `gh pr create`. This is the pre-existing flow: no poll, no added latency.

Write the body to a temp file (on the `declared` path, compose it with the provenance footer — see template), then take the matching path:

**Declared repo — poll, then attach:**

```bash
# Wait for the auto-opened PR (CI cold start; normally appears in 15–40s).
num=""
for _ in $(seq 1 30); do
  num=$(gh pr list --head <branch_name> --state open --json number --jq '.[0].number // empty')
  [ -n "$num" ] && break
  sleep 2
done

if [ -n "$num" ]; then
  # Attach the rich content (author stays the bot identity). --body-file replaces the
  # workflow's auto-generated body, so the file must already carry the provenance footer.
  # --base re-targets the PR if the workflow opened it against a different branch than
  # the run's <base_branch> (this is what honors a --base override on the declared path).
  gh pr edit "$num" --title "<feature_name>" --body-file <temp-pr-body.md> --base <base_branch>
else
  # Timeout: do NOT fall back to gh pr create — the repo forbids it.
  # Report and hand off to the user instead (see failure handling below).
  :
fi
```

Then apply the draft-vs-ready decision from above to the found PR — `gh pr ready "$num"` for ready, `gh pr ready --undo "$num"` for draft. The workflow chooses the initial state, so this is a required step, not an optional one; if the PR is already in the target state, `gh` says so and nothing changes.

**Silent repo — create directly:**

```bash
gh pr create \
  --base <base_branch> \
  --head <branch_name> \
  --title "<feature_name>" \
  --body-file <temp-pr-body.md> \
  [--draft]
```

### PR body template

```markdown
> ⚠ **Partial execution** — N of M phases complete. See plan for incomplete phases. Promote to ready when remaining work is finished. <!-- include this line ONLY when outcome is partial -->

## Summary

<one-liner derived from plan's first paragraph, or feature name as fallback>

## Plan

Implements [Plan: <feature_name>](gh_url_for_plan_sub_issue) — see plan for full phase breakdown.

Closes #<plan_sub_issue_number>
Refs #<gh_issue_number> <!-- omit this line when <gh_issue_number> is unset (standalone plan issue, no parent PRD-epic) — Closes already links the plan issue; the missing Refs is expected, not a bug -->

## Phases completed

- [x] Phase 1: <title>
- [x] Phase 2: <title>
- ...

## Test plan

- [ ] <see population rule below>

## Review notes

<!-- include this section ONLY when Step 5c.5 produced surviving findings, when Step 4 item 10 carried defects to the report route, or when a plan contradiction was accepted as written (Step 3's batch or fix-cycles.md's mid-run drift — the orchestrator wrote each `(accepted as written — …)` marker itself and lists them from that record) — tag each entry with its source -->
- <finding — `file:line`, one-line description, CONFIRMED|PLAUSIBLE> <!-- branch review (Step 5c.5) -->
- <carried defect — `file:line`, one-line description> <!-- carried, Step 4 item 10: the lines of <scratch_dir>/carried-findings.md, read once with the final summary -->
- <plan contradiction — criterion or plan text quoted, what HEAD shows, "accepted as written"> <!-- accepted as written, Step 3 -->

<details>
<summary>Run cost (per sub-agent)</summary>

<!-- paste the `rp.sh totals` output from the Step 5 summary verbatim — a re-paste, not a re-computation. OMIT this whole details block when the host exposed no usage metadata (the table would carry no figures). -->

</details>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

<!-- Provenance footer — include ONLY when attaching to an auto-opened PR (declared-repo path above), so run-plan PRs read consistently with the repo's other auto-opened PRs. OMIT when self-creating via gh pr create (silent-repo path). If the repo's PR-opening workflow uses a specific footer, match its wording. -->
---
🤖 Opened automatically because `<branch_name>` was pushed. A human still reviews and approves.
```

**Test plan population rule:** replace the placeholder with concrete hands-on retest steps drawn from three sources: (a) if any phase touched rendered UI (components, routes, styles — judge from phase summaries and the plan's file manifests), the UI-touching phases' acceptance criteria and reported user-visible behavior; (b) any criteria the per-phase reviews marked NEEDS-RUNTIME — these carry over regardless of whether the run touched UI (Step 4 item 5 promises every NEEDS-RUNTIME criterion a Test-plan entry); (c) every human-form criterion a human gate left deferred (references/human-gate.md), verbatim, marked `(deferred human gate)`. These steps are the manual-retest gate — make each one independently checkable by a human running the app. Only when none of the three sources applies does the single `- [ ] <reviewer fills in based on feature area>` placeholder line remain.

The PR title is the feature name with no Conventional-Commits prefix. Per-phase commits are typed individually by the `commit` skill based on each commit's diff — aggregating them under a single PR-level prefix would mislabel a mixed-type branch. The commit list in the PR shows the full type breakdown for reviewers.

---

## PR step: expected paths and failures

By path (the declaration gate in Step 5d above); a declared repo whose PR appears within the poll window is the happy path handled there, not a failure:

- **Declared repo, no PR within the poll window.** The workflow is slow, misfiring, or Actions is backed up. **Never self-create here — the repo's instructions forbid `gh pr create`**, and an engineer-authored PR would defeat the reason the rule exists (reviewer independence). The branch is safely pushed, so hand off:
  ```
  Branch <branch_name> is pushed, but no auto-opened PR appeared within ~60s.
  Check the repo's Actions runs for the PR-opening workflow. Once the PR appears, attach the prepared body:
    gh pr edit <number> --title "<feature_name>" --body-file <path>
  ```
  Keep the temp body file around for that follow-up (report its path).
- **Silent repo, `gh pr create` reports the PR already exists.** Something auto-opened it despite no declared rule (an undocumented workflow). Treat it as the declared path from here: find it via `gh pr list --head <branch_name> --json url,number`, append the provenance footer to the body file (the silent path composed it without one), attach with `gh pr edit`, do NOT recreate — and suggest the user document the workflow in the repo's agent instructions.
- **Other `gh pr create` / `gh pr edit` failures:** log the error verbatim and surface the manual command matching the situation:
  ```
  PR step failed: <error>
  To finish manually — if a PR already exists (gh pr list --head <branch_name> --json url,number):
    gh pr edit <number> --title "..." --body-file <path>
  otherwise (silent repos only):
    gh pr create --base <base_branch> --head <branch_name> --title "..." --body-file <path>
  ```

The branch is already pushed before any of this runs, so all work is preserved on remote regardless of outcome.

---

## Local file cleanup (Step 5e)

Step 5e above gates this (GH mode; outcome `complete`; PR submitted successfully; no unresolved CONFIRMED Step 5c.5 finding) and routes here when all four conditions hold.

Two exemptions override the deletions below; keep the file and say which exemption applied:

- **Tracked** (`git ls-files --error-unmatch <path>` succeeds) — committed on this branch, by this run or long before it; deleting it leaves the tree contradicting HEAD.
- **Declared keep-dirty** — `<keep_dirty_pathspec>` means never staged, committed, or reverted by this run; deleting it outright is a stronger violation than any of those.

1. **Delete the plan file:** `rm <plan_file_path>` (unless exempt per above)
2. **Delete the upstream PRD file** if it is exempt from neither rule above, exists locally, and was published to GH:
   - Derive the PRD path by swapping the suffix on the plan filename: `<slug>-plan.md` → `<slug>-prd.md` in the same directory
   - If that file exists AND its content contains a `<!-- gh-issue: N -->` footer (proving it was published — local-only PRDs are kept as the audit trail) AND its content matches that issue's current GH body (`gh issue view <N> --json body --jq .body` — the PRD never syncs during a run, so any difference is local edits that exist nowhere else), `rm` it
   - If any condition fails, leave it alone; on a content mismatch, say why: `PRD file kept — it carries local edits never pushed to GH issue #<N>.`
3. **Note what was deleted and what was kept in the final summary** (e.g. `Local plan and PRD files removed — GH issues #<gh_issue_number>/#<plan_sub_issue_number> and PR are the canonical record.` — drop the `#<gh_issue_number>/` segment when no parent PRD-epic exists — or `Local plan file removed; PRD file kept (not published to GH).` / `…kept (tracked on this branch).`)

Rationale: the GH issues hold the final checkbox state and the PR the work, so an untracked local copy is redundant; a re-run re-fetches it (Step 1b's "GH ref passed → not found → fetch").
