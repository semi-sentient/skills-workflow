import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from common import (expect_committed, expect_explanatory_body, expect_read_staged_diff,
                    subject, TYPE_RE)


def check(ctx, expect):
    msg = expect_committed(ctx, expect)
    subj = subject(msg)

    expect.match("subject carries the ticket as a scope",
                 rf"^({TYPE_RE})\(SALES-456\): [A-Z]", subj)
    expect_explanatory_body(expect, msg)

    lines = [l for l in msg.splitlines() if l.strip()]
    expect.that("Ticket: footer is the final line",
                bool(lines) and lines[-1].strip() == "Ticket: SALES-456",
                f"last line: {lines[-1].strip() if lines else '<empty>'!r}")

    # commitlint's footer-leading-blank warns without the separating blank line.
    raw = msg.rstrip().splitlines()
    idx = next((i for i, l in enumerate(raw) if l.strip().startswith("Ticket:")), None)
    expect.that("blank line precedes the Ticket: footer",
                idx is not None and idx > 0 and raw[idx - 1].strip() == "",
                f"line before footer: {raw[idx - 1]!r}" if idx else "no footer found")

    expect.equals("ticket appears exactly once as a footer",
                  len(re.findall(r"^Ticket:", msg, re.M)), 1)
    expect_read_staged_diff(expect, ctx)
    expect.info("subject", subj)
