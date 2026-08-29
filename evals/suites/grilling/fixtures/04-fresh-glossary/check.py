import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from common import (events, expect_asked, expect_challenged, expect_dodge_pressed,
                    expect_no_lookupable_asked, expect_wrapup_structure, has, record_shape)


def check(ctx, expect):
    expect.that("separated Invoice from Statement", has(ctx, "term_sharpened:invoice"),
                f"events: {sorted(set(events(ctx)))}")

    # Lazy creation: CONTEXT.md exists because a term was resolved, and holds it.
    context = ctx.read("CONTEXT.md")
    expect.that("CONTEXT.md was created", ctx.exists("CONTEXT.md"), "present" if context else "absent")
    expect.match("CONTEXT.md defines Invoice", r"(?im)^\*\*Invoice\b", context)
    expect.match("CONTEXT.md defines Statement", r"(?im)^\*\*Statement\b", context)
    expect.absent("CONTEXT.md stays free of implementation detail",
                  r"(?i)cron|02:00|pdfkit|puppeteer|\.js\b|s3\b|object storage", context)

    # ADR gate: nothing here clears all three criteria.
    adrs = ctx.sh("ls docs/adr 2>/dev/null").split()
    offered = sorted(e for e in events(ctx) if e.startswith("adr_offered:"))
    expect.that("no ADR offered for reversible decisions", not offered, f"offered: {offered}")
    expect.equals("no ADR files written", len(adrs), 0)

    expect_asked(expect, ctx, "schedule")
    expect_asked(expect, ctx, "storage")
    expect_asked(expect, ctx, "currency")
    expect_dodge_pressed(expect, ctx, "email_failure")
    expect_no_lookupable_asked(expect, ctx)
    expect_challenged(expect, ctx, "numbering", r"INV-|per[- ]customer|sequen")
    expect_wrapup_structure(expect, ctx)
    record_shape(expect, ctx)
