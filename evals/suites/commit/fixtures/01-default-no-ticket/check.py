import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from common import (expect_committed, expect_conventional_subject, expect_explanatory_body,
                    expect_read_staged_diff, expect_checked_message_rules, subject, TICKET_SHAPE)


def check(ctx, expect):
    msg = expect_committed(ctx, expect)
    expect_conventional_subject(expect, msg)
    expect_explanatory_body(expect, msg)

    # No ticket was passed, so nothing ticket-shaped may appear anywhere.
    expect.absent("no ticket scope in subject", rf"\({TICKET_SHAPE}\)", subject(msg))
    expect.absent("no Ticket: footer", r"^Ticket:", msg, re.M)

    expect_read_staged_diff(expect, ctx)
    expect_checked_message_rules(expect, ctx)
    expect.info("subject", subject(msg))
