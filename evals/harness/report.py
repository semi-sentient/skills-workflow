"""Aggregate outcomes and compare two arms.

Deliberately reports raw counts rather than p-values. At the replicate counts
this suite is affordable at (n=3 per cell), a significance test would be
theatre. What n=3 *can* establish is the thing these fixtures are built for: a
deterministic invariant flipping 3/3 → 0/3 is decisive; a 2/3 → 3/3 drift is
noise until replicated.

Two classifications matter as much as the pass rates:

- **unstable** — reps within one arm disagree. Either the fixture is not
  pinning down what it claims, or the skill is genuinely non-deterministic
  there. Both want investigating before the number is quoted.
- **non-discriminating** — the assertion passes everywhere in both arms. It
  costs money every run and tells you nothing about the change. Keep it only if
  it guards a regression you expect to be possible.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .runner import RunOutcome

IMPROVED, REGRESSED, UNCHANGED, FLAT = "improved", "regressed", "unchanged", "non-discriminating"


@dataclass
class Cell:
    """One assertion, one fixture, one arm, across reps."""

    passes: int = 0
    total: int = 0
    evidence: list[str] = field(default_factory=list)

    @property
    def rate(self) -> float:
        return self.passes / self.total if self.total else 0.0

    @property
    def unstable(self) -> bool:
        return 0 < self.passes < self.total

    def __str__(self) -> str:
        return f"{self.passes}/{self.total}"


class Report:
    def __init__(self, outcomes: list[RunOutcome]):
        self.outcomes = outcomes
        self.arms: list[str] = []
        # (suite, fixture, assertion) -> arm -> Cell
        self.cells: dict[tuple[str, str, str], dict[str, Cell]] = {}
        self.errors: list[RunOutcome] = []

        for o in outcomes:
            if o.arm not in self.arms:
                self.arms.append(o.arm)
            if o.error:
                self.errors.append(o)
            for r in o.graded:
                key = (o.fixture.suite, o.fixture.name, r.name)
                cell = self.cells.setdefault(key, {}).setdefault(o.arm, Cell())
                cell.total += 1
                cell.passes += int(r.passed)
                if not r.passed and r.evidence:
                    cell.evidence.append(r.evidence)

    # ------------------------------------------------------------ totals

    def cost(self, arm: str | None = None) -> float:
        return sum(o.cost_usd for o in self.outcomes if arm is None or o.arm == arm)

    def duration_s(self, arm: str | None = None) -> float:
        return sum(o.duration_ms for o in self.outcomes if arm is None or o.arm == arm) / 1000

    def models(self) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {}
        for o in self.outcomes:
            if o.model:
                out.setdefault(o.arm, set()).add(o.model)
        return out

    def pass_rate(self, arm: str) -> tuple[int, int]:
        cells = [c[arm] for c in self.cells.values() if arm in c]
        return sum(x.passes for x in cells), sum(x.total for x in cells)

    def baseline(self, arms: dict[str, str], reps: int) -> dict:
        """A compact, diffable record of this run.

        This is the artifact whose absence made the July 2026 benchmark
        unrepeatable: the numbers existed, but only inside session transcripts
        that were discarded with the worktrees. Committing this means the next
        change to a skill has something to be compared against.
        """
        from datetime import datetime, timezone

        fixtures: dict[str, dict[str, dict[str, str]]] = {}
        for (suite, fixture, assertion), by_arm in self.cells.items():
            key = f"{suite}/{fixture}"
            fixtures.setdefault(key, {})[assertion] = {
                arm: str(cell) for arm, cell in by_arm.items()
            }
        return {
            "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "reps": reps,
            "arms": arms,
            "models": {arm: sorted(ms) for arm, ms in self.models().items()},
            "totals": {
                arm: {
                    "passed": self.pass_rate(arm)[0],
                    "of": self.pass_rate(arm)[1],
                    "cost_usd": round(self.cost(arm), 3),
                }
                for arm in self.arms
            },
            "errors": [
                {"fixture": o.fixture.name, "arm": o.arm, "rep": o.rep, "error": o.error}
                for o in self.errors
            ],
            "fixtures": fixtures,
        }

    def unstable(self) -> list[tuple[tuple[str, str, str], str, Cell]]:
        out = []
        for key, by_arm in self.cells.items():
            for arm, cell in by_arm.items():
                if cell.unstable:
                    out.append((key, arm, cell))
        return out

    # ------------------------------------------------------------ single

    def render(self) -> str:
        lines: list[str] = []
        for arm in self.arms:
            p, t = self.pass_rate(arm)
            lines.append(
                f"arm {arm}: {p}/{t} assertions passed  "
                f"${self.cost(arm):.2f}  {self.duration_s(arm) / 60:.1f} min"
            )
        lines.append("")

        last_fixture = None
        for (suite, fixture, assertion), by_arm in self.cells.items():
            if (suite, fixture) != last_fixture:
                lines.append(f"{suite}/{fixture}")
                last_fixture = (suite, fixture)
            cols = "  ".join(f"{arm}={by_arm[arm]}" for arm in self.arms if arm in by_arm)
            failing = any(c.passes < c.total for c in by_arm.values())
            mark = "FAIL" if failing else "ok  "
            lines.append(f"  {mark}  {assertion}  [{cols}]")
            if failing:
                for arm in self.arms:
                    cell = by_arm.get(arm)
                    if cell and cell.evidence:
                        lines.append(f"          {arm}: {cell.evidence[0]}")

        if self.errors:
            lines.append("")
            lines.append(f"{len(self.errors)} run(s) errored before grading:")
            for o in self.errors[:10]:
                lines.append(f"  {o.fixture.name} {o.arm} rep{o.rep}: {o.error}")

        unstable = self.unstable()
        if unstable:
            lines.append("")
            lines.append("Unstable cells (reps disagree — fixture or skill is not pinned down):")
            for (suite, fixture, assertion), arm, cell in unstable:
                lines.append(f"  {suite}/{fixture} [{arm}] {assertion}: {cell}")

        models = self.models()
        if len({frozenset(v) for v in models.values()}) > 1:
            lines.append("")
            lines.append("WARNING: arms did not run on the same model — the comparison is confounded.")
            for arm, ms in models.items():
                lines.append(f"  {arm}: {', '.join(sorted(ms))}")
        return "\n".join(lines)


@dataclass
class Delta:
    suite: str
    fixture: str
    assertion: str
    base: Cell
    cand: Cell
    verdict: str

    @property
    def line(self) -> str:
        return (
            f"  {self.verdict:<18} {self.suite}/{self.fixture} — {self.assertion} "
            f"[{self.base} → {self.cand}]"
        )


def compare(report: Report, base_arm: str, cand_arm: str) -> tuple[list[Delta], str]:
    """Classify every assertion as improved / regressed / unchanged / flat."""
    # An arm that never produced a graded assertion is a broken arm, not a tie.
    # Reporting "no measured difference" here would be the worst possible
    # failure: silence that reads as evidence.
    for arm in (base_arm, cand_arm):
        graded = sum(c[arm].total for c in report.cells.values() if arm in c)
        errored = [o for o in report.outcomes if o.arm == arm and o.error]
        if graded == 0:
            detail = errored[0].error if errored else "no runs recorded"
            return [], (
                f"Comparison: {base_arm} (base) → {cand_arm} (candidate)\n\n"
                f"ABORTED: arm '{arm}' produced no graded assertions "
                f"({len(errored)} errored run(s)).\n"
                f"         First error: {detail}\n"
                "         This is an apparatus failure, not a result. Fix it and re-run —\n"
                "         do not read this as 'the two versions behave the same'."
            )

    deltas: list[Delta] = []
    for (suite, fixture, assertion), by_arm in report.cells.items():
        base, cand = by_arm.get(base_arm), by_arm.get(cand_arm)
        if base is None or cand is None:
            continue
        if cand.rate > base.rate:
            verdict = IMPROVED
        elif cand.rate < base.rate:
            verdict = REGRESSED
        elif base.rate == 1.0 and cand.rate == 1.0:
            verdict = FLAT
        else:
            verdict = UNCHANGED
        deltas.append(Delta(suite, fixture, assertion, base, cand, verdict))

    order = {REGRESSED: 0, IMPROVED: 1, UNCHANGED: 2, FLAT: 3}
    deltas.sort(key=lambda d: (order[d.verdict], d.suite, d.fixture, d.assertion))

    counts = {v: sum(1 for d in deltas if d.verdict == v) for v in (IMPROVED, REGRESSED, UNCHANGED, FLAT)}
    lines = [
        f"Comparison: {base_arm} (base) → {cand_arm} (candidate)",
        "",
        f"  improved   {counts[IMPROVED]}",
        f"  regressed  {counts[REGRESSED]}",
        f"  unchanged  {counts[UNCHANGED]}   (still failing in both arms)",
        f"  flat       {counts[FLAT]}   (passing everywhere — no signal about this change)",
        "",
    ]
    shown = [d for d in deltas if d.verdict != FLAT]
    if shown:
        lines += [d.line for d in shown]
    else:
        lines.append("  Every assertion passed in both arms. This suite cannot")
        lines.append("  distinguish these two versions — add a fixture that targets the change.")

    lines.append("")
    if counts[REGRESSED]:
        lines.append(f"VERDICT: {counts[REGRESSED]} regression(s). The candidate is worse on at least one invariant.")
    elif counts[IMPROVED]:
        lines.append(f"VERDICT: {counts[IMPROVED]} improvement(s), no regressions.")
    else:
        lines.append("VERDICT: no measured difference. Either the change is behaviourally inert")
        lines.append("         on these fixtures, or no fixture covers what it touched.")

    n_reps = max((c.total for by in report.cells.values() for c in by.values()), default=0)
    if n_reps < 3:
        lines.append(f"         (n={n_reps} per cell — treat single-rep flips as unreplicated.)")

    partial = [o for o in report.outcomes if o.error]
    if partial:
        lines.append(
            f"         ({len(partial)} run(s) errored and are absent from the counts above.)"
        )
    return deltas, "\n".join(lines)
