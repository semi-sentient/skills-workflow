import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from common import expect_committed, expect_conventional_subject, expect_explanatory_body


def check(ctx, expect):
    msg = expect_committed(ctx, expect)
    expect_conventional_subject(expect, msg)
    expect_explanatory_body(expect, msg)

    # SKILL.md item 5: only ever describe files staged for commit.
    for token in ("refund", "chargeback", "gateway", "payment"):
        expect.absent(f"message does not mention unstaged work ({token})", token, msg, re.I)

    expect.that("the unstaged file was not staged or committed",
                "refund-gateway.js" not in ctx.sh("git show --name-only --format= HEAD"),
                f"committed files: {ctx.sh('git show --name-only --format= HEAD')}")
    expect.that("the unstaged file still exists untracked",
                ctx.exists("src/payments/refund-gateway.js"),
                "left in place")
    expect.info("subject", msg.splitlines()[0] if msg else "")
