# Run ledger and progress reporting (SKILL.md Step 4 items 8–9, Step 5)

Read this when a usage figure needs interpreting — a host that exposes no `<usage>` block, an `n/a` row, a question about what the token figures mean — or when the progress table needs more than SKILL.md's compact rule says. `rp.sh ledger` and `rp.sh phase-cost` do the recording and the arithmetic; this file explains what the figures are.

## The ledger

`<scratch_dir>/ledger.md` is append-only and the single source of truth for per-sub-agent cost and time; the progress table and the completion summary render from it. Because it is a file, it survives context compaction: late-run reporting stays accurate after early phases are summarized out of context. `rp.sh init` creates it, so it exists before the run's first sub-agent spawn.

Every time ANY sub-agent returns — Research, Code, Architect, Debug, Review; every step including retries, the Debug → re-review cycle, the pre-PR branch review, and post-run follow-ups — append one row from its `<usage>` block:

```
bash <scratch_dir>/rp.sh ledger <phase> <mode> <subagent_tokens> <tool_uses> <duration_ms> [group] [note]
```

- **Phase** is the plan's phase id (`3`, `6A`), or `setup` for whole-run research, `pre-PR` for the branch review, `followup` for post-run fixes. Mid-phase research (fix-cycles.md item 4) takes its phase's id.
- **Mode** is one word: `Research`, `Code`, `Architect`, `Debug`, `Review`. Retries and re-reviews keep their mode; the Note carries the qualifier.
- **group** is blank for a solo spawn; rows spawned concurrently in one batch share a short label (`R1`, `R2`, …) and `phase-cost` counts the group's **max** duration, not its sum. Pass `""` to skip it when a note follows.
- **note** names what the row was: `all MET`, `retry 1/2`, `corrective 2/2`, `deletion 1/1`, `re-review`, `no budget` (a hook-failure Debug), a death (`died — no return`; the re-spawn's row carries the Note its dead predecessor would have — the cycle is charged once). The tracker flags and any mid-run budget claim derive from these Notes, never from memory.
- Record raw numbers; `phase-cost` formats. A field the host did not expose is `n/a` — never fabricated.
- Only sub-agent returns become rows. Orchestrator-side commands (a pre-commit hook, `rp.sh` calls, a human-gate check) are never ledger rows and never enter Active time; the earlier option of bracketing one heavy command with `date` was dropped with the script — do not re-add it as a `Code` row.

**`subagent_tokens` is cumulative tokens the agent processed across its internal turns — throughput, not peak context occupancy.** Report it as throughput; do NOT present it as "% of context window" (a long agent can process far more than the window without ever occupying it). Per-agent tokens are a **cost** signal; `tool_uses` is the closest available **occupancy** proxy — nothing evicts within a single sub-agent, so its context grows monotonically with tool-using turns, and a 250-call agent ran far closer to its window than a 30-call one whatever their token figures suggest. True peak occupancy is unmeasured on this host.

**This is a cost ledger, not a context-health ledger.** It records what each sub-agent spent; it says nothing about what stays resident in the orchestrator's own context — that occupancy is unmeasured (no mid-run signal exposes it) and is the cost Context Discipline exists to bound. Do not read a fully-populated ledger as evidence the run was context-lean.

All reported timing derives from summed `duration_ms` (parallel groups at their max) — never wall-clock `date` diffs across turns, which absorb laptop-closed / dropped-connection / checkpoint-pause idle and misreport. `RUN_START` in `run.env` exists only for the optional, clearly-labelled "elapsed (includes pauses)" line.

**Host portability.** `subagent_tokens` / `tool_uses` / `duration_ms` are Claude Code's Task-tool `<usage>` fields. On another host, record whatever usage metadata its delegation mechanism returns, and degrade **per column** when a field is absent — the ledger, the file-handoff protocol, and the idle-immune-timing *intent* are host-agnostic; only these field names are Claude Code's. **Time:** prefer a duration measured by the agent runner (idle-immune). If the host exposes none, an orchestrator-side bracket is allowed only when labelled "wall-clock (may include idle)"; with neither, write `n/a`. **Tokens and tool uses:** record when exposed, else `n/a`. Even on Claude Code, some agent types emit no `<usage>` block — the read-only `Explore` type behind inline-lookup Research is one — so an inline-lookup row reading `n/a` across tokens and `duration_ms` alongside fully-populated rows is expected, not a ledger bug. None of these figures gate control flow (retries are count-based, phases are criteria-gated), so a host exposing no usage metadata still runs the plan correctly — it just reports fewer columns.

## The between-phase progress table

After each phase, render progress as a GitHub-flavored markdown table (it displays cleanly in the user's terminal — prefer it over ASCII box-art). `rp.sh phase-cost <n>` prints the five cost cells for one row; the orchestrator supplies `#`, the short title, and the Status:

| # | Phase | Status | Research | Code | Review | Total | Active time |
| - | ----- | ------ | -------: | ---: | -----: | ----: | ----------: |
| — | setup (research) | ✓ | 68K·59K·77K·75K | — | — | 280.0K | 0:08:25 (Σ 0:27:08, 1 parallel group) |
| 1 | {short title} | ✓ Complete | — | 151.6K | 78.1K | 229.7K | 0:56:48 |
| 2 | {short title} | ✓ Complete (↻ retry 2/2) | — | 354K·113K·108K | 125K·119K·120K | 939.2K | 2:41:12 |
| 3 | {short title} | ▶ Current | — | — | — | — | — |

- **Phase** — the phase id plus a **short** title, truncated to ~25 chars with `…` when longer; the full title appears in the between-table note and the final Outcomes list, and an untruncated title is what pushes the table past a terminal's width.
- **Research / Code / Review** — each sub-agent's `subagent_tokens` as its **own figure**, dot-separated in spawn order when the phase had several (`354K·113K·108K` — the retry count is visible at a glance). A lone agent keeps one-decimal precision; multi-value cells drop to whole-K. NEVER sum agents into one figure: `354K + 113K + 108K` rendered as `575.1K` reads as one enormous agent, the opposite of what happened — the skill's whole architecture exists to keep each individual sub-agent lean, so the table must show each agent's own cost. Architect lands in the Research column (non-implementing, pre-code), Debug and retries in Code, each still listed individually. Upfront Step 3 research is its own `setup` row; mid-phase research lands in that phase's Research cell.
- **Total** — the phase's full token cost, every figure summed. This is the one place summing is correct — it reconciles the row without impersonating any single agent's size.
- **Active time** — the phase's summed `duration_ms` (idle-immune), `h:mm:ss`; rows sharing a Parallel group contribute the group's **max**, with the labelled Σ appended as the work figure.
- **Status** — `✓ Complete`, `▶ Current`, `· Pending`; append a flag where relevant: `(no commit — no changes)`, `(GH sync degraded)`, `(⚠ needs-runtime)`, `(⚠ human gate — deferred)`, `(review skipped)`, and for any phase that drew on a fix-cycle budget, the used/available counts — `(↻ retry 1/2, corrective 2/2)`, `(↻ deletion 1/1)` — never a bare `(↻ retried)`: the tracker is the run's rendered budget state, and any mid-run claim about remaining budget derives from its flags plus the current phase's ledger Notes, never from memory.

Between the table and the next phase, briefly note: the key outcome of the completed phase (1–2 sentences); any context being carried forward and the `phase-<n>-handoff.md` path the next brief will reference; which agent mode the next phase will use and why (if not obvious).

**Host portability:** the token columns need host-exposed per-agent token counts; without them, drop Research/Code/Review/Total (likewise `Tool uses` in the final table, and Active time if no duration is exposed) — with no usage metadata at all, the table is just `# | Phase | Status`.

## The final completion table

At Step 5 the table switches shape: one row per **sub-agent**, grouped under its phase with per-phase *subtotal* lines and a Totals row — the ledger already holds exactly these rows, so render them; this is also where `tool_uses` is reported. Format and example live in completion-templates.md.
