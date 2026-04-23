# Completion Templates

Load this reference only at Step 5, when composing the end-of-run summary comment and PR body. Contains the exact markdown templates.

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
**Total time:** <h:mm:ss>

### Outcomes

- **Phase 1: <title>** — <one-line distillation> (<h:mm:ss>)
- **Phase 2: <title>** — <one-line distillation> (<h:mm:ss>)
- ...

### Notes

- <caveat / manual step / follow-up, if any>
```

### Partial outcome

```markdown
## Plan execution partial ⚠

**Phases:** X of N complete
**Acceptance criteria:** Y of M met
**Total time:** <h:mm:ss>

### Completed (with durations)

- **Phase 1: <title>** — (<h:mm:ss>)
- **Phase 2: <title>** — (<h:mm:ss>)
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
- Otherwise → ready

Write the body to a temp file, then run:

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
Refs #<gh_issue_number>

## Phases completed

- [x] Phase 1: <title>
- [x] Phase 2: <title>
- ...

## Test plan

- [ ] <reviewer fills in based on feature area>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

The PR title is the feature name with no Conventional-Commits prefix. Per-phase commits are typed individually by the `commit` skill based on each commit's diff — aggregating them under a single PR-level prefix would mislabel a mixed-type branch. The commit list in the PR shows the full type breakdown for reviewers.

---

## Failure handling for `gh pr create`

- **Already exists:** detect via `gh pr list --head <branch_name> --json url,number`; surface the existing PR URL; do NOT auto-recreate.
- **Other failures:** log error verbatim and surface the manual command:
  ```
  PR creation failed: <error>
  To create manually:
    gh pr create --base <base_branch> --head <branch_name> --title "..." --body-file <path>
  ```

The branch is already pushed at this point, so all work is preserved on remote.
