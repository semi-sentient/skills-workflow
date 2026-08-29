# Upstream Differences

Several skills in this repo originated from [Matt Pocock's skills repo](https://github.com/mattpocock/skills) and have diverged. This document is a snapshot of those differences so future-us can decide whether to pull in upstream changes or keep our fork.

> **Last compared against** [`mattpocock/skills@651eab0`](https://github.com/mattpocock/skills/commit/651eab033bdf8f7fd535c274f8cbe839075aba5e) **on 2026-04-15.** Covers `write-a-prd`, `tdd`, and `grill-me` directly — all three were imported from that commit on this same date, and none has been re-diffed against upstream since. `grill-with-docs` has no separate comparison; it inherits grill-me's via the shared `<what-to-do>` body (see the `grill-me` & `grill-with-docs` section below).
>
> Upstream has since renamed `write-a-prd` to `to-spec` — look for it under that name when next comparing.

Skills are migrating to per-skill ledgers under [upstream/](upstream/) (format and sync procedure in [upstream/README.md](upstream/README.md)); `grill-me` and `grill-with-docs` have moved already. Refresh this document whenever upstream is re-synced. It is not a changelog — `git log` handles that. If a skill listed below is no longer meaningfully forked (or if new skills are forked in), update the sections accordingly.

## Common themes

Three threads run through all of our changes:

1. **Output location flexibility** — Skills that write files no longer hardcode `./plans/`. They walk a precedence chain (`.agents/plans/` → `.claude/plans/` → fallback `.plans/`) so they compose with whichever agent harness is in use.
2. **Stack-agnostic content** — `tdd`'s companion files no longer assume TypeScript; code samples are pseudocode with an explicit "adapt to your language" note.
3. **Tighter workflow chaining** — `write-a-prd` explicitly references `grill-me` and `tdd`, and `prd-to-plan` gains verification + user-approval gates. The `grill-me` → `write-a-prd` → `prd-to-plan` → `run-plan` arc is enforced more deliberately than upstream.
4. **Progressive disclosure via `references/`** — Detailed procedures, templates, and on-demand content are moved into per-skill `references/` subdirectories and loaded on explicit triggers from `SKILL.md`. This keeps the always-loaded core lean and matches the Agent Skills best-practices recommendation to separate conditional content from the entry-point instructions.

## `write-a-prd`

### Changes

- **Output destination — local-first, with optional GH publish** — Upstream submits the PRD directly as a GitHub issue; ours always writes a local Markdown file at `<plans-dir>/{kebab-case-name}-prd.md` using the plans-dir precedence chain, and only then offers to publish it as an issue labeled `epic`. The local file stays authoritative throughout authoring, and the user reviews/edits it before any `gh issue create` happens. On publish, the skill stamps a `<!-- gh-issue: N -->` footer and a `GH Issue:` header onto the local file — this marker is how `prd-to-plan` detects the linkage for sub-issue creation. Pass `--no-github` to skip the publish prompt. Re-invocation on an existing PRD surfaces a matrix (overwrite / publish existing file as new issue / cancel) so failed publishes retry cleanly.
- **Solution Sketch — user-facing terminology** — New requirement that, when the feature has UI, the PRD lists specific labels, column headers, status values, button text, and empty-state messages. This specificity lets `prd-to-plan`'s i18n step enumerate keys upfront instead of inventing copy during implementation.
- **Code-snippet rule loosened** — "Do NOT include specific file paths or code snippets" → "...unless they are immune to code changes."

### Additions

- **New Step 5: Cross-link to `tdd`** — Before drafting the PRD, read the `tdd` skill and incorporate its testing philosophy (vertical slices, behavior over implementation) into the PRD's Testing Decisions section.
- **Step 3 delegates to `grill-me`** — Upstream inlines a copy of grill-me phrasing at step 3. Ours replaces that with a reference: read the `grill-me` skill and run a grilling session, with a skip condition when an earlier in-conversation grilling already covered the needed ground. Exposes the `--light` flag to the PRD author. Matches the existing delegation pattern at Step 5's `tdd` reference and keeps grill-me as a single source of truth.
- **Slug derivation rule** — Explicit, documented slugify rule (lowercase, spaces → hyphens, strip non-alphanumeric-non-hyphen, collapse/trim hyphens). The same rule is used by `prd-to-plan` to pair plan filenames to PRD filenames — consistency here is load-bearing for cross-skill re-invocation detection.

## `prd-to-plan`

Our most heavily diverged skill. The core tracer-bullet philosophy is preserved, but significant structural steps have been added.

### Changes

- **Plans directory** — Hardcoded `./plans/` replaced with the precedence chain.
- **Vertical-slice rules — softened** — Upstream: "Do NOT include specific file names, function names, or implementation details that are likely to change." Ours distinguishes _volatile_ details (omit: intermediate variable names, refactorable state shapes, styling) from _durable_ ones (include: which library/framework, API patterns, error-handling strategy, serialization format). The change is motivated by downstream agents under-implementing when plans are too abstract.

### Additions

- **Step 3.5: Assess i18n impact** — Discovers the project's i18n setup, audits reusable translation keys, enumerates new keys, and inserts a dedicated "Translations" phase as Phase 1 of the plan (touches only translation files, no source code). Skipped when the PRD has no user-facing strings. SKILL.md keeps only the decision gate; the full procedure lives in `references/i18n-phase.md` and is loaded on demand when the gate fires.
- **Cross-phase evolution subsection** — When a shared function or component is introduced in Phase N and modified in Phase N+K, both phases must explicitly document the before→after change. Prevents downstream agents from rebuilding from scratch or being confused about current state.
- **Forward-compatibility subsection** — Each phase must identify structural extension/abstraction points that anticipate later phases.
- **Step 6: Verify the plan** — A full verification pass before writing the file:
  - Re-read source files referenced in each phase (catches stale-memory errors)
  - Check cross-phase coherence
  - Resolve any "either/or" / "or alternatively" language to a single prescriptive decision
  - Verify PRD coverage (every user story → ≥1 phase; every testing decision → TDD slice)
  - Check architectural feasibility (provider nesting, hook accessibility, import paths)
  - **Confidence scoring 0–10** per phase; anything below 9 gets concrete detail added until it reaches 9+
  - **i18n completeness check** — when Step 3.5 fired, verify Phase 1 is a Translations phase, architectural decisions list the i18n namespaces and reusable keys, no later phase edits translation files, and non-default locales have real translations. Return to Step 3.5 if any criterion fails.
  - Present verification results to the user and require **explicit approval** before Step 7
- **Step 7 gates on Step 6 approval** — Writing the plan file is now a hard prerequisite on verification having been presented and approved.
- **Plan template — i18n field** — New entry in the architectural-decisions section listing namespaces/scopes used and the reusable key reference from Step 3.5.
- **Step 8: Optional GH sub-issue linkage** — When the PRD is published as a GitHub epic (see `write-a-prd` changes above), the skill resolves the PRD source from multiple inputs (explicit `#N` argument, in-context issue URL, `<!-- gh-issue: N -->` footer on a local PRD file, or pure-local content with no footer) and then offers to publish the plan as a formally nested sub-issue of the epic (label `plan`). Attachment uses the GitHub REST API directly (`/repos/<org>/<repo>/issues/<parent>/sub_issues`) since `gh` 2.88.1 has no first-class sub-issue support; retries with backoff handle transient failures, and orphaned child issues surface the exact manual fix command rather than auto-rolling back. A `<!-- gh-sub-issue: N -->` footer stamped on the local plan file is the handoff marker for `run-plan`. Pass `--no-github` to force local-only mode regardless of context.
- **Plan scope — git/GH ceremony explicitly excluded** — Plans no longer include phases or steps for branch creation, per-phase commits, or PR submission. Those are handled uniformly by `run-plan` (native to this repo; not in upstream), so plans describe _what to build and how to verify it_ independent of which git/GH opt-outs the user eventually picks.

## `tdd`

### Additions

- **The Prove-It Pattern (Bug Fixes)** — A new dedicated red-green flow for bugs: write a failing reproduction test first, then fix, then verify. Includes a pseudocode example and guidance to spawn a subagent for the reproduction test on complex bugs (so it's written without knowledge of the fix).

### Changes

- **Language neutrality in companion files** — `interface-design.md`, `mocking.md`, and `tests.md` had their TypeScript/Jest code blocks rewritten as language-agnostic pseudocode. `tests.md` gained a top-of-file note: _"Examples use pseudocode — adapt to your project's language and test framework."_
- **Reference-link triggers** — Links to the five companion files (`tests.md`, `mocking.md`, `deep-modules.md`, `interface-design.md`, `refactoring.md`) were rewritten from generic "see X for Y" prose to explicit load conditions ("If you need concrete test examples, read tests.md"; "Before starting the refactor step, read refactoring.md"). Upstream's plain links don't tell the agent _when_ to load each file.
- **Companion files moved to `references/`** — The five supporting docs now live under `universal/tdd/references/` for consistency with `prd-to-plan` and `run-plan`, and to signal at the filesystem level that they are on-demand content. Upstream keeps them at the skill root. SKILL.md's links were updated accordingly; the companion files themselves are unchanged in content.

### Unchanged

- `deep-modules.md` and `refactoring.md` are byte-identical to upstream (now at `references/deep-modules.md` and `references/refactoring.md`; contents unchanged).
- `SKILL.md`'s core TDD flow, red-green-refactor loop, and checklist are unchanged; only the Prove-It Pattern is additive.

## `grill-me` & `grill-with-docs`

> **Moved.** These two skills now have per-skill sync ledgers with pinned upstream commits: [upstream/grill-me.md](upstream/grill-me.md) and [upstream/grill-with-docs.md](upstream/grill-with-docs.md). The text below is the 2026-04-15 snapshot, kept for the `fc60d33` history it records; the ledgers are authoritative.

`grill-with-docs` is a sibling skill that wraps the same interview engine in a `<what-to-do>` block and adds a `<supporting-info>` block for inline `CONTEXT.md` / ADR maintenance during the session. The `<what-to-do>` body is identical to our `grill-me` SKILL.md, so every deviation listed below applies to both skills. The `<supporting-info>` block — domain-glossary challenges, fuzzy-language sharpening, scenario stress-testing, and the three-criterion ADR gate (hard to reverse, surprising without context, real trade-off) — is specific to `grill-with-docs` and not compared against upstream here.

### Additions

- **Progressive sub-decision unfolding** — The walk resolves both top-level decisions and the sub-decisions each answer unlocks, not just a flat branch list. NEVER rule: don't stop at surface-level branches — drill into sub-decisions as they emerge from answers. Upstream walks "each branch" without an explicit sub-decision concept.
- **Selective challenge step** — When the user answers directly (not from an options menu the skill offered), push back once with a concrete counter before accepting ("Did you consider X?", "What breaks if Y?"). One probe, then move on. Skipped when `--light` is passed. This is the step that turns an interview into an actual grilling.
- **`--light` flag** — Skips the challenge step for a faster pass. Intended for smaller features or well-understood domains where deep stress-testing is overkill. The full mode remains the default.
- **Honesty rule on assumptions** — Any default the skill did not explicitly confirm with the user belongs under "assumptions" or "open questions," never silently under "decisions." If assumptions exceed ~3 items, the skill treats it as a signal that questions were missed and loops back. Prevents the failure mode where a "complete" wrap-up quietly papers over skipped questions.
- **Structured wrap-up** — Closing summary is a required three-section structure: decisions made (with rationale), assumptions accepted (each with a one-line justification), and open questions still requiring resolution. Upstream asks only for a brief summary and loses the assumption/open-question distinction.
- **Mid-interview codebase re-exploration** — Explicit guidance to keep exploring the codebase during the interview whenever an answer surfaces a new constraint that reshapes later branches, not just as a pre-question lookup. Upstream's "if a question can be answered by exploring the codebase, explore instead" is purely pre-question.
- **Explicit same-turn bundling ban** — Upstream already asks one question at a time; ours adds an explicit ban on same-turn bundling even for tightly coupled sub-decisions (parameters of one choice, or a follow-up only meaningful given the first answer) — they are asked in sequence, with the follow-up landing immediately after the answer. An earlier revision granted a 2 (rarely 3) sub-decision bundling allowance; it was removed because its elastic trigger invited over-bundling in practice — do not re-add it.
- **NEVER rules** — Codified hard rules: never accept "I'll figure that out later," never ask more than one question per turn, never stop at surface-level branches (must drill sub-decisions), never silently default on something the user didn't confirm.

### Changes

- **Stop condition tightened** — Completion now requires every branch and its unlocked sub-decisions to have either a decision or an explicit open question. Previously stopped when the user signaled satisfaction, which let the user escape grilling prematurely.

### Unchanged

- Core "interview relentlessly, walk each branch, recommend answers, one question at a time, explore the codebase when possible" content matches upstream.
