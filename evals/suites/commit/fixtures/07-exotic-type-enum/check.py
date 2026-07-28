import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from common import expect_committed, expect_explanatory_body, expect_read_staged_diff, subject


def check(ctx, expect):
    msg = expect_committed(ctx, expect)
    subj = subject(msg)

    # The decisive assertion: these types exist nowhere but this repo's config.
    expect.match("type comes from the project's own type-enum",
                 r"^(deliver|repair|tidy): ", subj)
    expect.absent("did not fall back to a standard Conventional type",
                  r"^(feat|fix|chore|refactor|docs|test|style|perf|build|ci)\b", subj)
    # subject-case upper-case, and scope-empty: always → no scope permitted.
    expect.match("subject description is UPPER-CASE per the repo rule",
                 r"^[a-z]+: [^a-z]*$", subj)
    expect.absent("no scope (scope-empty: always)", r"^[a-z]+\([^)]*\):", subj)
    expect.at_most("header within header-max-length 72", len(subj), 72)

    expect_explanatory_body(expect, msg)
    expect.that("read the package.json that carries the rules",
                any("package.json" in p for p in ctx.trace.reads())
                or ctx.trace.ran(r"package\.json")
                or any("package.json" in str(c.input) for c in ctx.trace.tool_calls("Grep")),
                f"reads={ctx.trace.reads()[:6]} bash={ctx.trace.bash_commands()[:4]}")
    expect_read_staged_diff(expect, ctx)
    expect.info("subject", subj)
