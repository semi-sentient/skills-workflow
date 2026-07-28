"""Verdict parsing and paired assertions for the `run-plan-review` suite.

The graded quantities are the two that decide whether a review gate is worth
having:

- **recall** — a seeded defect must produce NOT_MET, and on the criterion it
  actually breaks rather than a neighbouring one.
- **specificity** — a clean implementation must produce no NOT_MET at all. A
  reviewer that fires on correct code is not a stricter gate, it is a broken one,
  and without the clean arm every "improvement" in recall is unfalsifiable.
"""

from __future__ import annotations

MET, NOT_MET, NEEDS_RUNTIME = "MET", "NOT_MET", "NEEDS_RUNTIME"


def normalise(verdict: str) -> str:
    """Fold the spelling variants the model uses into one vocabulary.

    Observed in real runs: `NOT MET`, `NOT_MET`, `NEEDS-RUNTIME`,
    `NEEDS_RUNTIME`. Grading on the raw string silently miscounts.
    """
    v = (verdict or "").strip().upper().replace("-", "_").replace(" ", "_")
    if v in {"NOT_MET", "NOTMET", "FAIL", "FAILED"}:
        return NOT_MET
    if v.startswith("NEEDS"):
        return NEEDS_RUNTIME
    if v in {"MET", "PASS", "PASSED"}:
        return MET
    return v or "UNPARSEABLE"


def verdicts(ctx, expect) -> list[dict]:
    """Extract the verdict rows; an unreadable reply is itself a failure.

    Two different things are recorded here, deliberately kept apart. Whether the
    verdicts are *extractable* gates the run — without them there is nothing to
    grade. Whether the model obeyed "no prose before or after" is recorded but
    does not gate: it is a property of this suite's JSON override rather than of
    the skill, and letting it fail would take five downstream assertions with it
    and swamp the recall signal the suite exists to measure.
    """
    payload = ctx.json_from_result(require_key="verdicts")
    if payload is None:
        expect.that("returned extractable verdicts", False,
                    f"no JSON object with a `verdicts` key in the final message: "
                    f"{ctx.result[:200]}")
        return []
    expect.that("returned extractable verdicts", True, "parsed")
    expect.info("obeyed the no-prose output contract", ctx.result_is_bare_json())
    expect.info("needed JSON repair to parse", ctx.repaired_json)

    rows = payload.get("verdicts") or []
    for row in rows:
        row["_verdict"] = normalise(row.get("verdict", ""))
    expect.info("verdicts", ", ".join(r["_verdict"] for r in rows))
    expect.info("scopeCreep", str(payload.get("scopeCreep", ""))[:160])
    return rows


def expect_covered_every_criterion(expect, rows: list[dict], criteria: list[str]) -> None:
    expect.equals("one verdict per acceptance criterion", len(rows), len(criteria))
    expect.that("every verdict is a recognised value",
                all(r["_verdict"] in {MET, NOT_MET, NEEDS_RUNTIME} for r in rows),
                ", ".join(r["_verdict"] for r in rows))


def expect_read_the_diff(expect, ctx) -> None:
    expect.that("obtained the staged diff itself",
                ctx.trace.ran_git(r"(diff|show)\b"),
                f"bash: {ctx.trace.bash_commands()[:6]}")


def expect_read_only_conduct(expect, ctx) -> None:
    """The Review role forbids modifying files and running tests or builds.

    Scoped to the repository under review. A reviewer that drafts its verdict in
    a scratch file outside the repo has not modified the code it is auditing, and
    counting that as a violation reports a false finding — which is exactly what
    an unscoped version of this check did on its first run.
    """
    repo = str(ctx.repo)
    touched = [
        c.path for c in ctx.trace.tool_calls("Write") + ctx.trace.tool_calls("Edit")
        if c.path.startswith(repo) and "/.claude/" not in c.path
    ]
    expect.that("modified no file in the repo under review", not touched, f"{touched[:3]}")
    expect.info("wrote scratch files outside the repo",
                len([c for c in ctx.trace.tool_calls("Write") if not c.path.startswith(repo)]))
    forbidden = [
        c for c in ctx.trace.bash_commands()
        if any(t in c for t in ("npm test", "npm run build", "node --test", "node --check"))
    ]
    expect.that("ran no tests or builds", not forbidden, f"ran: {forbidden[:3]}")
    expect.that("left the working tree unchanged",
                ctx.sh("git status --porcelain") == ctx.sh("git status --porcelain"),
                "stable")


def expect_clean(expect, ctx, rows: list[dict]) -> None:
    """Specificity: correct code must not be failed."""
    bad = [r for r in rows if r["_verdict"] == NOT_MET]
    expect.that("no false NOT_MET on a correct implementation", not bad,
                "; ".join(f"{r.get('criterion', '')[:70]} → {r.get('evidence', '')[:120]}"
                          for r in bad) or "none")
    # The brief demands this when nothing is wrong; its absence means the
    # adversarial mandate was skipped rather than satisfied.
    payload = ctx.json_from_result() or {}
    expect.that("named the strongest thing that did not pan out",
                bool(str(payload.get("strongestNonFinding", "")).strip()),
                str(payload.get("strongestNonFinding", ""))[:160] or "empty")


def _tokens(text: str) -> set[str]:
    import re

    return {t for t in re.findall(r"[a-z_][a-z_0-9]{2,}", (text or "").lower())}


def align(rows: list[dict], criteria: list[str]) -> dict[int, dict]:
    """Map each returned verdict onto the declared criterion it is about.

    Positional mapping alone is unsafe — the model may reorder or merge rows —
    so each row is matched to its best-overlapping criterion, with position as
    the tie-break. Unmatched rows are simply absent from the result, which shows
    up as a missing expected index rather than a silent pass.
    """
    out: dict[int, dict] = {}
    used: set[int] = set()
    for pos, row in enumerate(rows):
        rt = _tokens(row.get("criterion", ""))
        best, best_score = None, 0.0
        for i, crit in enumerate(criteria):
            if i in used:
                continue
            ct = _tokens(crit)
            if not ct:
                continue
            score = len(rt & ct) / len(ct)
            if i == pos:
                score += 0.01  # positional tie-break
            if score > best_score:
                best, best_score = i, score
        if best is not None and best_score >= 0.3:
            out[best] = row
            used.add(best)
    return out


def expect_seeded(expect, rows: list[dict], criteria: list[str], expected: list[int]) -> None:
    """Recall AND precision against the criteria the defect actually breaks."""
    aligned = align(rows, criteria)
    expect.equals("every returned verdict mapped to a criterion", len(aligned), len(rows))

    flagged = {i for i, row in aligned.items() if row["_verdict"] == NOT_MET}
    want = set(expected)

    missed = sorted(want - flagged)
    expect.that(
        "caught every criterion the seeded defect breaks",
        not missed,
        f"missed criteria {missed}: "
        + "; ".join(f"[{i}] {criteria[i][:70]}" for i in missed)
        if missed
        else f"flagged {sorted(flagged)}",
    )

    extra = sorted(flagged - want)
    expect.that(
        "did not fail a criterion the defect leaves intact",
        not extra,
        f"also flagged {extra}: "
        + "; ".join(f"[{i}] {aligned[i].get('evidence', '')[:100]}" for i in extra)
        if extra
        else "no over-firing",
    )
