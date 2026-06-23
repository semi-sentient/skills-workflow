# Condense — Cautious Compression (authoritative reference)

> **This is the condense branch of the `tend-steering-docs` skill.** The router (`SKILL.md`) sends you here; **read it in full before you classify, compress, or ledger a single rule.** It condenses a repo's **agent-steering docs** — `AGENTS.md`, any `CLAUDE.md`, the topic docs wherever the repo keeps them (e.g. `docs/agents/`), and any nested module-/feature-level `AGENTS.md` *if present* — **without losing load-bearing rules.**
>
> **Why it's this cautious:** an earlier compression pass **over-removed** — valuable rules were deleted and had to be re-added by hand. This procedure makes prose-compression the main lever, treats *lossy* compression as a removal, and gates every removal behind a reviewed ledger.

---

## Prime directive

**Compress wording freely. Compressing _meaning_ is a removal — and removals are rare, gated, and default to "no."**

The error costs are wildly asymmetric: a wrongly-**removed** load-bearing rule causes silent, recurring bad output across many future tasks and nobody notices until it ships; a wrongly-**kept** redundant line costs a handful of tokens. **So when in doubt, KEEP.** Every judgment call defaults to retention.

Most of the win is in *wording*, not deletion — you can often cut a large fraction of lines (tables → bullets, six examples → one, drop filler) while removing zero rules. The percentage is an *observation, never a target*: a correct run may compress 30% or 0%. "I left this doc nearly as-is because it was already lean" is a fully successful outcome — report it as success.

---

## Step 0 — orient before touching anything

1. **Discover the actual doc layout.** Glob for `AGENTS.md`, `CLAUDE.md`, and any docs dir. Don't assume a frontend's `docs/agents/` + per-feature `AGENTS.md` shape; a backend is module-foldered, an infra repo is environment-/module-foldered, and either may have zero nested docs.
2. **Derive every rule from THIS repo.** Re-derive all stack/convention claims from this repo's own code and tooling config. Never import rules from a sibling repo, a "starter," or this skill's examples.

---

## Hard stops — these are always PROTECT

A rule of any of these kinds is **PROTECT regardless of how many gauntlet checks it appears to pass.** The gauntlet below cannot promote them to CUT:

- **Exclusions** — anything that forbids a plausible alternative ("use X, not Z"). The *exclusion* is the non-obvious payload, even when the "use X" half looks obvious.
- **Provenance** — anything carrying a "why," a past-incident reference, a tradeoff rationale, or a "do NOT 'fix' this" tone. Hard-won = keep.
- **Non-default choices** — anything that narrows or contradicts a framework/language/tool default (overriding a default is the usual reason a rule was written down).
- **Curated lists** — an allowlist/denylist/sanctioned-set is **one PROTECT unit**; never nibble individual entries as "obvious." The *completeness of the list* is the rule.

---

## Commonly keep-worthy categories (re-derive specifics per stack)

These categories are almost always non-obvious AND non-discoverable — recognize them as PROTECT (at most COMPRESS), don't cut them as "generic," and re-derive the concrete rule from *this* repo's stack:

- **Vendored / generated code is third-party.** Codegen output (API clients, OpenAPI/GraphQL/proto stubs, generated sources, CLI-scaffolded components) is exempt from the repo's naming/ordering/doc/style conventions — extend via the central system or by wrapping, regenerate via the tool, don't hand-edit. State it explicitly so it isn't read as debt.
- **Central design-system + the linter's blind spots.** "Style only from the system, never raw values" — *plus* what the linter does NOT catch, so the agent self-enforces the gap.
- **The one sanctioned escape hatch.** When the default can't express something, name the single allowed escape and bound it (which form is allowed, which is banned) so it can't rot.
- **Co-location for delete-together.** Tests (and co-located assets) next to their source, to prevent orphans.
- **The wire / serialization boundary.** HTTP payloads and persisted shapes the client sees, documented per-field (units, ranges, edge-cases) — non-discoverable and survives stack changes (especially a backend↔frontend contract).

---

## Commonly discoverable — cut candidates (must still clear the gauntlet)

The mirror image of the keep-worthy list: content that is almost always *noise* because a competent agent finds it in the first minutes of reading the repo. The fast test — *"could the agent find this by scanning the codebase?"* — usually answers **yes** for these. Treat them as CUT candidates, **but they still run the full gauntlet and the Hard Stops still override** — any one can secretly encode a non-obvious rule:

- **Directory / structure tours** ("packages live in `/packages`", "components go in `src/components`") — a directory listing finds it. *Keep only* if it encodes a non-obvious boundary (e.g. "never import across these two packages").
- **Tech-stack / dependency recitations** that just restate the manifest (`package.json`, `build.gradle.kts`, `*.tf`). *Keep only* the non-default choice ("use `uv`, not `pip`") or a version-is-the-rule pin — those are Hard Stops, not recitations.
- **Module / architecture overviews and codebase tours** the agent reads directly from the code.
- **Generic style rules the formatter/linter already enforces** — prove it's enforced (read the config), then cut. If the linter does *not* catch it, it's a keep-worthy blind-spot, not noise.

**Anchoring caution (legacy / deprecated tech).** Don't merely *mention* obsolete tech — "we used to use tRPC", "the old Redux store" — even as history: it biases agents toward dead patterns (an anchoring effect), so the bare reminiscence is a CUT. **Keep only the operational-landmine form:** "`legacy/` is deprecated but still imported by 3 production modules — don't break it." The landmine is provenance (Hard Stop → keep); the reminiscence is noise (cut).

---

## Classify every rule into three buckets

| Bucket | Meaning | Action |
|---|---|---|
| **PROTECT** | Hits any Hard Stop above, or is non-obvious/repo-specific, or is the only place a constraint is stated | Leave verbatim. |
| **COMPRESS** | A real rule stated verbosely | Keep the rule; shorten the words. Most rules land here. |
| **CUT** | Eligible for deletion *only* after clearing the Removal Gauntlet | Log in the ledger; delete only after human approval. |

**Default is COMPRESS.** Unsure CUT vs COMPRESS → COMPRESS. Unsure COMPRESS vs PROTECT → PROTECT.

---

## The Removal Gauntlet

A rule reaches **CUT** only if it passes **ALL SIX** *and* hits no Hard Stop. Fail any one → COMPRESS or PROTECT.

1. **Discoverable (with evidence)** — enforced automatically at write-time by *this repo's* tooling (formatter / linter / type-or-compile check / test / policy-check) **or** stated elsewhere in the steering docs. Prove it: read the actual config, or grep the other doc. If "stated elsewhere," the other copy must (a) be bucketed PROTECT/COMPRESS (never CUT, so it can't vanish in the same pass) and (b) retain all conditions/exceptions/"why" of both copies — never satisfy this check by pointing at a *barer* duplicate.
2. **Not a guardrail** — does not implicitly forbid an alternative. (If it does, it's a Hard-Stop exclusion → PROTECT.)
3. **No provenance** — no "why," incident, or override rationale. (If it has one → Hard Stop → PROTECT.)
4. **Obvious — and you can cite *why*** — to pass, name *where* a competent engineer in this stack would independently arrive at the rule (a framework default, documented language behavior, an industry-standard convention). "It sounds generic" / "I already know this" is an automatic **FAIL** — obviousness is not self-certified. A rule that narrows/contradicts a default is by definition NOT obvious.
5. **No realistic task degrades** — using *this repo's actual* agent task inventory (from `AGENTS.md` / the repo's stated use-cases, not a list you invent), confirm no task produces worse output without this line. If you can't point to a canonical task list, this check FAILS.
6. **Not the sole source** — not the only place a real constraint is recorded.

A rule that clears all six still goes to the **ledger for human review** — clearing the gauntlet earns a *proposal*, not a deletion.

---

## Lossy compression IS removal

Rewording that drops a condition, exception, exclusion, version-rationale, or "why" clause is **not a compression — it is a removal.** It must go in the Removal Ledger and through the gauntlet like any CUT, and the human gate must see a side-by-side old→new diff of it. (This is the channel that most likely caused the original over-removal: rules lost not via honest CUTs but via lossy rewording that no gate ever saw.)

---

## Safe compression moves (remove words, not meaning)

- **Drop filler preambles** ("Quick reference for…"). Replace only with a one-liner that does real work (e.g. "Project-specific rules; generic X assumed" — which *licenses* cutting generic content).
- **Tables → bullets/prose** when low-density.
- **One canonical example per concept**, not several.
- **Cut generic pep-talk** ("we value quality") and checklists that merely restate rules already stated. **Never** cut rule-specific rationale — a "why" tied to an incident, tradeoff, or overridden default is *provenance* (Hard Stop), not "motivational filler." Unsure if prose is filler or provenance → it's provenance → keep.
- **Collapse multi-level sub-headers** into one tight section.
- **Merge duplicated statements** into one — preserving the *richer* copy (the one with conditions/exceptions/"why"), never the barer twin.
- **Defer skill-owned methodology to a skill** — *only* when the text is a verbatim restatement of generic skill methodology with **no repo-specific addition, exception, or override**, and only when this repo actually ships that skill. If the text adds anything this repo does differently from the skill's default, KEEP it — that delta is the entire reason it exists. A deferral that drops a repo-specific delta is a removal (ledger + gauntlet). Replace with a strong "load the `<skill>` skill first" directive that names what the skill owns.

> A compression must preserve meaning exactly. If shortening loses a condition, exception, exclusion, or "why," you've crossed into removal — restore it or ledger it.

---

## Formatting & durability (compress in a way that ages well)

- **One rule = one bullet, under a clear header.** A rule you can't point at is a rule you can't audit.
- **Reference grep-able symbols, not fragile file paths** — a symbol/identifier name survives a file move; a full path doesn't.
- **No rotting version pins** — describe the behavior/convention, not an exact version, *unless the version is the rule* (e.g. "vN changed X"; and in IaC, provider/module/`required_version` pins are frequently load-bearing for reproducibility/state-compat — keep those).
- **No wide tables or run-on paragraphs; don't hard-wrap prose** — let it soft-wrap; keep rules atomic.
- **Keep the root `AGENTS.md` lean** — it loads every session; hold pointers + non-negotiables there and push detail into topic docs.

---

## Verification mandate (check; don't trust the doc)

- **Verify every factual claim against live code** — paths, symbols, config values, versions, and especially "the tooling enforces X." *Run the tooling*: resolve the linter/policy config, check the dependency manifest (`package.json` / `build.gradle.kts` / `libs.versions.toml` / `.terraform.lock.hcl` / whatever this repo uses), grep for the path/symbol. Reasoning-from-memory is how docs drift *and* how a pass introduces new false claims.
- **A false claim is FIXED, not deleted** — correct the detail; don't drop a rule because its supporting fact rotted. Distinguish: *stale* (fix) vs *redundant* (maybe cut) vs *wrong-but-load-bearing* (fix **and** protect).
- **Flag band-aid rules — fix the code, don't just cut the doc.** If a rule exists only to compensate for a *fixable* root cause (a confusingly-named symbol, a missing lint rule, a flaky build step the rule warns around), record it in the divergence map *with the root-cause fix* and surface it for the human — don't silently cut it. Cutting without fixing just reintroduces the friction; the durable fix lives in the code/tooling, after which the rule can retire.

---

## Surface pre-existing contradictions (don't silently resolve them)

Bloated doc sets accumulate **rules that contradict each other** — two docs giving incompatible style/workflow guidance, a topic doc overriding the root without saying so, a stale rule fighting a current one. Find these *before* you compress: compressing one side of a hidden conflict silently decides the conflict, and that decision never reaches a gate.

- **Scan across all docs** as part of the audit — root vs topic, topic vs topic, and doc vs the code reality you verified. This is a *proactive* pass, distinct from the Phase C check that catches conflicts your *edits* introduce.
- **Distinguish a true contradiction from a rule-plus-exception.** "Use X" in one place and "use Y when Z" in another is usually a general rule and its documented exception — they coexist; **keep both**. A contradiction is *mutually exclusive* guidance with no reconciling condition. Unsure → treat as coexisting (keep both) and raise it as a question, not a conflict.
- **Never resolve a contradiction yourself.** Record each in a **Contradiction Register** — both sides quoted **verbatim + `file:line`** — and let the human pick precedence at the gate. A winner picked silently is indistinguishable from a load-bearing rule lost.
- **Resolution flows through the existing gates, never around them.** If the chosen precedence *deletes* the losing rule, that deletion still goes through the Removal Ledger + gauntlet + Hard Stops. If it *rewords* a rule to defer to the other, that is a meaning-touching edit → compression plan with old→new. Resolving a contradiction is never a license to cut ungated.
- A contradiction best fixed by **changing the code/tooling** so the conflict disappears is a band-aid signal — surface the root-cause fix (see the verification mandate) rather than just editing the doc.

---

## Process — gated and non-destructive first

**Phase A — AUDIT (no edits).** Classify every rule (PROTECT / COMPRESS / CUT); verify all claims against the code. Produce four artifacts: a **divergence map** (claims vs reality), a **compression plan** (every COMPRESS edit, with old→new for any that touch meaning), a **Contradiction Register** (every genuine rule-vs-rule conflict, both sides quoted verbatim + `file:line`), and the **Removal Ledger** (every proposed deletion *and* every lossy compression). **Then STOP.**

**Human-review gate.** The user does **line-item veto on the Removal Ledger** (default per row = REJECT; a row is cut only on explicit approval; bulk "looks fine" approves nothing), **resolves each Contradiction Register entry** by picking precedence (a resolution that deletes a rule still rides the Removal Ledger; one that rewords a rule still appears in the compression plan), and **skims the compression plan's old→new diffs**. Nothing is edited until this gate clears. *This gate is the entire over-removal safety mechanism — and it must cover lossy compressions, not just deletions.*

**Phase B — APPLY.** Apply: approved compressions, approved removals (skip vetoed rows), and the claim-corrections from the divergence map. Re-derive nothing from memory.

**Phase C — ADVERSARIAL REVIEW.** Three independent checks against the live code:
1. **Accuracy** — every remaining claim true?
2. **Lost-guidance** — diff old → new; for each deletion **and each lossy compression**, did it truly pass the gauntlet? Flag regressions to restore.
3. **Ambiguity/contradiction** — did compression muddy a rule, or *introduce* a new contradiction with `AGENTS.md` / another doc? (Pre-existing contradictions were surfaced in Phase A and resolved at the gate; this check is for conflicts the edits themselves created.)

Fix what they find, then run the repo's check gate (validate / fmt-check / lint / test / plan — whatever applies; an infra repo may have no unit tests). **Steering docs drive behavior, so stage changes in logical groups and leave them uncommitted for human retest** unless told otherwise.

---

## Removal Ledger format

One row per proposed deletion *or lossy compression* — **not** for meaning-preserving edits (wording compression and dedup that keeps the richer copy are COMPRESS, so a big shrink does **not** imply a big ledger; the restructure/split adds none). Nothing changes that isn't here and approved. Order **most-risky-first** (so review fatigue lands on the safe rows). **A ledger past ~15 rows is a skepticism threshold, not a cap:** first confirm none are a COMPRESS/dedup mislabeled as CUT and that each survivor truly clears all six gauntlet checks; if that many distinct rules are genuinely removable, present them anyway — **in batches, most-risky-first**. **Never relabel a real CUT as COMPRESS to get under the number** — that hides a removal from the gate.

| Full original text (verbatim) + `file:line` | CUT or lossy-COMPRESS | Weakest gauntlet check + why it barely passed | How verified discoverable/redundant | Risk if this was wrong |
|---|---|---|---|---|

Quote the **full original rule**, not a paraphrase — the reviewer must judge the rule, not your framing. Keep the completed ledger as a record of what changed and why (and any false claims fixed).

---

## How the skill runs this

The skill's router (`SKILL.md`) has already oriented (Step 0) and chosen the condense branch. Execute **Phase A only** first, then STOP:

1. Map docs → reality: read every steering doc, explore the code + tooling config, list every divergence. Verify by *running* the tooling — don't assume. While reading, also list every genuine rule-vs-rule contradiction (root vs topic, topic vs topic) for the Contradiction Register — distinguishing a true conflict from a rule-plus-exception.
2. Classify every rule PROTECT / COMPRESS / CUT. **Default to COMPRESS; bias to keep.** Honor the Hard Stops. A rule reaches CUT only by clearing all six gauntlet checks; lossy rewording counts as a removal too.
3. (Only if large — more than ~5 docs or ~600 lines total) fan out one subagent per doc to audit + draft, each verifying against the code; review every draft yourself.
4. Produce the divergence map, the compression plan (with old→new for meaning-touching edits), the Contradiction Register (genuine conflicts, both sides quoted), and the Removal Ledger (deletions + lossy compressions, most-risky-first, full quotes).

**Then STOP and wait for the human line-item review. Edit no doc until the user approves.** After approval: Phase B → Phase C → the repo's check gate → leave changes uncommitted for retest. Follow this repo's own `CLAUDE.md`/`AGENTS.md` workflow where it applies; skip any step (plan mode, grilling, TDD) the repo doesn't have.

### Per-repo fill-ins
- **Backend (e.g. Kotlin):** focus on build/test gotchas, the API-boundary/serialization contract, and framework conventions that override defaults; drop frontend topic docs. *Codegen exemption:* if the repo generates code (OpenAPI/proto stubs, etc.), exempt generated files from these rules and note where they're generated.
- **Infrastructure (IaC):** focus on the tool's conventions, **provider/module version pinning (often load-bearing — keep it; see the durability carve-out)**, state/backend/workspace boundaries and state-mutation gotchas (`import`, `state mv`, drift), environment/secrets handling, and plan/apply workflow gotchas. Drop application-code rules; if the repo synthesizes/generates config, exempt the generated output.

### When to grill instead of just running
- **Grill first** (`grill-me`, or `grill-with-docs` if terminology/ADRs are in play) **when those skills are installed** and the doc set is large (~5+ docs), you expect disagreement about what's load-bearing, or the repo has domain terminology worth sharpening. Point the grilling at the **Removal Ledger**: make the agent *defend each proposed cut* against the gauntlet and Hard Stops.
- **Skip grilling** for small/clear-cut doc sets — the Phase-A ledger + the human line-item review is enough.
