---
name: tend-steering-docs
description: Condense or split a repo's agent steering docs (AGENTS.md, CLAUDE.md, docs/agents/*) without losing load-bearing rules; surfaces contradictions between rules and produces a human-reviewed Removal Ledger before any deletion. Use to clean up, tighten, split, or de-conflict bloated or stale agent docs.
---

# Tend Steering Docs

Maintain a repo's **agent steering docs** — `AGENTS.md`, any `CLAUDE.md`, the topic docs (`docs/agents/*`), and nested module/feature `AGENTS.md` — by either **condensing** them (cut bloat without losing load-bearing rules) or **restructuring** a bloated monolith into topic docs first. Scope is **steering docs only** — not developer docs, READMEs, ADRs, or `CONTEXT.md`.

This skill exists because an earlier cleanup **over-removed** valuable rules that had to be re-added by hand. The whole design is biased to *keep*: you compress wording freely, but losing *meaning* is a removal, and every removal is gated behind a ledger a human reviews line by line. **That human gate is the point of the skill, not an obstacle.**

## Read the full procedure before you touch anything

The authoritative, detailed procedure lives in the reference for your branch. **Before you classify, compress, move, or ledger a single rule, read the relevant reference IN FULL:**

- **Condense** an already-structured doc set → read [references/condense.md](references/condense.md).
- **Restructure** a monolith into topic docs first (its own PR) → read [references/restructure.md](references/restructure.md).

The summaries below are a **floor** so the safeguards are always in mind. They do **not** replace reading the reference — the reference is authoritative and richer.

## Step 0 — orient (both branches)

1. **Discover the actual doc layout.** Glob for `AGENTS.md`, `CLAUDE.md`, and any docs dir. Don't assume a shape: a frontend has `docs/agents/` + per-feature `AGENTS.md`; a backend is module-foldered; an infra repo is environment/module-foldered; some repos have a lone `CLAUDE.md`.
2. **Derive every rule from THIS repo.** Re-derive all stack/convention claims from this repo's own code and tooling config. Never import rules from a sibling repo, a "starter," or this skill's examples.

## Pick a branch

The deciding question is **topic count, not bloat** (full criterion in [references/restructure.md](references/restructure.md)): *imagine the keep-worthy rules after a mental cleanup — do they cluster into **3+** coherent topics, each with enough load-bearing content to stand alone as a doc?*

- **Yes, and they're still jammed into one monolith → restructure first** (`restructure.md`), as its own pure-move PR; condensing follows as the **next** PR.
- **No (1–2 thin topics survive) → condense** (`condense.md`) in place.
- **Post-split guard:** if coherent topic docs **already exist as separate files** (you just split, or the repo was already structured), you are in the *condense* state — do **NOT** re-split. Restructure runs **once per PR**, not once per repo.
- `--split` / `--condense` override this judgment. `--light` skips **only** the optional grilling step — never the gauntlet, ledger, or human gate.

## Always-loaded safeguards (the floor — the reference has the full version)

These apply on every run. They're summarized here so they're never out of context; the reference defines them fully and is authoritative.

**Prime directive.** Compress wording freely; compressing *meaning* is a removal. **Default to COMPRESS; when in doubt, KEEP.** The error costs are asymmetric — a wrongly-removed load-bearing rule fails silently across many future tasks and nobody notices until it ships; a wrongly-kept line costs a few tokens.

**Hard Stops — always PROTECT** (never cut; at most compress wording):
- **Exclusions** — anything forbidding a plausible alternative ("use X, **not** Z"). The exclusion is the payload even when "use X" looks obvious.
- **Provenance** — a "why," a past-incident reference, a tradeoff rationale, or a "do NOT 'fix' this" tone. Hard-won = keep.
- **Non-default choices** — anything narrowing or contradicting a framework/language/tool default.
- **Curated lists** — an allowlist/denylist/sanctioned-set is **one unit**; never nibble individual entries as "obvious." The completeness of the list is the rule.

**The Removal Gauntlet** — a rule reaches CUT only by clearing **all six** *and* hitting no Hard Stop:
1. **Discoverable (with evidence)** — enforced by *this repo's* tooling, or stated elsewhere in the docs. **Prove it by reading the actual config / grepping the other doc; never satisfy this by pointing at a *barer* duplicate.**
2. **Not a guardrail** — doesn't implicitly forbid an alternative.
3. **No provenance.**
4. **Obvious — and you can cite *where*** a competent engineer in this stack independently arrives at it (a framework default, documented behavior, an industry convention). **"I already know this" is an automatic FAIL.** A rule that narrows a default is by definition not obvious.
5. **No realistic task degrades** without it (against *this repo's actual* task inventory, not one you invent).
6. **Not the sole source** of a real constraint.

A rule that clears all six still goes to the **ledger for human review** — clearing the gauntlet earns a *proposal*, not a deletion.

**Lossy compression IS removal.** Rewording that drops a condition, exception, exclusion, version-rationale, or "why" goes in the Removal Ledger and through the gauntlet like any cut, with a side-by-side old→new diff at the gate. (This is the channel that most likely caused the original over-removal — meaning lost via rewording that no gate ever saw.)

**Verify; don't trust the doc.** Check every factual claim (paths, symbols, config values, versions, "the tooling enforces X") against live code by *running* the tooling. **A false claim is FIXED, not deleted** — distinguish *stale* (fix) from *redundant* (maybe cut) from *wrong-but-load-bearing* (fix **and** protect).

**Surface contradictions; don't silently pick a winner.** While auditing, scan *across* the docs for rules that genuinely conflict (root vs topic, topic vs topic, doc vs verified code). Quote both sides verbatim with `file:line` in a **Contradiction Register** and let the human choose precedence at the gate — never resolve it yourself, because a winner picked silently is indistinguishable from a load-bearing rule lost. An apparent conflict that is really a general rule plus its documented exception is **not** a contradiction — keep both. Resolution rides the existing gates: if it deletes a rule it goes through the ledger/gauntlet; if it rewords one it goes in the compression plan.

**The gated process:**
- **Phase A — AUDIT (no edits).** Classify every rule PROTECT/COMPRESS/CUT; verify claims; surface pre-existing contradictions; produce a divergence map, a compression plan (old→new for meaning-touching edits), a **Contradiction Register**, and the **Removal Ledger**. **Then STOP.**
- **Human gate.** The user does **line-item veto on the ledger** (default per row = REJECT; bulk "looks fine" approves nothing), **resolves each Contradiction Register entry** (picks precedence), and skims the compression diffs. Nothing is edited until this clears. **This human review is the entire over-removal safety mechanism — never skip, shortcut, or automate it.**
- **Phase B — APPLY** approved compressions + approved removals + claim-corrections only (skip vetoed rows; re-derive nothing from memory).
- **Phase C — ADVERSARIAL REVIEW** against live code (accuracy / lost-guidance / ambiguity), then the repo's check gate. **Steering docs drive behavior — stage changes in logical groups and leave them uncommitted for human retest** unless told otherwise.

**The Removal Ledger** (these are over-removal defenses, not mere formatting): one row per deletion *or lossy compression* (wording compression and dedup that keeps the richer copy are COMPRESS, **not** ledger rows); quote the **full verbatim original + `file:line`** (the reviewer must judge the rule, not your framing); order **most-risky-first** (so review fatigue lands on the safe rows); **a ledger past ~15 rows is a skepticism threshold, not a cap — re-verify none are a mislabeled COMPRESS/dedup, then present genuine removals in batches, most-risky-first.**

**Restructure branch is MOVE-ONLY** (full procedure in `restructure.md`): no cut/reword/dedupe; a compound/conditional rule (one with `unless / if / except / when`, a joining semicolon, or a main-plus-exception shape) moves as **one verbatim bullet** — never split an exclusion/condition/"why" from its rule; **STOP after the mapping table** for human review; prove completeness **by string** (coverage / conservation / live-set) against the untouched original — never "says the same thing."

## When to grill first (optional)

If the doc set is large (~5+ docs), you expect disagreement about what's load-bearing, or the repo has domain terminology worth sharpening, run a grilling skill first **if one is installed** (`grill-with-docs` when terminology/ADRs are in play, else `grill-me`), pointed at the Removal Ledger — make the agent *defend each proposed cut* against the gauntlet and Hard Stops. Skip for small/clear-cut sets; the Phase-A ledger + the human line-item review is enough.
