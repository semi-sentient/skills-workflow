import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from common import (NEEDS_RUNTIME, align, verdicts, expect_covered_every_criterion, expect_clean,
                    expect_read_the_diff, expect_read_only_conduct, expect_read_spec_file)
from phases import BANDS_COMMAND as PHASE


def check(ctx, expect):
    rows = verdicts(ctx, expect)
    expect_covered_every_criterion(expect, rows, PHASE["criteria"])
    expect_read_spec_file(expect, ctx, ".claude/scratch/phase-2-spec.md", len(PHASE["criteria"]))
    expect_clean(expect, ctx, rows)
    by_index = align(rows, PHASE["criteria"])
    for k in PHASE["needs_runtime"]:
        got = by_index.get(k, {}).get("_verdict", "missing")
        expect.equals(f"command-decided criterion C{k + 1} is NEEDS_RUNTIME, not a static-trace MET", got, NEEDS_RUNTIME)
    # the rule must not spread to criteria a static read does decide
    others = [k for k in range(len(PHASE["criteria"])) if k not in PHASE["needs_runtime"]]
    not_met = [f"C{k + 1}={by_index.get(k, {}).get('_verdict', 'missing')}" for k in others
               if by_index.get(k, {}).get("_verdict") != "MET"]
    expect.that("every statically decidable criterion is MET", not not_met, ", ".join(not_met))
    ran = [c for c in ctx.trace.bash_commands() if re.search(r"\bnode\s+\S*check-bands", c)]
    expect.that("did not run the command criterion itself", not ran, f"{ran[:2]}")
    expect_read_the_diff(expect, ctx)
    expect_read_only_conduct(expect, ctx)
