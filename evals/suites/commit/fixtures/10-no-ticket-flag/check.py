import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from common import (expect_committed, expect_conventional_subject, expect_explanatory_body,
                    expect_read_staged_diff, subject, TICKET_SHAPE)


def check(ctx, expect):
    msg = expect_committed(ctx, expect)
    expect_conventional_subject(expect, msg)
    expect_explanatory_body(expect, msg)

    # SKILL.md step 2.1 — `--no-ticket` skips inference entirely, so the
    # branch's 123 must appear nowhere in the message.
    expect.absent("no issue-number scope in subject", r"\(#\d+\)", subject(msg))
    expect.absent("no project-key scope in subject", rf"\({TICKET_SHAPE}\)", subject(msg))
    expect.absent("no fabricated issue number", r"#\d+", msg)
    expect.absent("no Ticket: footer", r"^Ticket:", msg, re.M)

    expect_read_staged_diff(expect, ctx)
    expect.info("subject", subject(msg))
