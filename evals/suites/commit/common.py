"""Shared assertions for the `commit` suite.

Each helper checks one clause of the skill's stated contract, so a failure
points at a specific line of SKILL.md rather than "the message looked off".
"""

from __future__ import annotations

import re

CONVENTIONAL_TYPES = ("feat", "fix", "refactor", "test", "docs", "chore", "style", "perf", "build", "ci")
TYPE_RE = "|".join(CONVENTIONAL_TYPES)
TICKET_SHAPE = r"[A-Z][A-Z0-9]+-\d+"


def message(ctx) -> str:
    """The HEAD commit message, or '' when nothing was committed."""
    return ctx.sh("git log -1 --format=%B")


def commit_count(ctx) -> int:
    out = ctx.sh("git rev-list --count HEAD")
    return int(out) if out.isdigit() else 0


def subject(msg: str) -> str:
    return msg.splitlines()[0] if msg.strip() else ""


def body(msg: str) -> str:
    lines = msg.splitlines()
    return "\n".join(lines[1:]).strip()


def bullets(msg: str) -> list[str]:
    return [l.strip() for l in msg.splitlines() if re.match(r"^\s*[-*]\s+\S", l)]


def expect_committed(ctx, expect) -> str:
    """Assert a commit landed; return its message."""
    created = commit_count(ctx) > 1
    expect.that("a commit was created", created, f"{commit_count(ctx)} commit(s) on HEAD")
    msg = message(ctx) if created else ""
    expect.that("staged changes were committed",
                created and ctx.sh("git diff --cached --name-only") == "",
                f"still staged: {ctx.sh('git diff --cached --name-only') or 'nothing'}")
    return msg


def expect_conventional_subject(expect, msg: str, *, sentence_case: bool = True) -> None:
    subj = subject(msg)
    expect.match("subject is Conventional Commits",
                 rf"^({TYPE_RE})(\([^)]*\))?!?: .+", subj)
    if sentence_case:
        expect.match("subject description is Sentence-case",
                     rf"^({TYPE_RE})(\([^)]*\))?!?: [A-Z]", subj)


def expect_explanatory_body(expect, msg: str, *, min_bullets: int = 2) -> None:
    """SKILL.md 4.4-4.5: a context paragraph, then a bullet per unit of work."""
    b = body(msg)
    bs = bullets(msg)
    prose = [
        l for l in b.splitlines()
        if l.strip() and not re.match(r"^\s*[-*]\s+", l) and not re.match(r"^\w[\w-]*:\s", l)
    ]
    expect.at_least("body has a context paragraph", len(prose), 1)
    expect.at_least(f"body has >={min_bullets} bullets", len(bs), min_bullets)
    expect.absent("bullets are not raw file paths",
                  r"^\s*[-*]\s+(src|test|lib)/\S+\.(js|ts|tsx|py)\s*$", b, re.M)


def expect_read_staged_diff(expect, ctx) -> None:
    """SKILL.md step 1 — the skill starts from `git diff --cached`."""
    expect.that(
        "inspected the staged diff",
        ctx.trace.ran_git(r"diff\s+(--cached|--staged)"),
        f"bash calls: {ctx.trace.bash_commands()[:6]}",
    )


def expect_checked_message_rules(expect, ctx, *, pattern: str = r"commitlint|\.husky|commit-msg|CONTRIBUTING|\.gitmessage") -> None:
    """SKILL.md step 2 — detect repo message rules before writing anything."""
    looked = ctx.trace.ran(pattern) or any(
        re.search(pattern, p, re.I) for p in ctx.trace.reads()
    ) or any(
        re.search(pattern, str(c.input), re.I)
        for c in ctx.trace.tool_calls("Grep") + ctx.trace.tool_calls("Glob")
    )
    expect.that("looked for repo commit-message rules", looked,
                f"reads={ctx.trace.reads()[:5]} bash={ctx.trace.bash_commands()[:5]}")
