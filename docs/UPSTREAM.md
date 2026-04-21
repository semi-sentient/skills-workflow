# Upstream Differences

Several skills in this repo originated from [Matt Pocock's skills repo](https://github.com/mattpocock/skills) and have diverged. This document is a snapshot of those differences so future-us can decide whether to pull in upstream changes or keep our fork.

> **Last compared against** [`mattpocock/skills@651eab0`](https://github.com/mattpocock/skills/commit/651eab033bdf8f7fd535c274f8cbe839075aba5e) **on 2026-04-15.**

Refresh this document whenever upstream is re-synced. It is not a changelog — `git log` handles that. If a skill listed below is no longer meaningfully forked (or if new skills are forked in), update the sections accordingly.

## Common themes

Three threads run through all of our changes:

1. **Output location flexibility** — Skills that write files no longer hardcode `./plans/`. They walk a precedence chain (`.agents/plans/` → `.claude/plans/` → fallback `.plans/`) so they compose with whichever agent harness is in use.
2. **Stack-agnostic content** — `tdd`'s companion files no longer assume TypeScript; code samples are pseudocode with an explicit "adapt to your language" note.
3. **Tighter workflow chaining** — `write-a-prd` explicitly references `tdd`, and `prd-to-plan` gains verification + user-approval gates. The `grill-me` → `write-a-prd` → `prd-to-plan` → `run-plan` arc is enforced more deliberately than upstream.

## `write-a-prd`

### Changes

- **Output destination — local-first, with optional GH publish** — Upstream submits the PRD directly as a GitHub issue; ours always writes a local Markdown file at `<plans-dir>/{kebab-case-name}-prd.md` using the plans-dir precedence chain, and only then offers to publish it as an issue labeled `epic`. The local file stays authoritative throughout authoring, and the user reviews/edits it before any `gh issue create` happens. On publish, the skill stamps a `<!-- gh-issue: N -->` footer and a `GH Issue:` header onto the local file — this marker is how `prd-to-plan` detects the linkage for sub-issue creation. Pass `--no-github` to skip the publish prompt. Re-invocation on an existing PRD surfaces a matrix (overwrite / publish existing file as new issue / cancel) so failed publishes retry cleanly.
- **Solution Sketch — user-facing terminology** — New requirement that, when the feature has UI, the PRD lists specific labels, column headers, status values, button text, and empty-state messages. This specificity lets `prd-to-plan`'s i18n step enumerate keys upfront instead of inventing copy during implementation.
- **Code-snippet rule loosened** — "Do NOT include specific file paths or code snippets" → "...unless they are immune to code changes."

### Additions

- **New Step 5: Cross-link to `tdd`** — Before drafting the PRD, read the `tdd` skill and incorporate its testing philosophy (vertical slices, behavior over implementation) into the PRD's Testing Decisions section.
- **Slug derivation rule** — Explicit, documented slugify rule (lowercase, spaces → hyphens, strip non-alphanumeric-non-hyphen, collapse/trim hyphens). The same rule is used by `prd-to-plan` to pair plan filenames to PRD filenames — consistency here is load-bearing for cross-skill re-invocation detection.

## `prd-to-plan`

Our most heavily diverged skill. The core tracer-bullet philosophy is preserved, but significant structural steps have been added.

### Changes

- **Plans directory** — Hardcoded `./plans/` replaced with the precedence chain.
- **Vertical-slice rules — softened** — Upstream: "Do NOT include specific file names, function names, or implementation details that are likely to change." Ours distinguishes *volatile* details (omit: intermediate variable names, refactorable state shapes, styling) from *durable* ones (include: which library/framework, API patterns, error-handling strategy, serialization format). The change is motivated by downstream agents under-implementing when plans are too abstract.

### Additions

- **Step 3.5: Assess i18n impact** — Discovers the project's i18n setup, audits reusable translation keys, enumerates new keys, and inserts a dedicated "Translations" phase as Phase 1 of the plan (touches only translation files, no source code). Skipped when the PRD has no user-facing strings.
- **Cross-phase evolution subsection** — When a shared function or component is introduced in Phase N and modified in Phase N+K, both phases must explicitly document the before→after change. Prevents downstream agents from rebuilding from scratch or being confused about current state.
- **Forward-compatibility subsection** — Each phase must identify structural extension/abstraction points that anticipate later phases.
- **Step 6: Verify the plan** — A full verification pass before writing the file:
  - Re-read source files referenced in each phase (catches stale-memory errors)
  - Check cross-phase coherence
  - Resolve any "either/or" / "or alternatively" language to a single prescriptive decision
  - Verify PRD coverage (every user story → ≥1 phase; every testing decision → TDD slice)
  - Check architectural feasibility (provider nesting, hook accessibility, import paths)
  - **Confidence scoring 0–10** per phase; anything below 9 gets concrete detail added until it reaches 9+
  - Present verification results to the user and require **explicit approval** before Step 7
- **Step 7 gates on Step 6 approval** — Writing the plan file is now a hard prerequisite on verification having been presented and approved.
- **Plan template — i18n field** — New entry in the architectural-decisions section listing namespaces/scopes used and the reusable key reference from Step 3.5.
- **Step 8: Optional GH sub-issue linkage** — When the PRD is published as a GitHub epic (see `write-a-prd` changes above), the skill resolves the PRD source from multiple inputs (explicit `#N` argument, in-context issue URL, `<!-- gh-issue: N -->` footer on a local PRD file, or pure-local content with no footer) and then offers to publish the plan as a formally nested sub-issue of the epic (label `plan`). Attachment uses the GitHub REST API directly (`/repos/<org>/<repo>/issues/<parent>/sub_issues`) since `gh` 2.88.1 has no first-class sub-issue support; retries with backoff handle transient failures, and orphaned child issues surface the exact manual fix command rather than auto-rolling back. A `<!-- gh-sub-issue: N -->` footer stamped on the local plan file is the handoff marker for `run-plan`. Pass `--no-github` to force local-only mode regardless of context.
- **Plan scope — git/GH ceremony explicitly excluded** — Plans no longer include phases or steps for branch creation, per-phase commits, or PR submission. Those are handled uniformly by `run-plan` (native to this repo; not in upstream), so plans describe _what to build and how to verify it_ independent of which git/GH opt-outs the user eventually picks.

## `tdd`

### Additions

- **The Prove-It Pattern (Bug Fixes)** — A new dedicated red-green flow for bugs: write a failing reproduction test first, then fix, then verify. Includes a pseudocode example and guidance to spawn a subagent for the reproduction test on complex bugs (so it's written without knowledge of the fix).

### Changes

- **Language neutrality in companion files** — `interface-design.md`, `mocking.md`, and `tests.md` had their TypeScript/Jest code blocks rewritten as language-agnostic pseudocode. `tests.md` gained a top-of-file note: *"Examples use pseudocode — adapt to your project's language and test framework."*

### Unchanged

- `deep-modules.md` and `refactoring.md` are byte-identical to upstream.
- `SKILL.md`'s core TDD flow, red-green-refactor loop, and checklist are unchanged; only the Prove-It Pattern is additive.

## `grill-me`

Used essentially as-is from upstream. Any minor edits are cosmetic. If meaningful divergence develops, add a section here.
