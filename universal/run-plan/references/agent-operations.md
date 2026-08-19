# Agent Operations

Load this reference once at Step 2 (before user confirmation) and keep it in working memory for the whole run. It contains the full agent-mode definitions and the per-section brief content that SKILL.md's skeleton refers to.

---

## Agent Modes (full definitions)

Each mode below lists a `subagent_type` — that value is Claude Code's reference agent type. On a host with a different delegation mechanism, map the mode's role onto its nearest isolated-context worker; the role definition, not the `subagent_type` string, is the contract.

### Research

Research runs in one of two tiers. The orchestrator picks the tier when it composes the topic, by the findings' **destination** — the selection rule lives in SKILL.md Step 3. The tier is a capability choice — a general-capability worker that writes its own findings file vs a read-only worker — so on another host, map by capability, not by these type names.

| Parameter     | File-backed (default) | Inline lookup |
| ------------- | --------------------- | ------------- |
| subagent_type | `general-purpose`     | `Explore`     |

**Role (both tiers):** Technical research assistant focused on gathering codebase context. Research never modifies the repo: no source, config, or test file is touched in either tier. The file-backed tier's one sanctioned write is its own findings file — its brief carries the Write Scope & Search Breadth section (below), and the orchestrator verifies the tree after it returns (SKILL.md Step 3's write-scope check).

**When to use:** Before implementation when the plan references unfamiliar code, or mid-execution when a phase needs more context than prior summaries provide.

**Expected output — file-backed tier:** The complete, structured findings — file paths, key interfaces/types, existing patterns, current line numbers, gotchas — WRITTEN to `<scratch_dir>/research-<topic>.md` (the orchestrator resolves and provides the exact path). Completeness wins over brevity in the file: include everything later phases will need, reference-dense (locations, excerpts, facts) rather than whole-file pastes. The RETURN is only a ≤8-line digest plus the file path — the full findings never appear in the returned message. The digest LEADS with any latent defect or interaction hazard the research uncovered (the facts that would change how a phase is implemented or ordered); structural summary takes whatever lines remain. A digest that names the architecture but drops a discovered hazard has buried its lede. Phase briefs point later Code agents at the file to read directly, as with every other file handoff; the detail never enters the orchestrator's context.

**Expected output — inline-lookup tier:** The complete answer RETURNED inline, in the same ≤8-line digest form — the digest IS the finding, and no file is created. `Explore` has no Write tool, so this tier is structurally incapable of the file handoff; that is exactly why it is reserved for answers small enough to inline. If a return proves the size was misjudged, the orchestrator persists the block verbatim to `<scratch_dir>/research-<topic>.md` and does not re-read it (accepted cost: those findings transit the orchestrator once and stay resident — a repeat miss is a tier-selection error to correct at Step 3, not a routine path).

### Code

| Parameter     | Value             |
| ------------- | ----------------- |
| subagent_type | `general-purpose` |

**Role:** Highly skilled software engineer who writes code that is performant, maintainable, accessible, and correct. If the workspace's AGENTS.md/CLAUDE.md defines a `Code Agent Role` section, use that as the role identity instead of this default.

**When to use:** For phases that create or modify code and tests. This is the primary workhorse mode.

**Expected output:** A terse structured summary per the Completion Requirement (status, files, tests, build, issues, deviations, incomplete criteria) PLUS the detailed downstream handoff written to `phase-<n>-handoff.md` and returned only as a path + 3-bullet précis. Judgment-relevant info (did it pass? risks? deviations?) is returned; bulky reference detail (which exported symbols live where, patterns to extend, hooks left open) goes to the handoff file the next phase reads.

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

**Role:** Independent reviewer auditing a phase's staged changes against its acceptance criteria. Adversarial by mandate: the job is to find where the implementation fails each criterion — a clean pass must be earned with evidence, not presumed. Read-only conduct toward the repo: never modify repository files, never run tests or builds; shell access is for `git diff`, `git log`, and read-only inspection only. The one sanctioned write is the reviewer's own evidence file (Expected output below).

Do not map this mode to a host's fast/small read-only worker tier (and never down-map Code/Architect/Debug for cost): the criteria audit needs the same model tier as the implementation it checks.

**When to use:** After every Code-mode phase (Step 4.5), before checkboxes are ticked or the phase is committed; re-run after any retry or Debug fix (full by default — the Scoped Re-review Exceptions section below can scope it, never skip it). Also used at branch scope for the pre-PR review (Step 5c.5).

**Independence rule:** The Review brief never includes the Code agent's summary or self-assessment. The reviewer re-derives criterion satisfaction from the diff and the codebase alone.

**Expected output — the verdict table:**

| Criterion (verbatim)  | Verdict       | Evidence                                          |
| --------------------- | ------------- | ------------------------------------------------- |
| <criterion 1>         | MET           | `path/file.ts:42` — <one-line why>                |
| <criterion 2>         | NOT MET       | <the concrete gap and where the fix belongs>      |
| <criterion 3>         | NEEDS-RUNTIME | <why it cannot be verified statically>            |

Plus a **scope-creep flag**: changes in the staged diff outside the Code brief's File Manifest and Scoped Task, or "None".

Plus **defects outside the criteria's wording** (required third section, never omitted): defects in the phase's changes — or in their direct interaction with existing code — that no acceptance criterion's wording covers, each verified against the code with `file:line` evidence and a one-line failure description, or an explicit "None". Over-documentation is a defect class like any other: a comment that restates the code, narrates the implementation, or explains a superseded attempt is reported with the same `file:line` evidence as a missing or stale one. Check the workspace's documentation guidance for its stated limits — a file header that exceeds them is a finding.

**The return splits by what the orchestrator acts on.** The full table above — every criterion's `file:line` evidence and the verified reasoning behind each MET — is WRITTEN to `<scratch_dir>/phase-<n>-review.md` (the orchestrator resolves and provides the path: unsuffixed for the phase's first review, then `-2`, `-3`, … for every later review spawn of the phase, whatever triggered it). RETURNED inline: one line per criterion (criterion verbatim + verdict, no evidence), the scope-creep flag, and every NOT MET / NEEDS-RUNTIME / CONFIRMED / PLAUSIBLE finding and out-of-criteria defect in full, unchanged — findings are what the orchestrator must act on and are never pushed to the file; MET evidence is what it never acts on and never stays inline. The evidence file is mandatory work, not bookkeeping: a MET with no `file:line` evidence recorded there is unverified. (The pre-PR variant returns findings only and writes no file.)

---

## Review Brief (dedicated composition)

Review agents do NOT use the 10-section skeleton. Their brief contains exactly:

1. **Role Preamble** — the Review role definition above, including the read-only conduct rule and the adversarial mandate: "Assume the implementation fails its criteria and hunt for where. A clean pass must be earned with evidence, not presumed."
2. **Scoped Task** — the phase description and acceptance criteria, verbatim from the plan (never paraphrased)
3. **File Manifest** — the same manifest the Code agent's brief carried (basis for the scope-creep check), plus any orchestrator-sanctioned changes, each named: pre-authorized cleanups assigned to this phase (SKILL.md Step 4 item 10) — in scope, not scope creep; the reviewer verifies each was actually applied and reports any that was not — and ordered comment deletions (SKILL.md Retry protocol), whose absent comment is not a defect
4. **Prior-phase interface pointers** — file + symbol names from earlier phases this phase builds on (pointers only, no restated signatures), with the caveat: handoffs are implementer-authored notes, not authority — if a handoff contradicts the plan, the plan wins
5. **Diff instruction** — "The phase's changes are staged. Obtain them yourself with `git diff --cached`; read any file in the repo you need for context. Do not modify anything." (For a scoped re-review, substitute the Scoped Diff instruction from the Scoped Re-review Exceptions section below — `git diff --cached` cannot isolate a post-verdict delta.)
6. **Output contract** — the return split from Expected output above (evidence table to the resolved `<scratch_dir>/phase-<n>-review.md` path, which this brief states; criterion + verdict lines, the scope-creep flag, and all findings inline), both required trailing sections included (the scope-creep flag and defects outside the criteria's wording — an explicit "None" each when empty), plus: "For every MET verdict record `file:line` evidence you actually verified in the evidence file — a MET without it is unverified. Then hunt beyond the criteria: report any defect in this phase's changes that no criterion's wording covers — criteria describe intended behaviour, and defects live in the states nobody wrote a criterion about — and over-documentation counts: a comment that restates the code or memorializes a superseded attempt is as much a defect as a missing one. If you cannot find a real failure, say so explicitly and name the strongest thing you checked that did NOT pan out — in five lines or fewer; it proves the gate ran, it is not a report section."

**Pre-PR variant (Step 5c.5):** substitute — scope = the branch diff, `git diff <base_branch>...HEAD`, or `git diff <inputs_commit_sha>...HEAD` when SKILL.md Step 5c.5 selects it (that step owns the selection rule; a mid-branch inputs commit keeps the `<base_branch>` ref and is named in the brief as out of scope instead); mandate = correctness bugs, with emphasis on integration seams between phases and on forward-compatibility hooks from phase summaries (the orchestrator lists them in the brief) that later phases should have resolved; output = surviving findings only, each verified against the code before reporting, with a CONFIRMED/PLAUSIBLE tag per finding. On Claude Code, instruct the sub-agent to invoke the installed `code-review` skill (effort medium) if available — it owns review methodology, including adversarial verification of findings; the generic mandate above is the fallback for hosts without it.

---

## Scoped Re-review Exceptions (SKILL.md Step 4 item 5)

The re-review after a post-verdict change is full by default. Two narrow exceptions scope it — never skip it. When in doubt, full.

**Establishing and transmitting the delta.** Both exceptions rest on knowing exactly what changed since the verdict, and the window for capturing that closes at re-staging: the index still holds the verdict-time state (item 5 staged it), so until `git add` runs again, `git diff --name-only` (with keep-dirty paths declared: `git diff --name-only -- . <keep_dirty_pathspec>`, or the keep-dirty entries always pollute the list) IS the tracked delta — names only; do not read the diff's content (Context Discipline). Add any `??` paths from `git status --porcelain`: a file the fix created is untracked and invisible to `git diff`, but it is delta all the same. Every file absent from both lists is untouched since the verdict. Once re-staged, the delta is unrecoverable from git — the reviewer's `git diff --cached` diffs against HEAD, which predates the phase, so it shows all of the phase's work and says nothing about what changed since the verdict. The moment a scoped exception applies:

1. **Extract baselines** — for each file in the names-only delta, capture its verdict-time content from the index without reading it: `git show :<path> > <scratch_dir>/baseline-<basename>`. A path `git show :` cannot resolve is new since the verdict: it has no baseline, the whole file is delta, and it must independently satisfy the exception's file-class rules below.
2. **Re-stage** (`git add -A`, exclusion form under keep-dirty paths), then spawn the scoped Review agent with the Scoped Diff instruction below in place of Review Brief §5, the delta's file list (path + baseline path per file), and — verbatim in the brief — every scoped-reviewer obligation from the exceptions below that applies to the delta: the file-class mandates, the "In both classes" obligations, and the escalation protocol. The scoped reviewer never loads this reference, so an obligation absent from the brief does not exist for it.
3. **Clean up** — baselines are deleted with the phase's other scratch files when the commit lands (Step 4 item 7) and in a retry revert; a stale baseline would hand a later scoped review the wrong delta.

**Scoped Diff instruction (replaces Review Brief §5):**

> Scope = the post-verdict delta only. For each file listed in this brief, obtain the delta with `diff <scratch_dir>/baseline-<basename> <path>` — that diff IS the delta, authoritative and complete; a listed file with no baseline is new since the verdict and is delta in full. Do NOT use `git diff --cached` to establish the delta: the index diffs against HEAD, which predates the phase, so it surfaces all of the phase's work and says nothing about what changed since the verdict. Read any file in the repo you need for context. Do not modify anything.

**Exception 1 — dependency or generated artifacts** (lockfiles, snapshots, codegen output). Scope the re-review to the delta plus the acceptance criteria it touches, only once all three hold: (a) the delta is established by the names-only mechanism above, never by eyeball; (b) no source, config, or test file appears in it — a config file forces the full re-review, no exceptions; a test file or a `[comment-only]`-marked production source file routes to Exception 2, and any other production source file forces the full re-review; (c) a Debug agent re-verified the runtime criteria the delta affects (its own post-fix verification satisfies this). What makes this narrow case safe: (a) proves the reviewed code is byte-identical, and (b) confines the change to artifacts no acceptance criterion is written against — so the verdict still covers everything it originally covered.

**Exception 2 — test files, and comment-only deltas in production source** — established by the same names-only mechanism; if generated or dependency artifacts appear alongside, they must independently satisfy Exception 1's conditions, and any config file — or any production source file whose changes the fix agent's summary did not mark `[comment-only]` (Completion Requirement §9) — forces the full re-review. The orchestrator never judges comment-onlyness itself (names-only; it must not read the diff): the fix agent's declaration admits the file, and the scoped reviewer proves or refutes it. Each file class carries its own scoped mandate:

- **Test files:** verify the change is purely additive — any weakened or removed existing assertion escalates to the full re-review, because a deleted assertion may be the very evidence a MET verdict rested on — and that new assertions are discriminating for the criteria they claim to cover, not tautological. A comment-only edit inside a test file qualifies too: nothing added or removed still passes the weakened-or-removed check.
- **Production source, declared comment-only:** the reviewer's FIRST task is to verify the declaration from the baseline diffs. Escalate to the full re-review on either: (a) any changed line that is not a comment — code, string literal, anything a parser executes; (b) any changed comment a tool reads rather than a human — lint suppressions (`eslint-disable`, `noqa`), type-checker pragmas (`@ts-ignore`, `type: ignore`), coverage or bundler directives (`istanbul ignore`, `webpackChunkName`): lexically comments, but they change lint, type, coverage, or build output, so the prior verdict does not cover them. A production file with no baseline (new since the verdict) never qualifies.

In both classes the scoped review fact-checks every changed comment's claims against the code — a deleted comment claims nothing and needs no check (comment-only fixes are the most common corrective-pass shape) — and re-verifies any acceptance criterion that constrains comment or documentation content, always including the criterion whose finding triggered the fix, when one did; every other criterion stands on the baseline-proven identity of the code (re-verification by proof, not a carried verdict).

**Escalation is a return, not a self-widening.** A scoped reviewer that hits any escalation condition stops and returns `ESCALATE — <the failed condition>` with no verdicts; the orchestrator then spawns a fresh full Review agent, exactly as if no exception had applied. A verdict from a run that escalated is never salvaged.

What makes this case safe: the names-only delta plus the reviewer-verified comment-only check prove the reviewed executable code is byte-identical since the verdict, so the prior verdict still covers it, and the delta itself gets a fresh scoped verdict.

---

## Brief Sections (full content)

SKILL.md lists the 10 section names that every brief must include. The exact content for each section is below. Sections 5–7, 9, and 10 — and §2's static directives (documentation budget, the AGENTS.md/CLAUDE.md read directive, the project conventions extracted at Step 1d) — are run-static: the orchestrator writes their full text once to `<scratch_dir>/run-conventions.md` at Step 2 (SKILL.md → Brief composition) and each brief points there instead of restating them. The concrete per-phase paths those sections reference (commit-message file, handoff file) are still named inline in every brief.

### 1. Role Preamble

State which mode the agent is operating in using the role definition from the Agent Modes section above.

### 2. Codebase Context

**Reference, don't re-embed** (the orchestrator's main context-cost lever): cite the plan section, the research file(s), and the prior phase's handoff by PATH for the agent to read itself — do not paste their contents into the brief. Include:

- The plan's architectural-decisions section BY REFERENCE ("read `## Architectural decisions` in the plan file — verbatim; do not rely on paraphrase"), not re-transcribed
- Prior Research findings BY PATH (`research-<topic>.md`)
- Prior phases' handoffs BY PATH (`phase-<n>-handoff.md`)
- The primary workspace and a directive to read its `AGENTS.md` and/or `CLAUDE.md` files for project conventions
- Inline ONLY the phase-specific deltas/corrections not captured in those files (e.g. line-number drift since the plan was written, a resolved ambiguity)
- **Documentation budget** — for every mode that writes code (Code, Debug, retries), include this directive verbatim:

  > Follow the workspace's own documentation guidance: where it calls for documentation (file headers, boundary TSDoc, incident notes), write it, at the size it states — its limits are limits, not floors. Beyond what that guidance requires, add a comment only where a maintainer would otherwise make a wrong change, and state the fact in a sentence, not a paragraph. Comment only on what this phase's own diff makes true — never on reachability, caller inventories, or cross-phase invariants whose truth lives in code this phase cannot see; the phase that completes a behaviour owns any comment about it. Do not document why a previous attempt was wrong — git history holds that. A comment that restates what the code says is a defect, not diligence.

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

### 7. Commit Message Directive (Code mode only)

Include this directive for every Code mode agent in a commit-producing run (in local-only mode, replace the ticket sentence with: "This run has no ticket identifier — do not infer one from the branch name or anywhere else."):

> After the build gate passes, read the installed `commit` skill — the single source of truth for message format — and write a commit message conforming to it for this phase's changes, saved to `<scratch_dir>/phase-<n>-commit-msg.md` (the orchestrator gives you the concrete resolved path). Write the file as raw commit-message text — no code fence, no Markdown wrapper, no preamble: the orchestrator passes it verbatim to `git commit -F`, so a stray leading fence line becomes the commit subject. Include any commit trailers the environment or repository requires (your harness instructions state them; `git log -1` shows the set already in use on this branch). Nothing is staged in your session: treat your phase's full working-tree diff (`git diff` plus any new files you created) as the staged changes that skill refers to. Use `#<plan_sub_issue_number>` as the ticket identifier. Do NOT run `git commit` — the orchestrator owns commits.

### 8. Write Scope & Search Breadth (file-backed Research tier only)

Include this directive verbatim for every file-backed Research agent — it carries the tier's single write authorization (verified by the orchestrator with `git status --porcelain` after the agent returns; SKILL.md Step 3) and its search-breadth contract:

> Write exactly one file: `<scratch_dir>/research-<topic>.md` (the orchestrator gives you the concrete resolved path). That is your only write. Never modify repository source, config, tests, or any other file — your job is to read the codebase and record findings, not to change anything.
>
> **Search breadth: very thorough** — search exhaustively across multiple locations and naming conventions; do not stop at the first set of plausible matches.

### 9. Completion Requirement

> When finished, provide a summary using this exact structure:
>
> **STATUS:** COMPLETE | PARTIAL | BLOCKED
>
> **Files changed:**
>
> - `path/to/file.ts` — description of change
>
> (In a fix cycle — retry or corrective pass — append `[comment-only]` to a file's description when your changes to it touch only comments. The orchestrator's re-review routing depends on that marker being present and truthful; a marker on a file with any non-comment change is refuted by the scoped reviewer and costs a full re-review.)
>
> **Tests:** N written, N passing, N failing
>
> **Build:** PASS | FAIL (with error summary if failed)
>
> **Issues:** description of any problems encountered and resolutions (or "None")
>
> **Incomplete criteria:** list any acceptance criteria not met and why (or "None")
>
> **Downstream handoff:** WRITE the detailed handoff for later phases to `<scratch_dir>/phase-<n>-handoff.md` (the orchestrator gives you the concrete resolved path) — do NOT inline it in this returned summary. In the file, document for every file created or significantly modified: key exported symbols and types by name and path; component state approach; patterns later phases should extend; and any forward-compatibility hooks left for later phases (e.g. "`getCardPath(config)` currently returns the route's default path — Phase 6 should replace this with crew path logic"). The handoff carries paths, symbol names, and facts stated in prose — never a pasted code block, a line number, or a count (of tests, files, assertions): each is a second copy of something the repo itself records, it goes stale the moment a later phase touches the code, and its reader has no way to see that it did. The next agent reads the named files directly. In THIS summary, give ONLY a 3-bullet précis plus the file path (e.g. "Handoff → phase-2-handoff.md: wrapper prop surface + effect dep arrays; provider `mediaRef` contract; `renderWithVideoState` usage"). The next phase's brief points its agent at the file, so the full detail never enters the orchestrator's context. If no downstream phases depend on this work, write "Downstream handoff: none" and skip the file.

### 10. Boundary Statement

> These instructions define your complete scope. Only perform the work outlined above. Do not refactor unrelated code, add features beyond the acceptance criteria, or deviate from the plan. Write only the files your task requires plus the `<scratch_dir>` files this brief names (`<scratch_dir>` is git-ignored and safe). Never create backup or working copies anywhere else — `.bak` files, saved tool output, coverage dumps: the orchestrator stages with `git add -A`, so a stray file lands in the phase's commit or forces a wider re-review. To recall a file's last committed content, use `git show HEAD:<path>` instead of copying the file.
