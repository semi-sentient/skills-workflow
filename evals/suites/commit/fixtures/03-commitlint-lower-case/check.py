import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from common import (expect_committed, expect_explanatory_body, expect_read_staged_diff,
                    expect_checked_message_rules, subject, TYPE_RE)


def check(ctx, expect):
    msg = expect_committed(ctx, expect)
    subj = subject(msg)

    expect.match("subject is Conventional Commits", rf"^({TYPE_RE})(\([^)]*\))?!?: .+", subj)
    # The whole point of the fixture: the repo's rule overrides the skill default.
    expect.match("subject description is lower-case (repo rule, not the default)",
                 rf"^({TYPE_RE})(\([^)]*\))?!?: [a-z]", subj)
    expect.absent("no trailing full stop (subject-full-stop)", r"\.\s*$", subj)
    expect_explanatory_body(expect, msg)
    expect_checked_message_rules(expect, ctx, pattern=r"commitlint")
    expect_read_staged_diff(expect, ctx)
    expect.info("subject", subj)
