import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from common import rows_from, expect_covered, expect_seeded, expect_executed, expect_read_only
from plan import SEEDED as PLAN


def check(ctx, expect):
    rows = rows_from(ctx, expect)
    expect_covered(expect, rows, PLAN["criteria"])
    expect_seeded(expect, rows, PLAN)
    expect_executed(expect, ctx, PLAN)
    expect_read_only(expect, ctx)
