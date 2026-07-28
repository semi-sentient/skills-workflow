#!/usr/bin/env python3
"""Tier 1 runner — behavioural fixtures for the skill corpus.

Answers one question: does this change to a skill make it better or worse?
It does that by running the same fixtures against two skill versions and
diffing the assertion pass rates.

    # what does the current working tree do?
    ./evals/run.py commit

    # did my edit help? (this is the one you want)
    ./evals/run.py commit --compare HEAD --reps 3

    # what would run, and what would it cost?
    ./evals/run.py --dry-run

Every run spends real tokens. --dry-run prints the plan and an estimate first.
Fixture repos are built under ~/.skills-evals/<run-id>/ and left in place so a
failure can be opened and read; nothing is written inside this repository.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness import Arm, Report, Runner, compare, discover_fixtures  # noqa: E402
from harness.runner import DEFAULT_WORKDIR, REPO  # noqa: E402

# Rough per-run cost, used only for the --dry-run estimate and the
# confirmation prompt. Observed range for these fixtures is $0.10-$0.60.
COST_PER_RUN_USD = 0.35


def check_prereqs() -> list[str]:
    problems = []
    if subprocess.run(["which", "claude"], capture_output=True).returncode != 0:
        problems.append("`claude` CLI not on PATH.")
    if subprocess.run(["git", "-C", str(REPO), "rev-parse", "--git-dir"],
                      capture_output=True).returncode != 0:
        problems.append(f"{REPO} is not a git repository (arms resolve git refs).")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(__doc__.splitlines()[1:]),
    )
    ap.add_argument("suite", nargs="?", help="suite name (default: all)")
    ap.add_argument("--fixture", action="append", default=[],
                    help="limit to named fixture(s); repeatable")
    ap.add_argument("--arm", default="worktree",
                    help="skill version under test: 'worktree' or a git ref (default: worktree)")
    ap.add_argument("--compare", metavar="REF",
                    help="baseline version to diff against, e.g. HEAD or HEAD~1")
    ap.add_argument("--ablate", action="append", default=[], metavar="PATH:REGEX",
                    help="delete a span from the candidate arm's skill before running, to test "
                         "whether a clause earns its place (e.g. "
                         "'references/agent-operations.md:Assume the implementation fails.*?presumed\\.'). "
                         "Repeatable. Pair with --compare worktree for a clean ablation A/B.")
    ap.add_argument("--reps", type=int, default=1,
                    help="replicates per fixture per arm (default 1; use 3 for a verdict)")
    ap.add_argument("--jobs", type=int, default=4, help="concurrent runs (default 4)")
    ap.add_argument("--model", help="pin the model for every arm (holds the comparison honest)")
    ap.add_argument("--workdir", default=str(DEFAULT_WORKDIR), help="where fixture repos are built")
    ap.add_argument("--run-id", help="name this run (default: a timestamp)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and estimate, run nothing")
    ap.add_argument("--yes", action="store_true", help="skip the cost confirmation")
    ap.add_argument("--gate", action="store_true",
                    help="exit nonzero on any regression or failing assertion (for CI)")
    ap.add_argument("--json", dest="json_out", help="also write the full result set here")
    ap.add_argument("--baseline-out", metavar="PATH",
                    help="write a compact, diffable record of this run (commit it, so the "
                         "next change to the skill has something to be compared against)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    problems = check_prereqs()
    if problems:
        for p in problems:
            print(f"error: {p}", file=sys.stderr)
        return 1

    fixtures = discover_fixtures(args.suite, args.fixture or None)
    if not fixtures:
        target = args.suite or "any suite"
        print(f"No fixtures found for {target}.", file=sys.stderr)
        return 1

    ablations: list[tuple[str, str]] = []
    for spec in args.ablate:
        path, sep, pattern = spec.partition(":")
        if not sep or not pattern:
            print(f"error: --ablate expects PATH:REGEX, got {spec!r}", file=sys.stderr)
            return 1
        ablations.append((path, pattern))

    arms = [Arm(args.arm, ablations)]
    if args.compare:
        arms.insert(0, Arm(args.compare))  # baseline first, always un-ablated
    if ablations and args.compare == args.arm and len(arms) == 2:
        arms[0] = Arm(args.compare)  # same ref, distinct labels via ablation

    total_runs = len(fixtures) * len(arms) * args.reps
    print(f"{len(fixtures)} fixture(s) x {len(arms)} arm(s) x {args.reps} rep(s) = {total_runs} runs")
    for arm in arms:
        try:
            print(f"  arm {arm.label}: {arm.resolve()}")
        except Exception as exc:
            print(f"  arm {arm.label}: unresolvable — {exc}", file=sys.stderr)
            return 1
    for fx in fixtures:
        print(f"  - {fx.suite}/{fx.name}: {fx.description}")
    print(f"\nEstimated cost: ~${total_runs * COST_PER_RUN_USD:.2f} "
          f"(~${COST_PER_RUN_USD:.2f}/run, varies with fixture size)")

    if args.dry_run:
        print("\n--dry-run: nothing executed.")
        return 0

    if not args.yes and sys.stdin.isatty():
        reply = input("Proceed? [y/N] ").strip().lower()
        if reply != "y":
            print("Aborted.")
            return 1

    run_id = args.run_id or time.strftime("%Y%m%dT%H%M%S")
    runner = Runner(Path(args.workdir), run_id, model=args.model, verbose=args.verbose)
    print(f"\nworkdir: {runner.workdir / run_id}\n")

    jobs = [(fx, arm, rep) for arm in arms for fx in fixtures for rep in range(1, args.reps + 1)]
    started = time.time()
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        outcomes = list(pool.map(lambda j: runner.run_one(*j), jobs))

    report = Report(outcomes)
    print(report.render())
    print(f"\nwall clock {(time.time() - started) / 60:.1f} min, "
          f"billed ${report.cost():.2f} across {len(outcomes)} run(s)")

    regressions = 0
    if args.compare:
        print()
        deltas, summary = compare(report, arms[0].label, arms[1].label)
        print(summary)
        regressions = sum(1 for d in deltas if d.verdict == "regressed")

    if args.baseline_out:
        out = Path(args.baseline_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(
                report.baseline({a.label: a.resolve() for a in arms}, args.reps), indent=2
            )
            + "\n",
            "utf-8",
        )
        print(f"\nbaseline recorded: {out}")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "arms": [a.label for a in arms],
                    "reps": args.reps,
                    "outcomes": [o.to_dict() for o in outcomes],
                },
                indent=2,
            ),
            "utf-8",
        )
        print(f"\nfull results: {args.json_out}")

    if args.gate:
        failed = [o for o in outcomes if not o.passed]
        if regressions or failed:
            print(f"\n--gate: {regressions} regression(s), {len(failed)} failing run(s).")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
