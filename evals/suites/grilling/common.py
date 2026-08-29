"""Shared assertions for the `grilling` suite.

The simulator (harness/dialogue.py) reports *events* named by each fixture's
persona.md — "dodge_pressed:webhooks", "challenged:store". Assertions here
read those events, the interviewer's final wrap-up, and the trajectory. Each
helper states which clause of the skill it is testing, so a flip between arms
points at a sentence.

Two categories are graded differently on purpose:

- **Recall** assertions (asked the planted question, surfaced the planted
  contradiction, pressed the dodge) are about *whether the interview found
  what was there*. Both lineages claim to do this.
- **Rigour** assertions (challenged a flawed answer, wrap-up separates
  assumptions from decisions) are properties *our* fork added. Upstream is
  expected to fail them; that failure is the finding, not a bug in the suite.

Shape metrics (turns, questions per turn, cost) are recorded as info, never
graded: frontier rounds and one-question-per-turn trade them off deliberately.
"""

from __future__ import annotations

import re

WRAPUP_HEAD = r"(?im)^\W*(decisions?( made)?|summary|wrap[- ]?up|shared understanding)\b"


def events(ctx) -> list[str]:
    return ctx.dialogue.events if ctx.dialogue else []


def has(ctx, event: str) -> bool:
    return event in events(ctx)


def wrapup(ctx) -> str:
    """The interviewer's closing summary: the turn the simulated user
    confirmed; failing that, the last turn that looks like one; else the final
    turn."""
    if ctx.dialogue and ctx.dialogue.wrapup:
        return ctx.dialogue.wrapup
    turns = ctx.dialogue.interviewer_turns if ctx.dialogue else [ctx.result]
    for text in reversed(turns):
        if re.search(WRAPUP_HEAD, text):
            return text
    return turns[-1] if turns else ""


def section(text: str, heading: str) -> str:
    """Text under a markdown/bold heading matching `heading`, up to the next
    heading of the same kind (best effort — wrap-ups are prose, not schemas)."""
    m = re.search(rf"(?im)^\W*(?:#+\s*|\*\*)?[^\n]*{heading}[^\n]*$", text)
    if not m:
        return ""
    rest = text[m.end():]
    nxt = re.search(r"(?m)^\W*(?:#+\s|\*\*[A-Z])", rest)
    return rest[: nxt.start()] if nxt else rest


# ------------------------------------------------------------------ recall


def expect_asked(expect, ctx, topic: str, label: str | None = None) -> bool:
    """Persona emits `asked:<topic>` when the interviewer raises that decision.
    Tests the walk itself — "resolve each branch and the sub-decisions it unlocks"."""
    return expect.that(label or f"asked about {topic}", has(ctx, f"asked:{topic}"),
                       f"events: {sorted(set(events(ctx)))}")


def expect_contradiction(expect, ctx, topic: str) -> bool:
    """`contradiction_surfaced:<topic>`: the interviewer told the user the code
    disagrees with what they said. Tests "explore the codebase" / "cross-reference
    with code"."""
    return expect.that(f"surfaced code contradiction: {topic}",
                       has(ctx, f"contradiction_surfaced:{topic}"),
                       f"events: {sorted(set(events(ctx)))}")


def expect_dodge_pressed(expect, ctx, topic: str) -> bool:
    """`dodge_pressed:<topic>` vs `dodge_accepted:<topic>` (the latter fires at
    the wrap-up if the topic was never decided or listed as open). Tests "NEVER
    accept 'I'll figure that out later'" — a decision or an explicit open question."""
    pressed, accepted = has(ctx, f"dodge_pressed:{topic}"), has(ctx, f"dodge_accepted:{topic}")
    return expect.that(f"pressed the deferral on {topic}", pressed,
                       f"pressed={pressed} accepted={accepted}")


def expect_no_lookupable_asked(expect, ctx) -> bool:
    """`asked_lookupable:<fact>`: the user was asked something the repo answers.
    Tests "if a question can be answered by exploring the codebase, explore"."""
    asked = sorted({e for e in events(ctx) if e.startswith("asked_lookupable:")})
    return expect.that("never asked the user for a fact the repo holds", not asked,
                       f"asked: {asked}" if asked else "none asked")


# ------------------------------------------------------------------ rigour


def expect_challenged(expect, ctx, topic: str, conceded_pattern: str) -> None:
    """The persona holds a flawed position until the interviewer names the flaw
    (`challenged:<topic>`), then concedes. Two assertions: the pushback happened,
    and the wrap-up carries the corrected decision rather than the flawed one.
    Tests our "push back once before accepting" clause."""
    expect.that(f"pushed back on the flawed {topic} answer", has(ctx, f"challenged:{topic}"),
                f"events: {sorted(set(events(ctx)))}")
    if has(ctx, f"challenged:{topic}"):
        expect.match(f"wrap-up records the corrected {topic} decision", conceded_pattern, wrapup(ctx), re.I | re.S)
    else:
        # Not raised or not challenged: the first assertion already failed; a
        # second failure here would count the same miss twice.
        expect.info(f"wrap-up records the corrected {topic} decision", "n/a — not challenged")


def expect_not_silently_decided(expect, ctx, topic: str, pattern: str) -> None:
    """If the interviewer never asked about `topic` yet the wrap-up states a
    decision matching `pattern` outside an assumptions/open-questions section,
    that is a silent default. Tests the honesty rule."""
    if has(ctx, f"asked:{topic}"):
        expect.info(f"silent default check on {topic}", "n/a — topic was asked")
        return
    text = wrapup(ctx)
    flagged = section(text, r"assumption") + section(text, r"open question")
    decided = section(text, r"decision") or text
    in_decisions = re.search(pattern, decided, re.I | re.S) is not None
    in_flagged = re.search(pattern, flagged, re.I | re.S) is not None
    expect.that(f"{topic} not silently decided", (not in_decisions) or in_flagged,
                f"unasked; in decisions={in_decisions} in assumptions/open={in_flagged}")


def expect_wrapup_structure(expect, ctx) -> None:
    """Our stop condition: decisions / assumptions / open questions, each
    distinguishable. Upstream has no wrap-up contract, so this is expected to
    discriminate the lineages."""
    text = wrapup(ctx)
    expect.match("wrap-up has a decisions section", r"(?i)decisions?", text)
    expect.match("wrap-up distinguishes assumptions or open questions",
                 r"(?i)(assumptions?|open questions?)", text)


# ------------------------------------------------------------------- shape


def record_shape(expect, ctx) -> None:
    dlg = ctx.dialogue
    if not dlg:
        return
    turns = dlg.interviewer_turns
    qpt = [len(re.findall(r"\?(?:\s|$|\*)", re.sub(r"```.*?```", "", t, flags=re.S))) for t in turns]
    numbered = sum(1 for t in turns if len(re.findall(r"(?m)^\W*\**Q?\d+[.)\]:\s*-]", t)) >= 2)
    expect.info("interviewer turns", len(turns))
    expect.info("questions per turn (max/mean)", f"{max(qpt) if qpt else 0}/{(sum(qpt) / len(qpt)) if qpt else 0:.1f}")
    expect.info("turns with >=2 numbered questions", numbered)
    expect.info("bundled-dependent events", sum(1 for e in dlg.events if e == "bundled_dependent"))
    expect.info("sub-agents dispatched", len(ctx.trace.subagents()))
    expect.info("stop reason", dlg.stop_reason)
    expect.info("simulator cost_usd", round(dlg.sim_cost_usd, 3))
    expect.that("interview reached a close", dlg.stop_reason == "user confirmed", dlg.stop_reason)
