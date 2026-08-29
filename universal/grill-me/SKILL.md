---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree and the sub-decisions it unlocks. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me", "devil's advocate", "challenge my assumptions", "poke holes in my plan", "what am I missing". Also use instead of asking ad hoc when you are about to ask the user three or more design questions, or any question whose answer would change what you ask next.
---

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
