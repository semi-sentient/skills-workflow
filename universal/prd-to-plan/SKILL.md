---
name: prd-to-plan
description: Turn a PRD into a multi-phase implementation plan using tracer-bullet vertical slices, saved as a local Markdown file. Use when user wants to break down a PRD, create an implementation plan, plan phases from a PRD, or mentions "tracer bullets".
---

# PRD to Plan

Break a PRD into a phased implementation plan using vertical slices (tracer bullets). Output is a Markdown file in the project's plans directory.

## Process

### 1. Confirm the PRD is in context

The PRD should already be in the conversation. If it isn't, ask the user to paste it or point you to the file.

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

**Skip this step** if the PRD involves only refactoring, testing, configuration, or other changes with no user-facing strings. Also skip if the project does not use i18n.

If the PRD introduces or modifies user-facing strings:

1. **Discover the i18n setup** — Identify the project's i18n framework, translation file format, supported locales, and key naming conventions by reading existing translation files and configuration.
2. **Audit for reusable keys** — Read translation files for namespaces/scopes likely to overlap with this feature. Do NOT exhaustively read every file — focus on the ones relevant to the feature area. Build a reusable key reference table mapping feature concepts to existing translation calls.
3. **Enumerate new keys** — List every new i18n key needed across all phases, with the default-language copy and the namespace/scope it belongs to. Only do this when the PRD has enough UI specificity (column headers, button labels, status labels, section titles, empty states) to enumerate keys confidently. If the PRD is too vague to determine exact copy, note which areas need keys but defer the specifics to each phase.
4. **Plan a Translations phase** — Include a dedicated "Translations" phase as Phase 1 of the plan. This phase touches only translation files — no source code. It contains: all new keys with default-language values, the reusable key reference table, and the list of translation files to modify. For non-default locales, provide real translated values — do NOT copy default-language strings as placeholders.
5. **Wire up later phases** — All subsequent phases reference translation keys using the project's standard lookup pattern. No translation file edits in later phases. Include the reusable key reference in the plan's architectural decisions section so every phase can consult it.

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

**Architectural feasibility** — For each phase, verify that components can actually access the contexts/hooks/functions they're described as using. Check provider nesting, import paths, and module boundaries.

**Confidence scoring** — Rate each phase 0–10 for how likely an AI coding agent will implement it correctly from the plan alone. Flag any phase below 9 for revision.

If issues are found, fix them before proceeding. If any phase scores below 9, add concrete implementation details (code snippets, API configurations, exact function signatures) until it reaches 9+.

**Present verification results** — Show the user a summary table with each phase's initial confidence score (0–10), any issues found, and the changes made to resolve them. Do NOT proceed to Step 7 until the user explicitly approves. If the user requests changes, revise, re-verify, and present the updated results to the user for approval. Repeat until approved.

### 7. Write the plan file

**Prerequisite**: Step 6 verification results MUST have been presented to the user and explicitly approved before writing. If Step 6 has not been completed and approved, go back and complete it now.

Determine the plans directory using this precedence:
1. If `.agents/plans/` exists, use it
2. Else if `.claude/plans/` exists, use it
3. Else if `.agents/` exists, create `.agents/plans/` and use it
4. Else if `.claude/` exists, create `.claude/plans/` and use it
5. Otherwise, create `.plans/` and use it

Write the plan as a Markdown file named after the feature (e.g. `.agents/plans/user-onboarding-plan.md`). Use the template below.

<plan-template>
# Plan: <Feature Name>

> Source PRD: <brief identifier or link>

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
</plan-template>
