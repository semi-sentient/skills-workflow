# Agent Operations

Read this when SKILL.md points here: to compose an Architect or Debug brief (the five templated briefs need nothing from this file), or when a scoped re-review looks applicable (Scoped Re-review Exceptions). It is not held in working memory; the brief templates under `briefs/` are the definitions the agents actually receive, and `rp.sh brief` fills them.

---

## Agent Modes

Each mode names a `subagent_type` — Claude Code's reference agent type. On a host with a different delegation mechanism, map the mode's role onto its nearest isolated-context worker; the role definition, not the `subagent_type` string, is the contract.

### Research

Two tiers, picked by the findings' **destination** when the topic is composed (SKILL.md Step 3): a general-capability worker that writes its own findings file versus a read-only worker. On another host, map by capability, not by these type names.

| Parameter     | File-backed (default) | Inline lookup |
| ------------- | --------------------- | ------------- |
| subagent_type | `general-purpose`     | `Explore`     |
| brief         | `brief-research.md`   | composed inline: the topic question, the plan/spec pointers, "return the complete answer in ≤8 lines; write nothing" |

Research never modifies the repo in either tier. The file-backed tier's one sanctioned write is its findings file; the orchestrator verifies the tree after it returns (Step 3's write-scope check). `Explore` has no Write tool, so the inline tier is structurally incapable of the file handoff — that is why it is reserved for answers small enough to inline. If an inline return proves the size was misjudged, persist the block verbatim to `<scratch_dir>/research-<topic>.md` and do not re-read it (accepted cost: those findings transit the orchestrator once); a repeat miss is a tier-selection error to correct at Step 3, not a routine path.

### Code

`subagent_type: general-purpose` · brief: `brief-code.md`. The primary workhorse: a highly skilled software engineer, for phases that create or modify code and tests. Expected output: the Completion Requirement summary (status, files, tests, build, issues, incomplete criteria by label) plus the downstream handoff written to `phase-<n>-handoff.md` and returned only as a path + 3-bullet précis. Judgment-relevant information (did it pass? risks? deviations?) is returned; bulky reference detail goes to the handoff file the next phase reads.

### Architect

`subagent_type: general-purpose` · brief composed inline (sections below).

**Role:** Experienced technical leader who evaluates architectural tradeoffs, resolves design ambiguities, and makes structural decisions. Gathers context, weighs alternatives, and produces a clear recommendation — does not implement code.

**When to use:** a phase description is ambiguous about _how_ to structure something (multiple valid approaches exist); a Code agent reports PARTIAL or BLOCKED due to an unanticipated architectural decision; a completed phase reveals that a later phase's planned approach needs revision; the orchestrator needs to evaluate cross-phase impact before proceeding.

**Protocol:** (1) read the relevant files and understand the current state; (2) identify the design options with their tradeoffs; (3) recommend a single approach with clear rationale; (4) specify exactly what the Code agent should do (file paths, patterns to follow, interfaces to create).

**Expected output:** a concrete recommendation — not a list of options. Include the chosen approach, why alternatives were rejected, and implementation guidance specific enough that the Code agent can execute without further design decisions. Written to `<scratch_dir>/architect-<topic>.md`; returned as a ≤8-line digest plus the path.

### Debug

`subagent_type: general-purpose` · brief composed inline (sections below).

**Role:** Expert software debugger specializing in systematic problem diagnosis and resolution.

**When to use:** a Code agent reports failures, test errors, or unexpected behavior it couldn't resolve; a human reports a failure at a human gate; a pre-commit hook rejects the phase's commit.

**Diagnostic protocol:** (1) reflect on 5–7 possible sources of the problem; (2) narrow to the 1–2 most likely causes; (3) investigate those causes (read files, inspect state, add logging); (4) implement the fix; (5) verify the fix and run the test suite.

**Expected output:** root cause, fix applied (Files-changed list, `[comment-only]` marked where true), test results, related issues discovered. A Debug brief carries no Commit Message Directive: the fix is committed via the fallback path.

**Composing an Architect or Debug brief inline.** Write it to `<scratch_dir>/phase-<n>-brief-<architect|debug>.md` and spawn with the standard pointer line. Sections: (1) role preamble — the Role text above; (2) codebase context — the plan file and `## Architectural decisions` by reference, the phase's `phase-<n>-spec.md`, research files and handoffs by path, and the failure description or design question in 2–5 sentences; (3) `Read <scratch_dir>/run-conventions.md in full; the blocks labelled All modes` — plus `Code and Debug modes` for Debug — `are part of this brief`; (4) the task; (5) expected output as above. Do not paste criteria, research, or handoff text into it.

### Review

`subagent_type: general-purpose` (read-only conduct — the brief says so) · brief: `brief-review.md` for a phase's first review and every full re-review; `brief-rereview.md` for a scoped re-review; the pre-PR variant below at Step 5c.5.

Do not map this mode to a host's fast/small read-only worker tier (and never down-map Code/Architect/Debug for cost): the criteria audit needs the same model tier as the implementation it checks.

**Independence rule:** the Review brief never includes the Code agent's summary or self-assessment, and a full re-review never names the prior review's findings as "fixed" — the reviewer re-derives criterion satisfaction from the diff and the codebase alone. The only orchestrator-authored content in the brief is the manifest, the pointers, the human-form labels, and the sanctioned-changes list (pre-authorized cleanups and ordered comment deletions, which the reviewer verifies were applied).

**Return contract** (the template states it; the orchestrator routes on it): one `C<k>: VERDICT` line per criterion (`MET`, `NOT MET`, `NEEDS-RUNTIME`, `HUMAN-GATE`), a `Scope creep:` line, a `Weak criteria:` line, and `Findings:` numbered `F1…` in full — each tagged `behaviour` or `documentation`, comment findings ending with a `required-by:` token. The evidence table (per-criterion `file:line` evidence) is written to the evidence path the brief names and is never returned inline; the orchestrator confirms the file exists (`ls`) and never reads it. Findings are what the orchestrator acts on, and later briefs cite them by file and number (fix-cycles.md). A `HUMAN-GATE` on a criterion the brief did not place is resolved first (human-gate.md).

---

## Scoped Re-review Exceptions (SKILL.md Step 4 item 5)

The re-review after a post-verdict change is full by default. Two narrow exceptions scope it — never skip it. When in doubt, full.

**Establishing and transmitting the delta.** Both exceptions rest on knowing exactly what changed since the verdict, and the window for capturing that closes at re-staging: the index still holds the verdict-time state (item 5 staged it), so until `rp.sh stage` runs again, `rp.sh delta` IS the tracked-plus-untracked delta since the verdict — names only, keep-dirty paths and the plan file already excluded (item 5's invariant exempts the plan file's edits, so it is never delta). Once re-staged, the delta is unrecoverable from git — the reviewer's `git diff --cached` diffs against HEAD, which predates the phase. The moment a scoped exception looks applicable:

1. **`rp.sh baselines`** — after the fix agent has returned and before `rp.sh stage` (earlier there is no delta and it saves nothing; later the delta is gone) — saves each delta file's verdict-time content from the index to `<scratch_dir>/baseline-<path with / as __>` without the orchestrator reading it, and prints one `path<TAB>baseline-…` line per file; `path<TAB>new` for a file the index does not hold (new since the verdict: no baseline, the whole file is delta, and it must independently satisfy the exception's file-class rules); `path<TAB>deleted` for a tracked file the fix removed (its class is judged from the path; the reviewer sees the deletion in full).
2. **Classify each path by name alone** (rules below) and decide: every path admissible → scoped; any path not → full re-review, and the baselines are simply deleted at cleanup.
3. **`rp.sh stage`**, then `rp.sh brief brief-rereview.md …` with `DELTA_FILES` holding one line per file — `<path> — <class> — <baseline-… | new | deleted>`, appending `, declared [comment-only]` where the fix agent's summary marked it — and `TRIGGER_CRITERIA` naming the criterion whose finding triggered the fix (when one did) and, under Exception 1, every acceptance criterion the changed artifacts affect (a lockfile touches the criteria that run the build or tests; a snapshot touches the criteria its test covers). The class mandates and the escalation protocol are in the template verbatim, so no obligation depends on the orchestrator restating it.
4. **Clean up** — `rp.sh cleanup <n>` deletes the baselines with the phase's message file when the commit lands, and a retry's default revert does the same; a stale baseline would hand a later scoped review the wrong delta.

**Exception 1 — dependency or generated artifacts** (lockfiles, snapshots, codegen output). Scope the re-review to the delta plus the acceptance criteria it touches, only once all three hold: (a) the delta is established by `rp.sh delta`, never by eyeball; (b) no source, config, or test file appears in it — a config file forces the full re-review, no exceptions; a test file, a documentation file, or a `[comment-only]`-marked production source file routes to Exception 2, and any other production source file forces the full re-review; (c) a Debug agent re-verified the runtime criteria the delta affects (its own post-fix verification satisfies this). What makes this narrow case safe: (a) proves the reviewed code is byte-identical, and (b) confines the change to artifacts no acceptance criterion is written against — so the verdict still covers everything it originally covered.

**Exception 2 — test files, documentation files, and comment-only deltas in production source** — established by the same names-only mechanism; if generated or dependency artifacts appear alongside, they must independently satisfy Exception 1's conditions, and any config file — or any production source file whose changes the fix agent's summary did not mark `[comment-only]` — forces the full re-review. The documentation class is decided from the path alone, so the orchestrator never opens the file: `.md`, `.txt`, `.rst`, and `.adoc` files are documentation files — EXCEPT agent-instruction files, which are config and force the full re-review: `AGENTS.md`, `CLAUDE.md`, and files with those four extensions under `.agents/`, `.claude/`, or `.github/` (Step 1d reads them to set run behaviour, so an edit changes what the run does). The exception reclassifies only documentation-extension files; any other file under those directories was never in this class and takes its own class as usual (a `.mjs` hook under `.agents/` is production source, admitted to a scoped re-review only by a `[comment-only]` declaration). Everything else — `.tf`, JSON settings, lockfiles, CI YAML, however prose-dense — is production source or config by its own rules. (A Markdown file some docs build or linter consumes still lands in the documentation class; the template's fact-check mandate covers that residual risk.) The orchestrator never judges comment-onlyness itself — not by reading the diff, not by a changed-line count, not by a comment-stripped digest (names-only, always): the fix agent's declaration admits the file, and the scoped reviewer proves or refutes it.

**Escalation is a return, not a self-widening.** A scoped reviewer that hits any escalation condition stops and returns `ESCALATE — <the failed condition>` with no verdicts; the orchestrator `rm -f`s that spawn's evidence path (partial evidence is not an audit record) and spawns a fresh full Review agent, exactly as if no exception had applied. A verdict from a run that escalated is never salvaged.

What makes this case safe: the names-only delta plus the reviewer-verified comment-only check prove the reviewed executable code is byte-identical since the verdict, so the prior verdict still covers it, and the delta itself gets a fresh scoped verdict.
