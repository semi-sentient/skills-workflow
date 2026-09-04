# Human-gate criteria (SKILL.md Step 4)

Read this when `plan-index.md` shows a `Human-form criteria:` or `Human-gate literal:` line for any phase, or when a reviewer returns `HUMAN-GATE`. A plan with neither never needs it.

## Identification is mechanical, once, at Step 2

The human-form criteria of a phase are every acceptance criterion whose text begins with the word `Human` followed by a space (`Human verifies …`, `Human applied …`, `Human confirms …` — case-insensitive, after the checkbox and any leading emphasis or backtick). `rp.sh extract` applies this rule and lists the labels on the phase's `Human-form criteria:` line in `plan-index.md`.

A phase whose text — heading, prose, or criteria — contains the literal `Known risk`, `human gate`, or `not agent-completable` (all case-insensitive), and not the literal `(human-form set confirmed)`, has an **unresolved set** however many `Human …` criteria it already carries (in production, one labelled criterion sat beside three unlabelled human-only ones). The index marks it `Human-gate literal: UNRESOLVED`. Name it at Step 2 (item 4) and ask in Step 3's batched drift message which of its non-`Human` criteria are human-form — the classification is the user's, never inferred from intent — then make the answer durable in the plan file with the other amendments: amend the named criteria to the `Human verifies …` form, and in every case append ` (human-form set confirmed)` to the line that carries the literal; then `rp.sh extract`. Either way the mechanical rule alone settles the phase for the rest of the run and any resume; a classification held only in conversation is lost at compaction.

## The gate is on criteria, never on the phase

A phase still runs the normal loop for every criterion an agent can own — Code agent, review gate, commit — with BOTH the Code brief and the Review brief naming the human-form criteria as outside their mandate (their `HUMAN_FORM` slot lists the labels; the reviewer returns `HUMAN-GATE` for each in place of a verdict; Step 4 item 5 routes that as no action; the Code agent never satisfies one by proxy or contorts it into a mechanical pass). A phase whose criteria are all human-form spawns no Code agent and no reviewer.

Then, once the agent-owned work is committed (or there is none): end the turn with a checklist — every human-form criterion verbatim (from `rp.sh criteria <n>`) and what the human must observe for each — as a sanctioned stop (Step 4 item 11). At the gate the orchestrator runs commands only at the human's explicit direction — read-only checks the human delegates back (`terraform plan`, an `aws … get-*` read) are the normal shape — report the check's result back to the human and tick only on their confirmation: delegation makes the orchestrator the human's eyes, never the author of their report; a mutating operation the human directs is theirs to authorize and is recorded in the progress note. Human-form criteria are ticked only from the human's report — never from the orchestrator's own evidence, never from a reviewer's verdict; a reviewer marking one NEEDS-RUNTIME does not make it item 6's checked-but-tagged case.

## The human's reply

The reply takes one of three shapes, and **results** may arrive incrementally across several exchanges (tick each criterion per item 6 as the human confirms it; the gate stays open); a reply that is none of the three is re-asked once, then treated as `defer`:

- **results** — tick what the human reports passed per item 6 and commit that plan-file edit as a checkbox-only commit via item 7 (`(no commit — no changes)` where the plans directory is git-ignored), and treat a reported failure as a blocking failure in the phase's committed code: spawn a Debug agent with the human's observation (fix-cycles.md item 3 — a human's report at a gate is an admitted failure source), run the review gate, commit, counting against this phase's retry limit, then re-present the checklist for every criterion still unticked — the gate repeats until the human reports all passed, says `defer`, or the retry limit is exhausted (escalate per fix-cycles.md).
- **`defer`** — leave the criteria unticked, flag the phase `(⚠ human gate — deferred)` in the tracker, and carry every deferred criterion to Step 5's caveats and the PR Test plan (completion-templates.md's population rule, source c) — `<outcome>` is then `partial` by definition and Step 5's partial templates apply, but a resume re-presents the checklist for the deferred criteria rather than re-attempting the phase (branch-and-resume.md → Resumability).
- **`stop`** — end the run at this phase as `aborted` (a user abort, per `<outcome>`'s definition).

The gate stops the run at the phase's position in the plan, wherever that is; never reorder it to the end or fold it into Step 5.

## An unplaced `HUMAN-GATE` return

A `HUMAN-GATE` on a criterion the brief did NOT place is a question for the user (a sanctioned stop, Step 4 item 11): "human-form" amends the criterion to the `Human …` form (re-extract, sync per item 6); "agent-verifiable" re-spawns the reviewer once, no budget, with the criterion named as agent-verifiable in its brief's `HUMAN_FORM` slot — a second `HUMAN-GATE` on it escalates to the user with both returns. Resolve an unplaced `HUMAN-GATE` before any other routing of that review.
