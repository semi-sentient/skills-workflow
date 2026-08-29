import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from common import (expect_asked, expect_challenged, expect_contradiction, expect_dodge_pressed,
                    expect_no_lookupable_asked, expect_not_silently_decided,
                    expect_wrapup_structure, record_shape)


def check(ctx, expect):
    # Recall — the walk found what was planted.
    expect_asked(expect, ctx, "retry_after")
    expect_asked(expect, ctx, "response_body")
    expect_asked(expect, ctx, "unauth_keying")
    expect_asked(expect, ctx, "per_route_config")
    expect_contradiction(expect, ctx, "public_routes")
    expect_dodge_pressed(expect, ctx, "webhooks")
    expect_no_lookupable_asked(expect, ctx)

    # Rigour — the fork's additions.
    # Any shared store is the corrected answer; the persona offers Redis but a
    # further probe can legitimately land on Postgres.
    expect_challenged(expect, ctx, "store", r"redis|postgres|shared (store|state|counter)")
    expect_not_silently_decided(expect, ctx, "response_body", r"retryAfterSeconds|\"error\"|body")
    expect_wrapup_structure(expect, ctx)

    record_shape(expect, ctx)
