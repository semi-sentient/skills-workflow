import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from common import (verdicts, expect_covered_every_criterion, expect_seeded,
                    expect_read_the_diff, expect_read_only_conduct)
from phases import WIRING as PHASE


def check(ctx, expect):
    rows = verdicts(ctx, expect)
    expect_covered_every_criterion(expect, rows, PHASE["criteria"])
    expect_seeded(expect, rows, PHASE["criteria"], PHASE["seeded_not_met"])
    expect_read_the_diff(expect, ctx)
    expect_read_only_conduct(expect, ctx)
