# Run ledger and progress reporting (SKILL.md Step 4 items 8–9, Step 5)

Read this when a usage figure needs interpreting — a host that exposes no `<usage>` block, an `n/a` row, a question about what the token figures mean — or when the progress table needs more than SKILL.md's compact rule says. `rp.sh ledger` and `rp.sh phase-cost` do the recording and the arithmetic; this file explains what the figures are.

## The ledger

`<scratch_dir>/ledger.md` is append-only and the single source of truth for per-sub-agent cost and time; the progress table and the completion summary render from it. Because it is a file, it survives context compaction: late-run reporting stays accurate after early phases are summarized out of context. `rp.sh init` creates it, so it exists before the run's first sub-agent spawn.

Every time ANY sub-agent returns — Research, Code, Architect, Debug, Review; every step including retries, the Debug → re-review cycle, the pre-PR branch review, and post-run follow-ups — append one row from its `<usage>` block:

```
bash <scratch_dir>/rp.sh ledger <phase> <mode> <subagent_tokens> <tool_uses> <duration_ms> [group] [note]
```

- **Phase** is the plan's phase id (`3`, `6A`), or `setup` for whole-run research, `pre-PR` for the branch review, `followup` for post-run fixes. Mid-phase research (fix-cycles.md item 4) takes its phase's id.
- **Mode** is one word: `Research`, `Code`, `Architect`, `Debug`, `Review`. Retries and re-reviews keep their mode; the Note carries the qualifier. A Diagnose spawn (human-gate.md) is recorded as `Research` with Note `diagnose C<k>`.
- **group** is blank for a solo spawn and **required** for every row of a concurrent batch: the rows share a short label (`R1`, `R2`, …) and `phase-cost` / `totals` count the group's **max** duration, not its sum. The column is the only record of concurrency — nothing infers it from timestamps, and both commands warn when two or more `setup` rows carry none (the shape both September live runs left, then corrected by hand in prose). Pass `""` to skip it when a note follows.
- **note** names what the row was: `all MET`, `retry 1/2`, `corrective 2/2`, `deletion 1/1`, `re-review`, `no budget` (a hook-failure Debug), `reopened C<k>` (a criterion added or reopened mid-run — fix-cycles.md; it draws no budget), a death (`died — no return`; the re-spawn's row carries the Note its dead predecessor would have — the cycle is charged once). The tracker flags and any mid-run budget claim derive from these Notes, never from memory.
- Record raw numbers; `phase-cost` formats. A field the host did not expose is `n/a` — never fabricated.
- Only sub-agent returns become rows. Orchestrator-side commands (a pre-commit hook, `rp.sh` calls, a human-gate check, an `rp.sh wait`) are never ledger rows and never enter Active time; the earlier option of bracketing one heavy command with `date` was dropped with the script — do not re-add it as a `Code` row.

**`subagent_tokens` is cumulative tokens the agent processed across its internal turns — throughput, not peak context occupancy.** Report it as throughput; do NOT present it as "% of context window" (a long agent can process far more than the window without ever occupying it). Per-agent tokens are a **cost** signal; `tool_uses` is the closest available **occupancy** proxy — nothing evicts within a single sub-agent, so its context grows monotonically with tool-using turns, and a 250-call agent ran far closer to its window than a 30-call one whatever their token figures suggest. True peak occupancy is unmeasured on this host.

**This is a cost ledger, not a context-health ledger.** It records what each sub-agent spent; it says nothing about what stays resident in the orchestrator's own context — that occupancy is unmeasured (no mid-run signal exposes it) and is the cost Context Discipline exists to bound. Do not read a fully-populated ledger as evidence the run was context-lean.

All reported timing derives from summed `duration_ms` (parallel groups at their max) — never wall-clock `date` diffs across turns, which absorb laptop-closed / dropped-connection / checkpoint-pause idle and misreport. `RUN_START` in `run.env` exists only for the optional, clearly-labelled "elapsed (includes pauses)" line.

**Host portability.** `subagent_tokens` / `tool_uses` / `duration_ms` are Claude Code's Task-tool `<usage>` fields. On another host, record whatever usage metadata its delegation mechanism returns, and degrade **per column** when a field is absent — the ledger, the file-handoff protocol, and the idle-immune-timing *intent* are host-agnostic; only these field names are Claude Code's. **Time:** prefer a duration measured by the agent runner (idle-immune). If the host exposes none, an orchestrator-side bracket is allowed only when labelled "wall-clock (may include idle)"; with neither, write `n/a`. **Tokens and tool uses:** record when exposed, else `n/a`. Even on Claude Code, some agent types emit no `<usage>` block — the read-only `Explore` type behind inline-lookup Research is one — so an inline-lookup row reading `n/a` across tokens and `duration_ms` alongside fully-populated rows is expected, not a ledger bug. None of these figures gate control flow (retries are count-based, phases are criteria-gated), so a host exposing no usage metadata still runs the plan correctly — it just reports fewer columns.

## The between-phase progress table

After each phase, render progress as a GitHub-flavored markdown table (it displays cleanly in the user's terminal — prefer it over ASCII box-art) of **two rows**: the phase just completed and the phase now starting (the first tracker adds the `setup` row above them). Earlier rows are not re-rendered — the ledger holds them and `rp.sh totals` renders every one at Step 5; re-printing the whole history after each phase was 10–20K resident tokens on a 9-phase run. `rp.sh phase-cost <n>` prints the five cost cells for one row — for every phase, including one that spawned no agent (a human-gate-only or amended-out phase), whose cells it prints as dashes; the orchestrator supplies `#`, the short title, and the Status:

| # | Phase | Status | Research | Code | Review | Total | Active time |
| - | ----- | ------ | -------: | ---: | -----: | ----: | ----------: |
| 2 | {short title} | ✓ Complete (↻ retry 2/2) | — | 354K·113K·108K | 125K·119K·120K | 939.2K | 2:41:12 |
| 3 | {short title} | ▶ Current | — | — | — | — | — |

A `setup` row with a parallel batch renders as `| — | setup (research) | ✓ | 68K·59K·77K·75K | — | — | 280.0K | 0:08:25 (Σ 0:27:08, 1 parallel group) |`.

- **Phase** — the phase id plus a **short** title, truncated to ~25 chars with `…` when longer; the full title appears in the between-table note and the final Outcomes list, and an untruncated title is what pushes the table past a terminal's width.
- **Research / Code / Review** — each sub-agent's `subagent_tokens` as its **own figure**, dot-separated in spawn order when the phase had several (`354K·113K·108K` — the retry count is visible at a glance). A lone agent keeps one-decimal precision; multi-value cells drop to whole-K. NEVER sum agents into one figure: `354K + 113K + 108K` rendered as `575.1K` reads as one enormous agent, the opposite of what happened — the skill's whole architecture exists to keep each individual sub-agent lean, so the table must show each agent's own cost. Architect lands in the Research column (non-implementing, pre-code), Debug and retries in Code, each still listed individually. Upfront Step 3 research is its own `setup` row; mid-phase research lands in that phase's Research cell.
- **Total** — the phase's full token cost, every figure summed. This is the one place summing is correct — it reconciles the row without impersonating any single agent's size.
- **Active time** — the phase's summed `duration_ms` (idle-immune), `h:mm:ss`; rows sharing a Parallel group contribute the group's **max**, with the labelled Σ appended as the work figure.
- **Status** — `✓ Complete`, `▶ Current`, `· Pending`, or `▶ Reopened` (a committed phase re-executing an added or reopened criterion, from the reopen's start until its commit lands — fix-cycles.md); append a flag where relevant: `(no commit — no changes)`, `(GH sync degraded)`, `(⚠ needs-runtime)`, `(⚠ human gate — deferred)`, `(review skipped)`, and for any phase that drew on a fix-cycle budget, the used/available counts — `(↻ retry 1/2, corrective 2/2)`, `(↻ deletion 1/1)` — never a bare `(↻ retried)`: the tracker is the run's rendered budget state, and any mid-run claim about remaining budget derives from its flags plus the current phase's ledger Notes, never from memory.

Between the table and the next phase, briefly note: the key outcome of the completed phase (1–2 sentences); any context being carried forward and the `phase-<n>-handoff.md` path the next brief will reference; which agent mode the next phase will use and why (if not obvious).

**Host portability:** the token columns need host-exposed per-agent token counts; without them, drop Research/Code/Review/Total (likewise `Tool uses` in the final table, and Active time if no duration is exposed) — with no usage metadata at all, the table is just `# | Phase | Status`.

## The final completion table

At Step 5 the table switches shape: one row per **sub-agent**, grouped under its phase with a *subtotal* line per phase and a Totals row — the ledger already holds exactly these rows, and `rp.sh totals` renders them; the orchestrator never hand-renders the table or reads `ledger.md` for it. This is also where `tool_uses` is reported: per-agent `tool_uses` is the closest available proxy for how full each agent's context window got, and its spread — a 202-call Code agent against 38–44-call reviewers — is the run's context-pressure story.

```
bash <scratch_dir>/rp.sh totals 1='✓ Complete' 2='✓ Complete (↻ retry 1/2)' pre-PR='✓'
```

One `<phase>=<Status>` pair per phase, the tracker's Status cell with its flags; a phase without a pair gets a bare *subtotal*. Phases appear in ledger order (spawn order); **Agent** is the Mode plus the Note in parentheses (`Code (retry 1/2)`, `Research (api client)`); subtotal and Totals Active time follow the parallel-group rule (max, with the Σ as a labelled aside); `n/a` cells stay `n/a` and never enter a sum. The same output is re-pasted verbatim into the PR body's collapsed "Run cost" section.

| Phase | Agent | Tokens | Tool uses | Active time |
| ----- | ----- | -----: | --------: | ----------: |
| setup | Research (window modules) | 163.2K | 48 | 0:10:01 |
| setup | Research (consumer wiring) | 200.6K | 47 | 0:11:17 |
| setup | *subtotal* — ✓ | 363.8K | — | 0:11:17 (Σ 0:21:18, 1 parallel group) |
| 2 | Code | 353.9K | 202 | 1:12:03 |
| 2 | Code (retry 1/2) | 113.2K | 96 | 0:22:41 |
| 2 | Review | 124.6K | 44 | 0:16:52 |
| 2 | Review (re-review) | 119.3K | 38 | 0:14:20 |
| 2 | *subtotal* — ✓ Complete (↻ retry 1/2) | 711.0K | — | 2:05:56 |
| — | **Totals** — 6 sub-agents | **1074.8K** | — | **2:17:13 (Σ 2:27:14, 1 parallel group)** |

**Carried findings** (Step 4 item 10's report route) are the other Step 5 input the ledger's neighbour file holds: `rp.sh carry <phase> '<file:line — one line>'` appends to `<scratch_dir>/carried-findings.md`, and Step 5 reads that file once — for the final summary's caveats and the PR's Review notes; absent means nothing was carried — instead of the orchestrator carrying each finding in its own context across phases.
