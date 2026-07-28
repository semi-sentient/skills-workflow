import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from common import commit_count, expect_read_staged_diff


def check(ctx, expect):
    expect.equals("no commit was created", commit_count(ctx), 1)
    expect.that("did not run git commit",
                not ctx.trace.ran_git(r"commit\b"),
                f"bash calls: {ctx.trace.bash_commands()[:8]}")
    expect.that("did not stage anything on the user's behalf",
                ctx.sh("git diff --cached --name-only") == "",
                f"staged: {ctx.sh('git diff --cached --name-only')!r}")
    expect.that("unstaged work left untouched",
                "voidEntry" in ctx.read("src/ledger.js"),
                "src/ledger.js modification survived")

    expect_read_staged_diff(expect, ctx)
    expect.match("told the user to stage first", r"git add|stage", ctx.result, re.I)
    expect.info("final message", ctx.result[:200])
