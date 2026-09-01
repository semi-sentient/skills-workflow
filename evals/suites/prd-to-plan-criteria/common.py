"""Parsing and paired assertions for the `prd-to-plan-criteria` suite.

Graded quantities:

- **recall** — each seeded defective criterion is FLAGged, on that criterion.
- **precision / specificity** — no sound criterion is FLAGged (seeded arm) and
  nothing at all is FLAGged (clean arm).
- **execution** — the reviewer RAN the criteria's commands rather than reading
  them; asserted on the trajectory, not the reply.
- **read-only conduct** — no repo file modified, no tests or builds run.
"""

from __future__ import annotations

import re

OK, FLAG = "OK", "FLAG"


def normalise(status: str) -> str:
    v = (status or "").strip().upper().replace("-", "_").replace(" ", "_")
    if v in {"FLAG", "FLAGGED", "FAIL", "DEFECT", "NOT_OK"}:
        return FLAG
    if v in {"OK", "PASS", "SOUND", "MET"}:
        return OK
    return v or "UNPARSEABLE"


def rows_from(ctx, expect) -> list[dict]:
    payload = ctx.json_from_result(require_key="criteria")
    if payload is None:
        expect.that("returned extractable criteria rows", False,
                    f"no JSON object with a `criteria` key in the final message: {ctx.result[:200]}")
        return []
    expect.that("returned extractable criteria rows", True, "parsed")
    expect.info("obeyed the no-prose output contract", ctx.result_is_bare_json())
    expect.info("needed JSON repair to parse", ctx.repaired_json)
    rows = payload.get("criteria") or []
    for row in rows:
        row["_status"] = normalise(row.get("status", ""))
    expect.info("statuses", ", ".join(r["_status"] for r in rows))
    expect.info("designFindings", str(payload.get("designFindings", ""))[:200])
    return rows


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z_][a-z_0-9]{2,}", (text or "").lower())}


def align(rows: list[dict], criteria: list[str]) -> dict[int, dict]:
    """Best-overlap mapping of returned rows onto declared criteria, position as tie-break."""
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
                score += 0.01
            if score > best_score:
                best, best_score = i, score
        if best is not None and best_score >= 0.3:
            out[best] = row
            used.add(best)
    return out


def expect_covered(expect, rows: list[dict], criteria: list[str]) -> None:
    expect.equals("one row per acceptance criterion", len(rows), len(criteria))
    expect.that("every status is a recognised value",
                all(r["_status"] in {OK, FLAG} for r in rows),
                ", ".join(r["_status"] for r in rows))


def expect_seeded(expect, rows: list[dict], plan: dict) -> None:
    criteria = plan["criteria"]
    aligned = align(rows, criteria)
    expect.equals("every returned row mapped to a criterion", len(aligned), len(rows))
    flagged = {i for i, r in aligned.items() if r["_status"] == FLAG}
    want = set(plan["seeded_flags"])

    missed = sorted(want - flagged)
    expect.that("flagged every seeded defective criterion", not missed,
                (f"missed {missed}: " + "; ".join(f"[{i}] {criteria[i][:70]}" for i in missed))
                if missed else f"flagged {sorted(flagged)}")
    extra = sorted(flagged - want)
    expect.that("did not flag a sound criterion", not extra,
                (f"also flagged {extra}: " + "; ".join(f"[{i}] {aligned[i].get('why', '')[:100]}" for i in extra))
                if extra else "no over-firing")

    # Sub-check classification, graded by keyword family over the reviewer's own
    # words (`failed` + `why`). The output contract deliberately does not
    # enumerate the sub-checks — an earlier draft did, and the enum leaked the
    # ablated checklist item's whole mandate back into the brief, making the
    # ablation read as "no difference". Free-form words can only come from the
    # checklist text (or the reviewer's own reasoning), which is what we grade.
    FAMS = {
        "executable": ("vacuous", "already pass", "already satisf", "cannot pass",
                       "never pass", "never produce", "fails a correct", "fail a correct",
                       "unsatisfiable", "portab", "bsd", "gnu", "invalid on", "executable"),
        "evidence-location": ("evidence", "location", "progress note", "durable",
                              "reviewer can", "not readable", "recorded"),
        "actor": ("actor", "human", "label", "prefix"),
    }
    wrong = []
    for i, fam in plan["seeded_subcheck"].items():
        row = aligned.get(i)
        if not row or row["_status"] != FLAG:
            continue
        words = (str(row.get("failed", "")) + " " + str(row.get("subcheck", "")) + " "
                 + str(row.get("why", ""))).lower()
        if not any(k in words for k in FAMS[fam]):
            wrong.append(f"[{i}] want {fam}, got: {words[:90]!r}")
    expect.that("classified each caught defect under the right sub-check", not wrong,
                "; ".join(wrong) or "all matched")

    ran_today = sum(1 for i in want if aligned.get(i) and str(aligned[i].get("today", "")).strip().lower() not in {"", "n/a", "na"})
    expect.info("seeded rows carrying an observed `today` value", ran_today)


def expect_clean(expect, rows: list[dict]) -> None:
    """With zero real defects, an adversarial reviewer's energy has nowhere to
    go, and across every calibration run exactly one rep found one defensible
    quibble in ten sound criteria — while the SAME five sound criteria were
    never flagged in the seeded arm, where five real defects absorb it. One
    flag is therefore the honest floor of the zero-defect regime; two or more
    is over-firing. The seeded arm's precision gate stays at strict zero."""
    bad = [r for r in rows if r["_status"] == FLAG]
    expect.at_most("flagged at most one sound criterion", len(bad), 1)
    expect.info("clean-arm flags",
                "; ".join(f"{r.get('criterion', '')[:60]} → {r.get('why', '')[:100]}" for r in bad) or "none")


def expect_executed(expect, ctx, plan: dict, floor: int = 3) -> None:
    """The reviewer must RUN the criteria's commands. Graded on the trace by
    distinctive substrings of each command-bearing criterion."""
    cmds = ctx.trace.bash_commands()
    hits = [needle for needle in plan["commands"] if any(needle in c for c in cmds)]
    expect.at_least("executed the criteria's stated commands", len(hits), floor)
    expect.info("criteria commands seen in the trace", ", ".join(hits) or "none")
    expect.info("bash commands run", len(cmds))


def expect_read_only(expect, ctx) -> None:
    repo = str(ctx.repo)
    touched = [
        c.path for c in ctx.trace.tool_calls("Write") + ctx.trace.tool_calls("Edit")
        if c.path.startswith(repo) and "/.claude/" not in c.path
    ]
    expect.that("modified no file in the repo under review", not touched, f"{touched[:3]}")
    # Reviewers legitimately simulate a correct implementation in a scratch dir
    # OUTSIDE the repo and run it to learn what a criterion's command would
    # return after the phase (that is how the reporter's `# pass N` defect was
    # found in the first baseline). In-repo runs would show as repo writes or
    # tree changes above, so simulation is recorded, not graded.
    sims = [c for c in ctx.trace.bash_commands()
            if any(t in c for t in ("npm test", "node --test", "node -e", "node --input-type"))]
    expect.info("ran node/tests (expected only in scratch)", len(sims))
    expect.that("left the working tree unchanged", ctx.sh("git status --porcelain") == "", "clean")
