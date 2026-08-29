import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from common import (expect_asked, expect_challenged, expect_contradiction, expect_dodge_pressed,
                    expect_no_lookupable_asked, expect_not_silently_decided,
                    expect_wrapup_structure, record_shape)


def check(ctx, expect):
    expect_asked(expect, ctx, "access_ttl")
    expect_asked(expect, ctx, "logout")
    expect_asked(expect, ctx, "key_rotation")
    expect_asked(expect, ctx, "webhook_auth")
    expect_contradiction(expect, ctx, "session_store")
    expect_dodge_pressed(expect, ctx, "refresh")
    expect_no_lookupable_asked(expect, ctx)

    expect_challenged(expect, ctx, "storage", r"httponly|http-only|cookie")
    expect_not_silently_decided(expect, ctx, "claims", r"\bsub\b|\bcid\b|claims?")
    expect_wrapup_structure(expect, ctx)

    record_shape(expect, ctx)
