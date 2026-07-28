# Agent Operations

Load this reference once at Step 2 (before user confirmation) and keep it in working memory for the whole run. It contains the full agent-mode definitions and the per-section brief content that SKILL.md's skeleton refers to.

---

## Agent Modes (full definitions)

Each mode below lists a `subagent_type` — that value is Claude Code's reference agent type. On a host with a different delegation mechanism, map the mode's role onto its nearest isolated-context worker; the role definition, not the `subagent_type` string, is the contract.

### Research

| Parameter     | Value     |
| ------------- | --------- |
| subagent_type | `Explore` |

**Role:** Technical research assistant focused on gathering codebase context.

**When to use:** Before implementation when the plan references unfamiliar code, or mid-execution when a phase needs more context than prior summaries provide.

**Expected output:** A complete, structured findings block RETURNED inline — file paths, key interfaces/types, existing patterns, current line numbers, gotchas — topped by a ≤8-line digest of the headline facts. Completeness wins over brevity: include everything later phases will need. Keep it reference-dense (locations, excerpts, facts) rather than pasting whole files. `Explore` has no Write tool, so the ORCHESTRATOR persists the findings block verbatim to `<scratch_dir>/research-<topic>.md` the moment it returns and does not re-read it afterward — phase briefs point later Code agents at the file to read directly, as with every other file handoff. (Accepted cost: research findings transit the orchestrator's context once on return.)

### Code

| Parameter     | Value             |
| ------------- | ----------------- |
| subagent_type | `general-purpose` |

**Role:** Highly skilled software engineer who writes code that is performant, maintainable, accessible, and correct. If the workspace's AGENTS.md/CLAUDE.md defines a `Code Agent Role` section, use that as the role identity instead of this default.

**When to use:** For phases that create or modify code and tests. This is the primary workhorse mode.

**Expected output:** A terse structured summary per the Completion Requirement (status, files, tests, build, issues, deviations, incomplete criteria) PLUS the detailed downstream handoff written to `phase-<n>-handoff.md` and returned only as a path + 3-bullet précis. Judgment-relevant info (did it pass? risks? deviations?) is returned; bulky reference detail (interface signatures, line numbers, patterns) goes to the handoff file the next phase reads.

### Architect

| Parameter     | Value             |
| ------------- | ----------------- |
| subagent_type | `general-purpose` |

**Role:** Experienced technical leader who evaluates architectural tradeoffs, resolves design ambiguities, and makes structural decisions. Gathers context, weighs alternatives, and produces a clear recommendation — does not implement code.

**When to use:**

- A phase description is ambiguous about _how_ to structure something (multiple valid approaches exist)
- A Code agent reports PARTIAL or BLOCKED due to an unanticipated architectural decision
- A completed phase reveals that a later phase's planned approach needs revision
- The orchestrator needs to evaluate cross-phase impact before proceeding

**Protocol:**

1. Read the relevant files and understand the current state
2. Identify the design options with their tradeoffs
3. Recommend a single approach with clear rationale
4. Specify exactly what the Code agent should do (file paths, patterns to follow, interfaces to create)

**Expected output:** A concrete recommendation — not a list of options. Include the chosen approach, why alternatives were rejected, and implementation guidance specific enough that the Code agent can execute without further design decisions.

### Debug

| Parameter     | Value             |
| ------------- | ----------------- |
| subagent_type | `general-purpose` |

**Role:** Expert software debugger specializing in systematic problem diagnosis and resolution.

**When to use:** When a Code agent reports failures, test errors, or unexpected behavior that it couldn't resolve.

**Diagnostic protocol:**

1. Reflect on 5-7 possible sources of the problem
2. Narrow to the 1-2 most likely causes
3. Investigate those causes (read files, inspect state, add logging)
4. Implement the fix
5. Verify the fix and run the test suite

**Expected output:** Root cause, fix applied, test results, related issues discovered.

### Review

| Parameter     | Value                                              |
| ------------- | -------------------------------------------------- |
| subagent_type | `general-purpose` (read-only conduct — see below)  |

**Role:** Independent reviewer auditing a phase's staged changes against its acceptance criteria. Adversarial by mandate: the job is to find where the implementation fails each criterion — a clean pass must be earned with evidence, not presumed. Read-only conduct: never modify files, never run tests or builds; shell access is for `git diff`, `git log`, and read-only inspection only.

Do not map this mode to a host's fast/small read-only worker tier (and never down-map Code/Architect/Debug for cost): the criteria audit needs the same model tier as the implementation it checks.

**When to use:** After every Code-mode phase (Step 4.5), before checkboxes are ticked or the phase is committed; re-run in full after any retry or Debug fix. Also used at branch scope for the pre-PR review (Step 5c.5).

**Independence rule:** The Review brief never includes the Code agent's summary or self-assessment. The reviewer re-derives criterion satisfaction from the diff and the codebase alone.

**Expected output — the verdict table:**

| Criterion (verbatim)  | Verdict       | Evidence                                          |
| --------------------- | ------------- | ------------------------------------------------- |
| <criterion 1>         | MET           | `path/file.ts:42` — <one-line why>                |
| <criterion 2>         | NOT MET       | <the concrete gap and where the fix belongs>      |
| <criterion 3>         | NEEDS-RUNTIME | <why it cannot be verified statically>            |

Plus a **scope-creep flag**: changes in the staged diff outside the Code brief's File Manifest and Scoped Task, or "None".

For an all-MET phase, keep the returned table compact — one line of evidence per criterion (`file:line — why`), not paragraphs. NOT MET / NEEDS-RUNTIME / CONFIRMED / PLAUSIBLE findings always stay inline in full: those are what the orchestrator must act on, and must never be pushed to a file.

---

## Review Brief (dedicated composition)

Review agents do NOT use the 9-section skeleton. Their brief contains exactly:

1. **Role Preamble** — the Review role definition above, including the read-only conduct rule and the adversarial mandate: "Assume the implementation fails its criteria and hunt for where. A clean pass must be earned with evidence, not presumed."
2. **Scoped Task** — the phase description and acceptance criteria, verbatim from the plan (never paraphrased)
3. **File Manifest** — the same manifest the Code agent's brief carried (basis for the scope-creep check)
4. **Prior-phase interface pointers** — file + symbol names from earlier phases this phase builds on (pointers only, no restated signatures)
5. **Diff instruction** — "The phase's changes are staged. Obtain them yourself with `git diff --cached`; read any file in the repo you need for context. Do not modify anything."
6. **Output contract** — the verdict table format above, plus: "For every MET verdict cite `file:line` evidence you actually verified. If you cannot find a real failure, say so explicitly and name the strongest thing you checked that did NOT pan out."

**Pre-PR variant (Step 5c.5):** substitute — scope = the full branch diff (`git diff <base_branch>...HEAD`); mandate = correctness bugs, with emphasis on integration seams between phases and on forward-compatibility hooks from phase summaries (the orchestrator lists them in the brief) that later phases should have resolved; output = surviving findings only, each verified against the code before reporting, with a CONFIRMED/PLAUSIBLE tag per finding. On Claude Code, instruct the sub-agent to invoke the installed `code-review` skill (effort medium) if available — it owns review methodology, including adversarial verification of findings; the generic mandate above is the fallback for hosts without it.

---

## Brief Sections (full content)

SKILL.md lists the 9 section names that every brief must include. The exact content for each section is below.

### 1. Role Preamble

State which mode the agent is operating in using the role definition from the Agent Modes section above.

### 2. Codebase Context

**Reference, don't re-embed** (the orchestrator's main context-cost lever): cite the plan section, the research file(s), and the prior phase's handoff by PATH for the agent to read itself — do not paste their contents into the brief. Include:

- The plan's architectural-decisions section BY REFERENCE ("read `## Architectural decisions` in the plan file — verbatim; do not rely on paraphrase"), not re-transcribed
- Prior Research findings BY PATH (`research-<topic>.md`)
- Prior phases' handoffs BY PATH (`phase-<n>-handoff.md`)
- The primary workspace and a directive to read its `AGENTS.md` and/or `CLAUDE.md` files for project conventions
- Inline ONLY the phase-specific deltas/corrections not captured in those files (e.g. line-number drift since the plan was written, a resolved ambiguity)

### 3. File Manifest

Every Code agent brief must include two file lists extracted from the plan and prior phase summaries:

**Files to modify** — files this phase will edit. The agent MUST read each one before making any changes.

> Before modifying any file, read it first to understand its current state. Do not assume file contents based on the plan description or prior phase summaries alone — always verify by reading.

**Files to reference** — files this phase should read for patterns, interfaces, or context, even if it won't modify them (e.g., "read `UserMenu.tsx` to match the Menu/Popover pattern").

### 4. Scoped Task

The specific work for this phase — paste the phase description and acceptance criteria from the plan. Be explicit about what is in scope and what is not.

### 5. TDD Directive (Code mode only)

Include this directive for every Code mode agent:

> Before writing any implementation code, read the installed `tdd` skill and its supporting docs. Follow the red-green-refactor workflow: write ONE test → verify RED → write minimal code → verify GREEN → repeat. For bug fixes, use the prove-it pattern.

### 6. Build Verification Gate (Code mode only)

Include this directive for every Code mode agent:

> After all implementation and tests are complete, run the project's build validation command (consult AGENTS.md/CLAUDE.md for the exact command). ALL checks must pass. If the build fails, fix the issues before reporting completion. Include the build result (pass/fail) in your summary.

### 7. Commit Message Directive (Code mode only; omit under `--no-commits`)

Include this directive for every Code mode agent in a commit-producing run (drop the ticket sentence in local-only mode):

> After the build gate passes, read the installed `commit` skill — the single source of truth for message format — and write a commit message conforming to it for this phase's changes, saved to `<scratch_dir>/phase-<n>-commit-msg.md` (the orchestrator gives you the concrete resolved path). Nothing is staged in your session: treat your phase's full working-tree diff (`git diff` plus any new files you created) as the staged changes that skill refers to. Use `#<plan_sub_issue_number>` as the ticket identifier. Do NOT run `git commit` — the orchestrator owns commits.

### 8. Completion Requirement

> When finished, provide a summary using this exact structure:
>
> **STATUS:** COMPLETE | PARTIAL | BLOCKED
>
> **Files changed:**
>
> - `path/to/file.ts` — description of change
>
> **Tests:** N written, N passing, N failing
>
> **Build:** PASS | FAIL (with error summary if failed)
>
> **Issues:** description of any problems encountered and resolutions (or "None")
>
> **Incomplete criteria:** list any acceptance criteria not met and why (or "None")
>
> **Downstream handoff:** WRITE the detailed handoff for later phases to `<scratch_dir>/phase-<n>-handoff.md` (the orchestrator gives you the concrete resolved path) — do NOT inline it in this returned summary. In the file, document for every file created or significantly modified: key exported interfaces/types with signatures; helper/utility signatures; component state approach; patterns later phases should extend; and any forward-compatibility hooks left for later phases (e.g. "`getCardPath(config)` currently returns `ROUTES[config.routeKey].defaultPath` — Phase 6 should replace this with crew path logic"). In THIS summary, give ONLY a 3-bullet précis plus the file path (e.g. "Handoff → phase-2-handoff.md: wrapper prop surface + effect dep arrays; provider `mediaRef` contract; `renderWithVideoState` signature"). The next phase's brief points its agent at the file, so the full detail never enters the orchestrator's context. If no downstream phases depend on this work, write "Downstream handoff: none" and skip the file.

### 9. Boundary Statement

> These instructions define your complete scope. Only perform the work outlined above. Do not refactor unrelated code, add features beyond the acceptance criteria, or deviate from the plan.
