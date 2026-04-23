---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree and the sub-decisions it unlocks. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me", "devil's advocate", "challenge my assumptions", "poke holes in my plan", "what am I missing". Pass `--light` for a faster pass with no counter-challenges.
---

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the decision tree, resolving both top-level decisions and the sub-decisions they unlock. For each question, provide your recommended answer.

Ask one question at a time. You may bundle 2 (rarely 3) sub-decisions into one turn only when they're all parameters of the same choice you just made, such that asking separately would require restating the same setup. If the bundle would require more than a short paragraph of setup plus brief options, split it. Err on the side of splitting.

If a question can be answered by exploring the codebase, explore instead of asking. Keep exploring mid-interview whenever an answer surfaces a new constraint that reshapes later branches.

When I answer directly — not by picking from a menu you offered — push back once before accepting ("Did you consider X?", "What breaks if Y?"). One probe, then move on. Skip the challenge if I picked from your menu, or if I pass `--light`.

## Stop condition

Stop when every branch and its unlocked sub-decisions have a decision or an explicit open question. Produce a wrap-up with three sections: **Decisions made** (with brief rationale), **Assumptions accepted** (each with a one-line justification), **Open questions still requiring resolution**.

**Honesty rule:** Any default I did not explicitly confirm belongs under "assumptions" or "open questions," never silently in "decisions." If assumptions exceed ~3 items, you missed questions — go back and ask.

## NEVER

- NEVER accept "I'll figure that out later" — require a decision or mark it as an open question.
- NEVER ask multiple top-level questions in one turn (bundling coupled sub-decisions within one branch is fine).
- NEVER stop at surface-level branches — drill into sub-decisions as they emerge from answers.
- NEVER silently default on something I didn't confirm.
