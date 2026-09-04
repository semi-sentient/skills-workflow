import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from common import (verdicts, expect_covered_every_criterion, expect_clean,
                    expect_read_the_diff, expect_read_only_conduct, expect_read_spec_file)
from phases import BANDS as PHASE


def check(ctx, expect):
    rows = verdicts(ctx, expect)
    expect_covered_every_criterion(expect, rows, PHASE["criteria"])
    expect_read_spec_file(expect, ctx, ".claude/scratch/phase-2-spec.md", len(PHASE["criteria"]))
    expect_clean(expect, ctx, rows)
    expect_read_the_diff(expect, ctx)
    expect_read_only_conduct(expect, ctx)
