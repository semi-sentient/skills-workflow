---
name: prd-to-plan
description: Turn a PRD into a multi-phase implementation plan using tracer-bullet vertical slices, saved as a local Markdown file and optionally published as a GitHub sub-issue. Use when user wants to break down a PRD, create an implementation plan, plan phases from a PRD, or mentions "tracer bullets". Accepts an optional GitHub issue reference (e.g. `#123` or a full issue URL) to link the plan as a sub-issue of that PRD-epic.
---

# PRD to Plan

Break a PRD into a phased implementation plan using vertical slices (tracer bullets). Output is a Markdown file in the project's plans directory.

## Process

### 1. Resolve PRD source and GitHub availability

Determine where the PRD content comes from and whether this invocation will publish to GitHub.

**Step 1a — Detect GitHub availability** (cheap, run once):

- `git remote get-url origin` — if no output or the URL is not `github.com`, GH integration is unavailable (pure local mode)
- If a GH remote exists, `gh auth status` — if not authenticated, GH integration is unavailable

Capture `<org>/<repo>` from the remote URL for later use.

**Step 1b — Resolve PRD source** by precedence:

1. **Explicit GH issue argument** passed to the skill (e.g. `#123` or `https://github.com/<org>/<repo>/issues/123`)
2. **In-context GH issue URL** matching the current repo's remote, detected by scanning the conversation
3. **Local PRD file with `<!-- gh-issue: N -->` footer** — if the user points to a local PRD file (or one is apparent from recent conversation, e.g. `write-a-prd` just wrote it), read it. If it contains the footer, extract `N` and treat equivalent to an explicit GH argument. This is how the `write-a-prd` → `prd-to-plan` handoff works across conversations without the user copying the issue number manually.
4. **In-context or local PRD content without footer** (pure local mode)

If the user passed `--no-github` (or equivalent), skip GH entirely and operate in local-only mode regardless of context — including ignoring any footer marker in the local PRD file.

**Step 1c — Handle each case:**

- **Explicit arg, GH available:**
  - Run `gh issue view <n> --json number,title,url,updatedAt` (no body — avoids duplicating content if the PRD is already in conversation). This doubles as a pre-flight that the parent issue exists.
  - Show confirmation: `Linking plan to #<n> '<title>' — last updated <updatedAt>.` Display the timestamp passively; do not prompt on it.
  - If the PRD is NOT already in conversation, fetch the full body: `gh issue view <n> --json body,title,number,url`
  - If conversation references a different issue number for this repo, surface the mismatch before proceeding: `You passed #<n> but I noticed #<m> earlier. Continue with #<n>?`
- **Explicit arg, GH unavailable:** fail loudly. Explain whether `gh` is missing, not authenticated, or the repo is not GitHub. Do not silently fall back.
- **In-context issue detected, GH available:**
  - Single match: `Detected GH issue #<n> '<title>' in this conversation. Link the plan as a sub-issue? (yes / specify different / skip GH)`
  - Multiple matches: list them, ask which (or `none`)
  - On confirm, proceed as if the user had passed an explicit arg
- **In-context issue detected, GH unavailable:** skip detection silently; operate in local-only mode
- **Local file footer detected, GH available:** proceed as if the footer's issue number were passed explicitly (same as "Explicit arg, GH available" case). Notify the user: `Detected GH issue #<n> from PRD footer — linking plan as a sub-issue. Use --no-github to disable.`
- **Local file footer detected, GH unavailable:** fail loudly — the PRD claims to be published but GH can't be reached; do not silently drop the sub-issue relationship. User either needs to fix their `gh` setup or pass `--no-github` to explicitly demote to local mode.
- **Nothing in context and no explicit arg:** operate in local-only mode. If the PRD content is also not apparent in the conversation, ask the user to paste it or point you to the file.

**Feature name (normalized).** Throughout this skill, `<feature name>` means the source title with a leading `PRD: ` prefix stripped (case-insensitive, surrounding whitespace trimmed). The source title is the GH issue title (GH mode) or the `# PRD: <Feature Name>` heading of the local PRD (pure-local mode) — `write-a-prd` prefixes both with `PRD: ` for scannability. That prefix must NOT leak into the derived artifacts: the plan slug (Step 7b), the plan heading (Step 7d template), or the `Plan: <feature name>` sub-issue title (Step 8b) — otherwise you get `Plan: PRD: …` and a `prd-…-plan.md` slug. Use the *raw* title — prefix intact — only where the actual issue is cited verbatim: the `Linking…` / `Detected…` confirmation messages above and the `("Title")` portion of the `Source PRD:` header.

### 2. Explore the codebase

If you have not already explored the codebase, do so to understand the current architecture, existing patterns, and integration layers.

### 3. Identify durable architectural decisions

Before slicing, identify high-level decisions that are unlikely to change throughout implementation:

- Route structures / URL patterns
- Database schema shape
- Key data models
- Authentication / authorization approach
- Third-party service boundaries
- i18n namespace(s) and reusable key references (see Step 3.5)

These go in the plan header so every phase can reference them.

### 3.5. Assess i18n impact

**Decision gate:**

- **Skip this step** if the PRD involves only refactoring, testing, configuration, or other changes with no user-facing strings.
- **Skip this step** if the project does not use i18n.
- **Otherwise** (PRD introduces or modifies user-facing strings AND project uses i18n) → STOP and read [references/i18n-phase.md](references/i18n-phase.md) now. It contains the full procedure (discover setup → audit reusable keys → enumerate new keys → plan Translations phase → wire up later phases) plus the acceptance signal used by Step 6 validation. Do not proceed to Step 4 without reading it.

### 4. Draft vertical slices

Break the PRD into **tracer bullet** phases. Each phase is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

<vertical-slice-rules>
- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Prefer many thin slices over few thick ones
- Omit implementation details that are volatile across phases (e.g., intermediate variable names, internal state shapes that may be refactored, styling specifics)
- DO include implementation details that are durable and resolve ambiguity for the implementing agent (e.g., which library or framework component to use, specific API patterns to follow, error-handling strategy, serialization format)
- DO include durable decisions: route paths, schema shapes, data model names
</vertical-slice-rules>

#### Out of scope for plan content

Do NOT include phases or steps for:

- **Branch creation** — `run-plan` creates a `plan/<slug>` work branch automatically at start
- **Per-phase commits** — `run-plan` commits after each phase using the `commit` skill's format
- **PR submission** — `run-plan` opens the PR at end of run, linking the plan sub-issue and parent PRD
- **Merge / deployment ceremony** — these belong to the team's release process, not the plan

Plans describe the **work** (what to build, how to verify it). The **git/GH ceremony** (branch, commits, PR) is handled uniformly by `run-plan`. Users may opt out of individual pieces via `--no-branch`, `--no-commits`, or `--no-pr`; plans don't need to adapt to those overrides — they describe the work either way. If the PRD calls for post-merge verification or production observation, capture that as a phase describing _what to observe and decide_, not as commit/PR steps.

#### Cross-phase evolution

When a shared function, component, or data structure is introduced in one phase and modified in a later phase, document the evolution explicitly:

- In the earlier phase: describe what is built and note that later phases will extend it
- In the later phase: state clearly that it MODIFIES the earlier phase's implementation, and describe the before→after change (e.g., "Modify `resolveDefault()` from Phase 2 to check the cache BEFORE falling back to the hardcoded default")
- This prevents implementing agents from rebuilding from scratch or being confused about the function's current state

#### Forward-compatibility

For each phase, identify structural decisions that must anticipate later phases:

- Extension points that later phases will populate (e.g., "Response DTO includes an empty `metadata` map — Phase 4 will populate it with audit fields")
- Abstraction points that later phases will override (e.g., "Use a `resolveEndpoint(key)` function for path resolution so Phase 6 can swap in tenant-specific paths")
- Document these as explicit notes in the phase's "What to build" section

### 5. Quiz the user

Present the proposed breakdown as a numbered list. For each phase show:

- **Title**: short descriptive name
- **User stories covered**: which user stories from the PRD this addresses

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Should any phases be merged or split further?

Iterate until the user approves the breakdown.

### 6. Verify the plan

Before writing the file, critically verify your own plan against the actual codebase. This catches the #1 source of plan errors: working from stale memory instead of real files.

**Re-read source files** — For every source file referenced in any phase's "What to build" section, re-read the actual file now (not your earlier summary). Verify:

- File paths are correct
- Function signatures match what the plan describes
- Provider/component nesting hierarchies are accurate
- Interfaces and types match what the plan claims to extend

**Cross-phase coherence** — For each phase that modifies something from an earlier phase:

- The before→after change is explicitly documented
- Earlier phases' tests won't break silently from later changes
- Shared interfaces evolve consistently

**Decision completeness** — Scan every phase for "either/or", "or alternatively", "if > N lines", or other unresolved language. Each must be resolved to a single prescriptive decision. Plans close decisions; they don't enumerate options.

**PRD coverage** — Every user story from the PRD maps to at least one phase. Every testing decision from the PRD has a corresponding TDD slice.

**i18n completeness** — If the PRD contains user-facing strings and the project uses i18n, verify the plan matches the acceptance signal in [references/i18n-phase.md](references/i18n-phase.md): Phase 1 is a Translations phase, architectural decisions list i18n namespaces and reusable keys, no later phase edits translation files, non-default locales have real translations. If any criterion fails, return to Step 3.5 and rework.

**Architectural feasibility** — For each phase, verify that components can actually access the contexts/hooks/functions they're described as using. Check provider nesting, import paths, and module boundaries.

**Confidence scoring** — Rate each phase 0–10 for how likely an AI coding agent will implement it correctly from the plan alone. Flag any phase below 9 for revision.

If issues are found, fix them before proceeding. If any phase scores below 9, add concrete implementation details (code snippets, API configurations, exact function signatures) until it reaches 9+.

**Present verification results** — Show the user a summary table with each phase's initial confidence score (0–10), any issues found, and the changes made to resolve them. Do NOT proceed to Step 7 until the user explicitly approves. If the user requests changes, revise, re-verify, and present the updated results to the user for approval. Repeat until approved.

### 7. Write the plan file

**Prerequisite**: Step 6 verification results MUST have been presented to the user and explicitly approved before writing. If Step 6 has not been completed and approved, go back and complete it now.

**Step 7a — Determine the plans directory** using this precedence:

1. If `.agents/plans/` exists, use it
2. Else if `.claude/plans/` exists, use it
3. Else if `.agents/` exists, create `.agents/plans/` and use it
4. Else if `.claude/` exists, create `.claude/plans/` and use it
5. Otherwise, create `.plans/` and use it

**Step 7b — Derive the plan slug:**

The slugify rule (shared with `write-a-prd` Step 6a):

1. Lowercase
2. Replace spaces with hyphens
3. Strip any character that is not alphanumeric or a hyphen
4. Collapse any run of consecutive hyphens to a single hyphen; trim leading/trailing hyphens

- If a local PRD file is in play (e.g. `.agents/plans/mui-v9-migration-prd.md`), pair the slug by swapping the suffix: `mui-v9-migration-plan.md`
- Else slugify the GH issue title — strip the leading `PRD: ` prefix first (the feature-name rule in Step 1c) — using the rule above: "PRD: MUI v9 Migration" → "MUI v9 Migration" → `mui-v9-migration-plan.md`
- Confirm the resulting filename with the user before writing

**Step 7c — Re-invocation detection** (run before writing):

Check for existing state:

- Target plan file exists at the computed path?
- When GH is in play: a sub-issue with title `Plan: <feature name>` exists under the parent? Prefer reading the `<!-- gh-sub-issue: N -->` footer from an existing local file (more reliable than title matching). Otherwise query `gh api /repos/<org>/<repo>/issues/<parent>/sub_issues` and match by title.

Branch based on state:

| Local file | Sub-issue | Prompt                                                                                                        |
| ---------- | --------- | ------------------------------------------------------------------------------------------------------------- |
| No         | No        | Proceed normally                                                                                              |
| Yes        | No        | `Plan file exists. Overwrite (regenerate) / re-publish existing file as sub-issue / cancel?`                  |
| Yes        | Yes       | `Plan file and sub-issue #N both exist. Regenerate file / update sub-issue body / cancel?`                    |
| No         | Yes       | `Sub-issue #N exists but no local file. Fetch its body as the local file / regenerate from scratch / cancel?` |

If the user chose a publish-only or update-only path, skip the file write below and jump to Step 8 using the existing file. Otherwise proceed.

**Step 7d — Write the plan** using the template below.

The `Source PRD:` header has two forms — do not mix them:

- **GH in play:** `> Source PRD: #123 — https://github.com/<org>/<repo>/issues/123 ("Title")`
- **Pure local:** `> Source PRD: .agents/plans/<slug>-prd.md`

When a GH issue is in play, omit any local PRD file reference — the GH issue is the canonical source, and the local PRD file is typically uncommitted (a local path would confuse anyone reading the plan from GitHub).

<plan-template>
# Plan: <Feature Name>

> Source PRD: <one of:>
>
> - GH in play: `#123 — https://github.com/<org>/<repo>/issues/123 ("Title")`
> - Pure local: `.agents/plans/<slug>-prd.md`

## Architectural decisions

Durable decisions that apply across all phases:

- **Routes**: ...
- **Schema**: ...
- **Key models**: ...
- **i18n**: Namespace(s)/scope(s) used, reusable key reference (from Step 3.5, omit if no user-facing strings or no i18n)
- (add/remove sections as appropriate)

---

## Phase 1: <Title>

**User stories**: <list from PRD>

### What to build

A concise description of this vertical slice. Describe the end-to-end behavior, not layer-by-layer implementation.

### Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

---

## Phase 2: <Title>

**User stories**: <list from PRD>

### What to build

...

### Acceptance criteria

- [ ] ...

<!-- Repeat for each phase -->

<!--
  If published as a GH sub-issue, Step 8 appends a footer line at the very end
  of the file using an HTML comment of the form:  gh-sub-issue: <issue_number>
  This marker is used by re-invocation detection to find the linked sub-issue.
-->
</plan-template>

---

### 8. Publish to GitHub (only if GH is in play)

Skip this step entirely if operating in local-only mode.

**Step 8 — Determine the operation** based on how Step 7c resolved:

- **Create** — no existing sub-issue (fresh first-time publish, or "re-publish existing file" from the re-invocation matrix). Follow Steps 8a–8e.
- **Update** — existing sub-issue should be updated in place (from the "update sub-issue body" branch of the re-invocation matrix). Skip 8b–8e and follow Step 8f only.

**Step 8a — Confirmation gate:**

- Create path: `Ready to create sub-issue under #<parent> from <path>. Review the file (and edit if needed), then reply 'create' to proceed, or 'cancel' to stop.`
- Update path: `Ready to update existing sub-issue #<n> from <path>. Review the file (and edit if needed), then reply 'update' to proceed, or 'cancel' to stop.`

Wait for explicit confirmation. The user may edit the file before confirming.

**Step 8b — Create the sub-issue:**

First ensure the `plan` label exists, since `gh issue create --label plan` fails with HTTP 422 if it doesn't:

```
gh label create plan \
  --color bfd4f2 \
  --description "Phased implementation steps and technical rollout details" \
  2>/dev/null || true
```

This is idempotent: `gh label create` errors when the label already exists, and `2>/dev/null || true` swallows that so a pre-existing `plan` label is left untouched. Do NOT add `--force` — that would overwrite an existing label's color/description. If this command fails for a real reason (auth, network), the `gh issue create` below surfaces it. Then create the sub-issue:

```
gh issue create \
  --title "Plan: <feature name>" \
  --body-file <path> \
  --label plan
```

Capture both the new issue number (for display) and the issue's integer database ID (for the attach call in Step 8c). The REST `sub_issues` endpoint expects the integer database ID, NOT the GraphQL node ID — passing the node ID returns HTTP 422 `is not of type 'integer'`. Fetch it with:

```
CHILD_DB_ID=$(gh api /repos/<org>/<repo>/issues/<child_number> -q .id)
```

Do NOT use `gh issue view <n> --json id` — that returns the GraphQL node ID (string starting with `I_kw…`), which the endpoint rejects.

**Step 8c — Attach the sub-issue relationship:**

`gh` 2.88.1 has no `--parent` flag and no `sub-issue` subcommand. Use the REST API. Note the `-F` (uppercase) flag — `gh api` sends `-f` values as strings, but `sub_issue_id` must be a number:

```
gh api --method POST /repos/<org>/<repo>/issues/<parent>/sub_issues \
  -F sub_issue_id=<child_db_id>
```

Retry up to 3 times on failure with backoff: 250ms, 1s, 3s (most failures are transient rate-limit or eventual-consistency issues).

**Step 8d — On success:**

- Append `<!-- gh-sub-issue: <child_number> -->` as a footer to the local plan file
- Report the sub-issue URL to the user

**Step 8e — Failure handling:**

- **Create fails** (Step 8b): the local file is intact. Report the error verbatim and instruct the user to re-run `/prd-to-plan #<parent>` to retry — the re-invocation matrix in Step 7c will detect the existing file and offer the publish-only path.
- **Attach fails after retries** (Step 8c): the child issue exists but has no parent link (orphan). Do NOT auto-delete. Report the partial state with the exact fix command:

  ```
  Plan written to <path>.
  Sub-issue #<n> created: <url>
  Failed to attach as sub-issue of #<parent>: <error>

  To fix the relationship manually:
    CHILD_DB_ID=$(gh api /repos/<org>/<repo>/issues/<n> -q .id)
    gh api --method POST /repos/<org>/<repo>/issues/<parent>/sub_issues \
      -F sub_issue_id="$CHILD_DB_ID"

  To start over: gh issue delete <n>, then re-run /prd-to-plan #<parent>.
  ```

**Step 8f — Update path** (when the user chose "update sub-issue body" from Step 7c's re-invocation matrix):

Instead of create + attach, run:

```
gh issue edit <n> --body-file <path>
```

This replaces the body wholesale, preserving the issue number, comment history, and the sub-issue relationship. No changelog preamble is added — the local file is the source of truth.

The `<!-- gh-sub-issue: <n> -->` footer is already present in the file from the original create; do NOT re-append. On success, just report the sub-issue URL to the user.
