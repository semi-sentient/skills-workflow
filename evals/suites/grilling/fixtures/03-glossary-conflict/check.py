import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from common import (expect_asked, expect_challenged, expect_dodge_pressed, expect_no_lookupable_asked,
                    expect_wrapup_structure, has, record_shape)


def check(ctx, expect):
    # Domain-modeling block: challenge against the glossary, sharpen fuzzy terms.
    expect.that("challenged 'cancel' against the glossary", has(ctx, "glossary_challenged:cancellation"),
                f"events: {sorted(set(ctx.dialogue.events))}")
    expect.that("sharpened 'account' to Customer/User", has(ctx, "term_sharpened:account"),
                f"events: {sorted(set(ctx.dialogue.events))}")

    # Inline CONTEXT.md maintenance: the new term landed, the old one kept its meaning.
    context = ctx.read("CONTEXT.md")
    expect.that("CONTEXT.md was updated during the session",
                ctx.sh("git status --porcelain CONTEXT.md") != "", ctx.sh("git status --porcelain CONTEXT.md") or "unchanged")
    expect.match("CONTEXT.md defines the new post-shipment term", r"(?im)^\*\*(Return|Refund)\b", context)
    expect.match("CONTEXT.md keeps Cancellation as pre-fulfilment", r"(?is)\*\*Cancellation\*\*.*?before.*?fulfil", context)
    expect.absent("CONTEXT.md stays free of implementation detail", r"(?i)stripe api|endpoint|middleware|\.js\b", context)

    # ADR gate: sparing. One for the refund path, none for the label.
    adrs = ctx.sh("ls docs/adr 2>/dev/null").split()
    adr_text = ctx.sh("cat docs/adr/* 2>/dev/null")
    refund_adr = re.search(r"(?i)stripe|refund", adr_text) is not None
    expect.that("wrote an ADR for the refund path", has(ctx, "adr_offered:refund_path") or refund_adr,
                f"adrs: {adrs}")
    expect.that("no ADR for the button label",
                not has(ctx, "adr_offered:button_label") and not re.search(r"(?i)button|label|wording", adr_text),
                f"adrs: {adrs}")
    expect.at_most("at most two ADRs written", len(adrs), 2)

    # Interview engine, as in the grill-me fixtures.
    expect_asked(expect, ctx, "window")
    expect_asked(expect, ctx, "stock")
    expect_dodge_pressed(expect, ctx, "partial")
    expect_no_lookupable_asked(expect, ctx)
    expect_challenged(expect, ctx, "ledger_edit", r"revers|new (ledger )?entr|immutable")
    expect_wrapup_structure(expect, ctx)
    record_shape(expect, ctx)
