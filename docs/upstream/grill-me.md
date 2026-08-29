# grill-me

**Upstream path(s):** `skills/productivity/grill-me` (a one-line dispatcher since 2026-05-31), `skills/productivity/grilling` (the interview engine; this is where the content lives)
**Last reviewed upstream commit:** [`6654f6b`](https://github.com/mattpocock/skills/commit/6654f6b60cd9d5be8b54c6fafe44346dabeb3b76) (2026-08-24)
**Forked from:** [`651eab0`](https://github.com/mattpocock/skills/commit/651eab033bdf8f7fd535c274f8cbe839075aba5e) (2026-04-15), when the skill was four sentences at `grill-me/SKILL.md`.

## Current divergence

Upstream `grill-me` is now `Call the Skill tool with "grilling"` plus `disable-model-invocation: true`. Ours is self-contained; the body below is compared against upstream `grilling`.

### Adopted from upstream on 2026-08-24 (now in both)

Frontier rounds and the `❓ **Qn** / ➡️` round format; facts-are-yours/decisions-are-mine framing with non-blocking sub-agent lookups; the confirmation gate before acting. Our body wraps these in our own section structure, so the text is not byte-identical to `grilling/SKILL.md` — diff against that file, not `grill-me/SKILL.md`, on the next sync.

### Ours, not upstream

- **Counter-challenge step** — when the user answers directly (not from an offered menu), push back once with a concrete counter before accepting. Upstream has no pushback mechanism at all: its `grilling` is a thorough interview, not a grilling.
- **Honesty rule** — unconfirmed defaults go under assumptions/open questions, never decisions; >~3 assumptions means questions were missed.
- **Structured wrap-up** — decisions / assumptions / open questions. Upstream ends on "frontier empty" with no wrap-up shape.
- **NEVER accept "I'll figure that out later"** — decision or explicit open question.

### Upstream, not ours

- **Dispatcher + engine composition** — `grill-me` and `grill-with-docs` are thin dispatchers over shared engines. Note `disable-model-invocation` is a Claude-Code-only key that `evals/lint.py` rejects (`AGENT_SPECIFIC_KEYS`), and "Call the Skill tool" is Claude Code vocabulary; adopting the composition would need harness-neutral phrasing.

### Same intent, different words

- Our "NEVER stop at surface-level branches" ≈ upstream's "settled decisions push the frontier outward". We keep both sentences.
- Our "NEVER ask me for a fact you could look up" restates upstream's facts/decisions paragraph as a hard rule.

## Sync ledger

### 2026-08-24 — reviewed `651eab0..6654f6b`

Prompted by the question of whether to drop the fork and use upstream directly. Answer: no — the properties we forked for (honesty rule, structured wrap-up, deferral ban) are still absent upstream and measurably matter (below). Sync instead.

- **adopted:** frontier rounds with the pinned question format; non-blocking sub-agent fact-finding; facts-vs-decisions framing; confirmation gate. Counter-probes are frontier items — a probe is a node unlocked by an answer and lands in the next round.
- **adopted** (consequence): retired the one-question-per-turn rule and its NEVER line in favour of "a question whose answer depends on another question still open in this round belongs to a later round". Supersedes the `fc60d33` history in [UPSTREAM.md](../UPSTREAM.md): that removed an *elastic* bundling allowance; the frontier rule is strict with a structural trigger, which is what the linter was built to prefer.

**Benchmark** (`evals/suites/grilling`, 4 dialogue fixtures × 3 reps, Opus 5, recorded in `evals/baselines/grilling.json`; v1-only pass in `grilling-v1-vs-upstream.json`):

| arm | assertions | cost | wall | interviewer turns/run |
|---|---|---|---|---|
| upstream `grilling` @ `6654f6b` | 114/154 (2 runs timed out) | $18 | 61 min | 6–8 |
| ours v1 (`main` @ `821fab1`, one question per turn) | 152/175 (3 runs hit the 28-turn cap) | $34 | 119 min | 19–29 |
| ours v2 (this sync) | 155/177 | $28 | 93 min | 5–10 |

What the numbers say, at n=3 (a 1/3 flip is noise; 3/3→0/3 is not):

- **Frontier rounds are a strict improvement on v1 here.** v2 met or beat v1 in every category (planted decisions asked 37/39 vs 36/39; deferrals pressed 12/12 vs 10/12; flawed answers challenged 12/12 vs 10/12), closed all 12 interviews (v1 capped out in 3/12 — one-at-a-time genuinely does not finish a mid-sized plan in 28 turns), and cost 18% less.
- **The structured wrap-up is the fork's load-bearing property.** Wrap-up with a decisions section: upstream 4/10, v1 10/12, v2 12/12. Assumptions/open questions distinguished: upstream 1/10, v1 9/12, v2 12/12. Corrected decision survives into the wrap-up: upstream 6/10, ours 22/22.
- **The challenge clause is not earning measurable keep on this model.** Upstream pushed back on the planted flawed answer in 10/10 graded runs with no such rule; v2 12/12, v1 10/12. Kept for now — the fixtures' flaws are all discoverable from the repo, which is the easy case; a flaw that needs reasoning rather than a file read is the test that would separate them.
- **Nobody dispatched a sub-agent** (0 across 36 runs): every arm read the repo directly from the main context. The "dispatch a sub-agent" wording is inert in `claude -p` on Opus 5. Kept as written since it is harmless and may matter on a weaker model; not a reason to prefer either lineage.
- **Two persona-side false positives** inflated "asked the user for a repo fact" failures in fixtures 03/04 for all arms and were fixed after the run (`order_lifecycle`, `entry_shape` were never actually in the repo). Those cells are not evidence about either lineage.
- **Not adopted:** anything from upstream's ADR/glossary behaviour — it is the same text as ours and over-writes ADRs in fixture 04 identically (0/12 clean across all arms). That is a `domain-modeling` finding, tracked in [grill-with-docs.md](grill-with-docs.md).
- **adopted (2026-08-25):** the one-line "read `CONTEXT.md` for vocabulary, respect ADRs" habit upstream added to `tdd`/`triage`/`diagnosing-bugs` (not to `grilling`). Lives in the facts section of the shared body; `grill-with-docs` layers its active glossary discipline on top.
- **rejected:** dispatcher + engine split (`Call the Skill tool with "grilling"`, `disable-model-invocation: true`). Claude-Code-specific phrasing and frontmatter; our skills are independently installable and the linter forbids the key. Would revisit if we adopt a cross-harness skill-invocation convention.
- **rejected:** `agents/openai.yaml` Codex metadata. Harmless but nothing in this repo consumes it; revisit when a Codex consumer exists.
- **rejected:** em-dash removal (`86cba45`, `3216582`). Cosmetic.
- **adopted-adjacent (ours, 2026-08-29):** an agent-initiated trigger in the description — "about to ask the user three or more design questions, or any question whose answer would change what you ask next" — after field reports of coding agents falling back to built-in ad-hoc Q&A mid-ticket instead of invoking the skill. Threshold is deliberately mechanical (count or dependency) to avoid an elastic trigger. Upstream has no equivalent (its dispatchers are `disable-model-invocation`). Consuming repos pair this with an AGENTS.md non-negotiable scoped to interactive sessions only, so autonomous agents (e.g. run-plan phases) never start a grilling session.
- **dropped (ours, 2026-08-25):** the `--light` flag (skipped the counter-challenge step). Never used in practice, and the benchmark showed the clause it disabled is not doing measurable work on Opus 5; one less thing to carry across syncs.
