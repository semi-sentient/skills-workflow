# Restructure — Monolith → Topic Docs (authoritative reference)

> **This is the restructure branch of the `tend-steering-docs` skill.** The router (`SKILL.md`) sends you here when a repo's steering docs are a **monolith** that needs splitting into topic docs. Run it as its **own PR**. This branch **only moves content** — it never condenses, cuts, deduplicates, or rewords. All of that is deferred to the condense branch ([condense.md](condense.md)) in a separate, later PR.
>
> **Why its own pure-move PR:** a split touches everything and silently loses or fragments rules if rushed. Keeping it a strict move makes the PR diff read "relocated + structured, nothing lost" — trivially reviewable — and lets the condense PR do all the judgment-laden cutting under its own gate. Two PRs, two jobs: structure, then condense. Split first because a pure move is easy to verify, the later condense then runs on bounded topic docs, and cross-topic redundancy only becomes collapsible once topics are separated.

A "monolith" here = a single steering doc large enough that distinct concerns are interleaved and hard to navigate — concretely, it already mixes the topics that would become 3+ standalone docs.

---

## When to use this (and when not)

**The sole deciding question:** imagine the keep-worthy rules after a mental cleanup — do they cluster into **3 or more** coherent topics, each with enough load-bearing content to stand alone as a doc?

- **Yes → split first** (this branch), *even if the doc also carries heavy removable bloat*. Bloat is cheaper to cut once distributed into bounded topic docs, and splitting surfaces the cross-topic redundancy the condense pass needs to see.
- **No (1–2 thin topics survive) → skip this**; just run the condense branch in place. There's no structure worth building.

"Is there bloat?" is **not** the deciding question — topic count is. (Bloat removal happens in the condense PR regardless of order.)

---

## Prime directive: move, don't cut

The **only** permitted changes in this PR:

1. **Atomize** prose into "one rule = one bullet under a header" — reformatting only. **Do NOT atomize a compound or conditional rule** (one containing `unless / if / except / when / but / only`, a semicolon joining clauses, or a main-plus-exception shape): it moves as a **single verbatim bullet**. An exclusion (`not Z`), its rationale (`why`), and any conditions must stay together in one bullet and therefore one destination. Atomize only genuinely independent enumerations.
2. **Move** each rule **verbatim** into exactly one primary home.
3. **Create** a minimal root doc (charter + always-on non-negotiables + a Topic Documentation table) and the topic docs.
4. **Archive** only *unambiguously* dead content (the monolith itself says deprecated/superseded) into a history doc — *route, don't delete*.

**Nothing is condensed, cut, reworded, or deduplicated.** Even verbatim duplicates are preserved (a rule in three monolith sections becomes that rule in three topic docs) — collapsing them is the condense PR's job. This is what lets the split PR promise "nothing lost, period." Brevity is **few sections via relocation, never fewer words.**

---

## Step 0 — orient

- **Pick the layout.** If the repo already has a steering-doc convention (a sibling layout, a topic dir, a canonical-file-plus-symlink pattern), **mirror it exactly**. If there is **none** (e.g. a lone `CLAUDE.md` with no `docs/`), adopt this default: keep the monolith's own filename as the canonical root doc, put topic docs in a new sibling `docs/agents/`, and the archive at `docs/agents/history.md`. Don't introduce a symlink or a second root filename unless the repo's tooling already expects one.
- **Derive topic seams from the doc's own section clusters** — let existing headings cluster into topics; don't impose an external taxonomy.

---

## Procedure

1. **Normalize into a scratch artifact (non-destructive).** Atomize prose into rules (honoring the compound/conditional carve-out) and write the result to `.agents/scratch/` — **do not edit the monolith in place.** The untouched original is the baseline the completeness proof (step 5) diffs against.
2. **Build the mapping table — then STOP for review.** One row per rule; create no files yet:

   | Rule (verbatim quote + monolith location) | Primary home (a topic doc, or ROOT) | Also relevant to (secondary topics) | Duplicate-of (canonical source, if repeated) | Superseded? (named successor location, or —) |

   This table is the gate. The human confirms **(a)** every rule has a home; **(b)** every always-on rule is routed to ROOT, not buried in a topic doc; **(c)** no atomized bullet separated an exclusion/condition/why from its rule; **(d)** every "superseded" row names its successor — bare "looks old" is not allowed; when supersession is uncertain, **keep it live** and defer to the condense PR; **(e)** any genuine rule-vs-rule contradiction spotted while mapping is **noted for the condense PR, not resolved here** — resolving a conflict is an edit, and this PR is move-only, so both conflicting rules move verbatim to their homes and the conflict goes on the condense worklist.
3. **Create the structure.** The minimal root doc + one topic doc per cluster + the history doc. *Root-membership test:* a rule belongs in ROOT iff it constrains **how any task is executed regardless of topic** (process/safety/escalation rules, the priority order, cross-cutting prohibitions); topic docs hold rules that apply only when a task touches that topic. Unsure → ROOT.
4. **Move, verbatim.** Place each rule in its mapped home, unchanged. Do **not** add cross-references, collapse duplicates, or rewrite — a rule with a real second home goes in its **primary** home only; its secondary topics are recorded in the table for the condense PR to resolve. The duplicate-set rows in the table are the condense PR's dedup worklist (so it knows which copies were identical and which is canonical).
5. **Prove completeness (the safeguard).** Verify against the **pre-normalization** original (the scratch baseline), by string, not by meaning:
   - **Coverage:** every word in the new docs traces to the monolith — nothing invented.
   - **Conservation:** every sentence of the monolith appears verbatim in exactly one destination (atomized only into co-located bullets within the *same* home — never paraphrased, never justified as "says the same thing").
   - **Live-set:** ROOT + topic docs (excluding the archive) retain every rule *except* those explicitly marked superseded-with-a-named-successor. An archived rule with no successor is a failure, not a pass.

   Have an independent reviewer or fresh agent confirm all three against the original.
6. **Validate + open its own PR.** Run any doc-sync step the repo has (e.g. a canonical→symlink sync) and whatever validation it provides — if none applies to docs, say so and skip. Title it as a pure move, e.g. *"docs: Split `<monolith filename>` into topic docs (no content change)"*, so reviewers verify *nothing was lost* rather than re-litigating rules. Leave uncommitted for retest if that's the repo's norm (default: leave uncommitted and summarize).

---

## Then: condense (separate PR)

After the split PR merges — **promptly, as the next PR** (the scattered duplicates are an unstable intermediate state that can drift) — run the condense branch ([condense.md](condense.md)) on the new topic docs. That second PR is where cutting, compressing, collapsing the duplicates this split surfaced, and **resolving the contradictions this split noted** all happen, under the condense gate, using the duplicate-set, secondary-topic, and noted-contradiction rows from this split's mapping table as its worklist.
