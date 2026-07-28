import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from common import (expect_committed, expect_read_staged_diff, expect_checked_message_rules,
                    subject)


def check(ctx, expect):
    msg = expect_committed(ctx, expect)
    subj = subject(msg)

    expect.match("type is within the declared type-enum", r"^(feat|fix)\(", subj)
    expect.at_most("header within header-max-length 60", len(subj), 60)
    expect.match("scope is present (scope-empty: never)", r"^(feat|fix)\([^)]+\):", subj)
    expect.match("subject description is Sentence-case", r": [A-Z]", subj)
    expect_checked_message_rules(expect, ctx, pattern=r"commitlintrc|commitlint")
    expect_read_staged_diff(expect, ctx)
    expect.info("subject", subj)
    expect.info("header length", len(subj))
