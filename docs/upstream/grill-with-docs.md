# grill-with-docs

**Upstream path(s):** `skills/engineering/grill-with-docs` (a one-line dispatcher since 2026-05-31), `skills/productivity/grilling` (interview engine), `skills/engineering/domain-modeling` (glossary/ADR engine, extracted 2026-05-31 from what used to be grill-with-docs's `<supporting-info>` block)
**Last reviewed upstream commit:** [`6654f6b`](https://github.com/mattpocock/skills/commit/6654f6b60cd9d5be8b54c6fafe44346dabeb3b76) (2026-08-24)
**Forked from:** approximately [`b843cb5`](https://github.com/mattpocock/skills/commit/b843cb5) (2026-04-30, the `<what-to-do>`/`<supporting-info>` structure) — registered here 2026-05-01 (`dcaa47d`); the glossary-only tightening from upstream `e74f006` was pulled 2026-05-25 (`4e76bc6`). Reconstructed from git history; no pin was recorded at the time.

## Current divergence

Upstream `grill-with-docs` is now `Call the Skill tool twice, for "grilling" and "domain-modeling"`. Ours inlines both: the `<what-to-do>` block is byte-identical to our `grill-me` body (every `grill-me` divergence applies — see [grill-me.md](grill-me.md)), and `<supporting-info>` is our copy of what is now upstream `domain-modeling`.

### Interview engine

Identical to [grill-me.md](grill-me.md) — do not maintain a second list here.

### Domain-modeling block vs upstream `domain-modeling/SKILL.md`

- **Body:** same sections in the same order (file structure, glossary challenge, sharpen fuzzy language, concrete scenarios, cross-reference with code, inline CONTEXT.md updates, three-criterion ADR gate). Upstream differences are punctuation (em-dashes → colons) and a new framing paragraph ("this is the *active* discipline… merely reading CONTEXT.md is not this skill"). Upstream's description now triggers on "discussing codebase terminology, writing or editing a CONTEXT.md, or recording or editing an ADR" so it can run standalone.
- **`references/CONTEXT-FORMAT.md`:** identical in rules since 2026-08-24 (the `e7df78b` trim was adopted); ours keeps em-dashes.
- **`references/ADR-FORMAT.md`:** identical modulo punctuation.

## Sync ledger

### 2026-08-24 — reviewed `b843cb5..6654f6b`

- **adopted:** everything listed under grill-me's 2026-08-24 entry, via the shared `<what-to-do>` body.
- **adopted:** the CONTEXT-FORMAT.md trim (`e7df78b`) — dropped relationships, example dialogue, and flagged-ambiguities. A glossary that also models relationships stops being "a glossary and nothing else", which is the rule the same file states.
- **benchmark** (fixtures 03/04 of `evals/suites/grilling`, 3 reps): the glossary discipline itself does not separate the lineages — glossary conflict challenged and "account" sharpened 3/3 in every arm; CONTEXT.md kept free of implementation detail 12/12 across arms. Two things are worth watching:
  - **ADR gate is leaky everywhere.** Fixture 04 plants only reversible decisions; every arm still wrote 2–5 ADRs in every run (0/12 clean). Upstream's `domain-modeling` text is the same as our block, so this is not a sync question — it is the three-criterion gate not holding on Opus 5. Candidate fix for a later change: require the interviewer to name which of the three criteria a decision meets before offering.
  - **v2 flipped two CONTEXT.md cells 3/3→2/3** (one run rewrote an existing glossary down to two terms after deciding the repo "doesn't own Orders"; one run never created CONTEXT.md despite resolving Invoice/Statement). Single-rep flips, noise-level by this repo's rule, but both are the kind of miss frontier rounds could plausibly cause (a round settles several terms at once and the inline-update habit slips). Re-check on the next run; if it replicates, add "update CONTEXT.md before asking the next round" to the `<supporting-info>` block.
- **deferred:** extracting the `<supporting-info>` block into a standalone `domain-modeling` skill. It would let the glossary discipline run outside a grilling session and make this file a pure dispatcher; it also adds an install dependency. Revisit together with the dispatcher question in grill-me.md.
- **rejected:** dispatcher composition, `agents/openai.yaml`, em-dash removal — same reasons as grill-me.
