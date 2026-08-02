# Completion Templates

Load this reference only at Step 5, when rendering the final completion table and composing the end-of-run summary comment and PR body. Contains the exact markdown templates.

(The active-time / token figures below come from the run ledger. On a host exposing no usage metadata, drop those figures — or label a wall-clock elapsed as approximate — per SKILL.md → Run Ledger → Host portability; the templates otherwise stand.)

---

## Final completion table (Step 5 summary)

The between-phase running table (SKILL.md → Progress Reporting) keeps one row per phase. At completion, switch shape: one row per **sub-agent**, grouped under its phase, with a *subtotal* line per phase — the ledger already holds exactly these rows, so render them; do not aggregate away the data the storage layer correctly keeps. This table is also where **`tool_uses` is reported** (kept out of the between-phase table to protect its width): per-agent `tool_uses` is the closest available proxy for how full each agent's context window got (SKILL.md → Run Ledger), and its spread — say a 257-call Code agent against 18–51-call reviewers — is the run's context-pressure story.

| Phase | Agent | Tokens | Tool uses | Active time |
| ----- | ----- | -----: | --------: | ----------: |
| 2 | Code | 353.9K | 202 | 1:12:03 |
| 2 | Code (retry 1) | 113.2K | 96 | 0:22:41 |
| 2 | Code (retry 2) | 108.0K | 71 | 0:21:14 |
| 2 | Review | 124.6K | 44 | 0:16:52 |
| 2 | Review (re-review 1) | 119.3K | 38 | 0:14:20 |
| 2 | Review (re-review 2) | 120.2K | 41 | 0:14:02 |
| 2 | *subtotal* — ✓ (↻ retried) | 939.2K | — | 2:41:12 |

**Agent** is the mode plus a qualifier where one disambiguates (`Code (retry 1)`, `Research: <topic>`, `Debug`). Subtotal lines carry the phase's status flags from the running table; their Active time follows the parallel-group rule (max, with the Σ as a labeled aside). Include `setup`, `pre-PR` (Review), and `followup` groups where they occurred, and end with a **Totals** row summing the subtotal lines. The same rendered table is re-pasted verbatim into the PR body's collapsed "Run cost" section (template below).

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
**Total active time:** <h:mm:ss> (summed sub-agent `duration_ms` from the ledger, parallel groups counted at their max — idle-immune; add wall-clock elapsed only as a clearly-labeled "elapsed, incl. pauses" aside, never as the headline)
**Total cost:** <sum of `subagent_tokens`> tokens across <N> sub-agents

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
**Total active time:** <h:mm:ss> (summed sub-agent `duration_ms` from the ledger, parallel groups counted at their max — idle-immune)
**Total cost:** <sum of `subagent_tokens`> tokens across <N> sub-agents

### Completed (with active time + cost)

- **Phase 1: <title>** — (<h:mm:ss> active, <tokens>)
- **Phase 2: <title>** — (<h:mm:ss> active, <tokens>)
- ...

### Incomplete

- **Phase X+1:** BLOCKED — <reason>
- **Phase X+2:** Not attempted (<reason>)

### Resume

Re-run `/run-plan #<plan_sub_issue_number>` to retry from Phase X+1.
```

Do not include file lists or code snippets in the comment — the synced body has the full plan with checkboxes; the comment is the milestone marker.

---

## PR body (Step 5d)

Determine draft vs. ready:

- `--draft` flag passed → draft
- Outcome is `partial` → draft (with a "Partial execution" warning at the top of the body)
- Pre-PR branch review (Step 5c.5) returned a CONFIRMED correctness finding → draft (surface the findings to the user alongside the PR URL)
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

<!-- include this section ONLY when Step 5c.5 produced surviving findings -->
- <finding — `file:line`, one-line description, CONFIRMED|PLAUSIBLE>

<details>
<summary>Run cost (per sub-agent)</summary>

<!-- paste the final completion table (format above) verbatim from the Step 5 summary — same rows, subtotals, and Totals; it is already rendered from the ledger, so this is a re-paste, not a re-computation. OMIT this whole details block when the host exposed no usage metadata (the table would carry no figures). -->

</details>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

<!-- Provenance footer — include ONLY when attaching to an auto-opened PR (declared-repo path above), so run-plan PRs read consistently with the repo's other auto-opened PRs. OMIT when self-creating via gh pr create (silent-repo path). If the repo's PR-opening workflow uses a specific footer, match its wording. -->
---
🤖 Opened automatically because `<branch_name>` was pushed. A human still reviews and approves.
```

**Test plan population rule:** replace the placeholder with concrete hands-on retest steps drawn from two sources: (a) if any phase touched rendered UI (components, routes, styles — judge from phase summaries and the plan's file manifests), the UI-touching phases' acceptance criteria and reported user-visible behavior; (b) any criteria the per-phase reviews marked NEEDS-RUNTIME — these carry over regardless of whether the run touched UI (Step 4.5 promises every NEEDS-RUNTIME criterion a Test-plan entry). These steps are the manual-retest gate — make each one independently checkable by a human running the app. Only when neither source applies does the single `- [ ] <reviewer fills in based on feature area>` placeholder line remain.

The PR title is the feature name with no Conventional-Commits prefix. Per-phase commits are typed individually by the `commit` skill based on each commit's diff — aggregating them under a single PR-level prefix would mislabel a mixed-type branch. The commit list in the PR shows the full type breakdown for reviewers.

---

## PR step: expected paths and failures

Which failures can occur depends on the path taken (see the declaration gate in Step 5d above):

- **Declared repo, PR found — the happy path (not an error).** CI opens the PR within seconds of the push, so `gh pr list --head <branch_name>` finding one is expected. Attach the body with `gh pr edit` (provenance footer already composed into it), and apply draft/ready via `gh pr ready` / `gh pr ready --undo`. Do NOT recreate.
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
