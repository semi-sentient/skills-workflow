---
name: grill-with-docs
description: Grilling session that challenges your plan against the existing domain model, sharpens terminology, and updates documentation (CONTEXT.md, ADRs) inline as decisions crystallise. Use when user wants to stress-test a plan against their project's language and documented decisions. Also use instead of asking ad hoc when you are about to ask the user three or more design questions, or any question whose answer would change what you ask next; prefer this skill over grill-me when the repo has a CONTEXT.md or ADRs.
---

<what-to-do>

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Map it as a decision tree: every decision branches into the sub-decisions it unlocks. For each question, provide your recommended answer.

## Rounds

Work the tree in rounds. The frontier is every decision whose prerequisites are already settled — the questions you can ask now without guessing at answers you haven't heard. Ask the whole frontier in one round, numbered, each with your recommendation, then wait for my answers. A question whose answer depends on another question still open in this round belongs to a later round.

Format a round like so:

```
❓ **Q1** - **<question title>**: <question body, including options where they help>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body>

➡️ <your recommended answer>
```

Each round of answers reshapes the tree: settled decisions push the frontier outward and unblock the questions that depended on them. Recompute the frontier and ask the next round.

## Facts are yours, decisions are mine

Finding facts is your job, never mine. When a question needs a fact from the environment — the codebase, config, tooling — dispatch a sub-agent to find it instead of asking me. Don't block the round on it: only the questions downstream of that fact wait for the answer; ask the rest of the frontier now. Read `CONTEXT.md` if it exists so your questions use the project's domain language, and respect ADRs in the area the plan touches. Keep looking whenever an answer surfaces a new constraint that reshapes later branches. The decisions are mine: put each one to me and wait.

## Challenge

When I answer directly — not by picking from options you offered — push back once before accepting ("Did you consider X?", "What breaks if Y?"). The probe is a frontier item: it goes in the next round, numbered like any other question. One probe per answer, then move on. Skip the probe if I picked from your options.

## Stop condition

Stop when the frontier is empty: every branch and its unlocked sub-decisions have a decision or an explicit open question. Produce a wrap-up with three sections: **Decisions made** (with brief rationale), **Assumptions accepted** (each with a one-line justification), **Open questions still requiring resolution**. Do not act on the plan until I confirm we have reached a shared understanding.

**Honesty rule:** Any default I did not explicitly confirm belongs under "assumptions" or "open questions," never silently in "decisions." If assumptions exceed ~3 items, you missed questions — go back and ask.

## NEVER

- NEVER accept "I'll figure that out later" — require a decision or mark it as an open question.
- NEVER stop at surface-level branches — drill into sub-decisions as they emerge from answers.
- NEVER silently default on something I didn't confirm.
- NEVER ask me for a fact you could look up.

</what-to-do>

<supporting-info>

## Domain awareness

During codebase exploration, also look for existing documentation:

### File structure

Most repos have a single context:

```
/
├── CONTEXT.md
├── docs/
│   └── adr/
│       ├── 0001-event-sourced-orders.md
│       └── 0002-postgres-for-write-model.md
└── src/
```

If a `CONTEXT-MAP.md` exists at the root, the repo has multiple contexts. The map points to where each one lives:

```
/
├── CONTEXT-MAP.md
├── docs/
│   └── adr/                          ← system-wide decisions
├── src/
│   ├── ordering/
│   │   ├── CONTEXT.md
│   │   └── docs/adr/                 ← context-specific decisions
│   └── billing/
│       ├── CONTEXT.md
│       └── docs/adr/
```

Create files lazily — only when you have something to write. If no `CONTEXT.md` exists, create one when the first term is resolved. If no `docs/adr/` exists, create it when the first ADR is needed.

## During the session

### Challenge against the glossary

When the user uses a term that conflicts with the existing language in `CONTEXT.md`, call it out immediately. "Your glossary defines 'cancellation' as X, but you seem to mean Y — which is it?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. "You're saying 'account' — do you mean the Customer or the User? Those are different things."

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios that probe edge cases and force the user to be precise about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it: "Your code cancels entire Orders, but you just said partial cancellation is possible — which is right?"

### Update CONTEXT.md inline

When a term is resolved, update `CONTEXT.md` right there. Don't batch these up — capture them as they happen. Use the format in [references/CONTEXT-FORMAT.md](./references/CONTEXT-FORMAT.md).

`CONTEXT.md` should be totally devoid of implementation details. Do not treat `CONTEXT.md` as a spec, a scratch pad, or a repository for implementation decisions. It is a glossary and nothing else.

### Offer ADRs sparingly

Only offer to create an ADR when all three are true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the ADR. Use the format in [references/ADR-FORMAT.md](./references/ADR-FORMAT.md).

</supporting-info>
