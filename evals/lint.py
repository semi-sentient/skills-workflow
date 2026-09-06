#!/usr/bin/env python3
"""Tier 0 static gates for the skill corpus.

Free, deterministic checks that run in well under a second. They do not measure
quality — they catch the class of mistake this repo has already made once and
written down. Every rule here traces to a specific past regression or to a
stated guideline in CONTRIBUTING.md.

Usage:
    ./evals/lint.py                 # check every skill
    ./evals/lint.py commit run-plan # check named skills
    ./evals/lint.py --strict        # warnings also fail the run

Exit status: 0 clean (warnings allowed), 1 any error, 1 any warning under
--strict. Errors are structural facts; warnings are heuristics that want a
human to look. A warning is not a bug report — it is a question.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
AGENT_DIRS = (".agents/skills", ".claude/skills")
USER_DOCS = ("README.md", "docs/WORKFLOW_SKILLS.md", "docs/WORKFLOW.md")

MAX_SKILL_LINES = 500  # CONTRIBUTING.md: "Keep SKILL.md under 500 lines."
# The line cap alone let run-plan's SKILL.md reach 102 KB / 16,000 words at 480 lines
# (the lines were paragraphs). SKILL.md is injected verbatim on every invocation and
# re-paid after every compaction, so its size is resident context for the whole run.
# A new mechanism must displace text or live in a trigger-loaded reference.
MAX_SKILL_BYTES = 50_000
MAX_SKILL_WORDS = 7_000

MODEL_NAMES = r"\b(opus|sonnet|haiku|fable)\b"

# Claude-Code-only frontmatter that other harnesses will not understand.
AGENT_SPECIFIC_KEYS = ("allowed-tools", "context", "paths", "disable-model-invocation")

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "than", "that", "this",
    "these", "those", "is", "are", "was", "be", "been", "being", "to", "of",
    "in", "on", "at", "for", "with", "as", "by", "from", "it", "its", "you",
    "your", "we", "our", "they", "their", "not", "never", "always", "do",
    "does", "did", "done", "can", "may", "must", "should", "would", "will",
    "one", "more", "most", "some", "any", "all", "each", "every", "own",
    "same", "so", "up", "out", "off", "over", "under", "again", "once",
    "when", "where", "why", "how", "what", "which", "who", "whom", "into",
}

PERMISSION_WORDS = r"\b(may|can|fine|acceptable|allowed|permitted|ok|okay)\b"


@dataclass
class Finding:
    level: str  # "error" | "warn"
    rule: str
    message: str
    location: str = ""

    def render(self) -> str:
        tag = "ERROR" if self.level == "error" else "warn "
        where = f" {self.location}" if self.location else ""
        return f"  {tag}  [{self.rule}]{where}\n         {self.message}"


@dataclass
class SkillDoc:
    name: str
    domain: str
    root: Path
    skill_md: Path
    text: str
    lines: list[str]
    frontmatter: dict[str, str]
    body: str
    body_offset: int  # line number (1-based) where the body starts
    findings: list[Finding] = field(default_factory=list)

    def err(self, rule: str, message: str, line: int | None = None) -> None:
        self.findings.append(Finding("error", rule, message, self._loc(line)))

    def warn(self, rule: str, message: str, line: int | None = None) -> None:
        if self.suppressed(rule, line):
            return
        self.findings.append(Finding("warn", rule, message, self._loc(line)))

    def suppressed(self, rule: str, line: int | None) -> bool:
        """Honour `<!-- lint-ok: <rule> — why -->` on, or just above, the line.

        A heuristic rule with no way to say "this one is deliberate, here's why"
        becomes permanent noise, and a noisy gate gets ignored wholesale. The
        reason text is required: the comment is the argument for the exception.
        """
        if line is None:
            candidates = self.lines
        else:
            candidates = self.lines[max(0, line - 2) : line]
        for cand in candidates:
            for m in re.finditer(r"<!--\s*lint-ok:\s*([a-z-]+)\s*(.*?)-->", cand):
                if m.group(1) == rule and m.group(2).strip(" —-\t"):
                    return True
        return False

    def _loc(self, line: int | None) -> str:
        try:
            rel: Path | str = self.skill_md.relative_to(REPO)
        except ValueError:
            rel = self.skill_md  # --file may point outside the repo
        return f"{rel}:{line}" if line else str(rel)


# --------------------------------------------------------------- parsing


def parse_frontmatter(text: str) -> tuple[dict[str, str], str, int]:
    """Parse YAML-ish frontmatter without a yaml dependency.

    Handles the two shapes this repo uses: `key: value` and `key: "value"`.
    Values are single-line in every current skill; a continuation line (deeper
    indent) is folded onto the previous key so a wrapped description still
    measures correctly.
    """
    if not text.startswith("---"):
        return {}, text, 1

    lines = text.splitlines()
    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return {}, text, 1

    fm: dict[str, str] = {}
    last_key = None
    for raw in lines[1:end]:
        if not raw.strip():
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw)
        if m and not raw.startswith((" ", "\t")):
            last_key = m.group(1)
            fm[last_key] = m.group(2).strip()
        elif last_key:
            fm[last_key] = (fm[last_key] + " " + raw.strip()).strip()

    for k, v in fm.items():
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            fm[k] = v[1:-1]

    body = "\n".join(lines[end + 1 :])
    return fm, body, end + 2


def load(skill_md: Path, name: str, domain: str) -> SkillDoc:
    text = skill_md.read_text(encoding="utf-8")
    fm, body, offset = parse_frontmatter(text)
    return SkillDoc(
        name=name,
        domain=domain,
        root=skill_md.parent,
        skill_md=skill_md,
        text=text,
        lines=text.splitlines(),
        frontmatter=fm,
        body=body,
        body_offset=offset,
    )


def discover(names: list[str] | None) -> list[SkillDoc]:
    docs: list[SkillDoc] = []
    for domain_dir in sorted(REPO.iterdir()):
        if not domain_dir.is_dir() or domain_dir.name.startswith("."):
            continue
        if domain_dir.name in {"scripts", "docs", "evals"}:
            continue
        for skill_dir in sorted(domain_dir.iterdir()):
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                continue
            if names and skill_dir.name not in names:
                continue
            docs.append(load(skill_md, skill_dir.name, domain_dir.name))
    return docs


# --------------------------------------------------------------- helpers


def code_spans(text: str) -> list[tuple[int, int]]:
    """Character ranges covered by fenced blocks or inline code."""
    spans = [(m.start(), m.end()) for m in re.finditer(r"```.*?```", text, re.S)]
    spans += [(m.start(), m.end()) for m in re.finditer(r"`[^`\n]+`", text)]
    return spans


def in_span(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(a <= pos < b for a, b in spans)


def line_of(text: str, pos: int, offset: int = 1) -> int:
    return text.count("\n", 0, pos) + offset


def salient(words: str) -> set[str]:
    toks = re.findall(r"[a-z][a-z-]{2,}", words.lower())
    return {t for t in toks if t not in STOPWORDS}


def sentences(text: str) -> list[tuple[int, str]]:
    out, pos = [], 0
    for chunk in re.split(r"(?<=[.!?])\s+|\n{2,}", text):
        out.append((pos, chunk))
        pos += len(chunk) + 1
    return out


# --------------------------------------------------------------- rules


def check_frontmatter(d: SkillDoc) -> None:
    if not d.frontmatter:
        d.err("frontmatter", "No parseable YAML frontmatter.")
        return
    name = d.frontmatter.get("name")
    if not name:
        d.err("frontmatter", "Missing required `name`.")
    elif name != d.name:
        d.err(
            "frontmatter",
            f"`name: {name}` does not match directory `{d.name}` — the CLI "
            "discovers skills by frontmatter name, so these must agree.",
        )
    desc = d.frontmatter.get("description")
    if not desc:
        d.err("frontmatter", "Missing required `description` — it is the trigger.")
    # No length rule. A `description-length` warning used to live here, enforcing
    # the "longer than 250 characters may be truncated" line CONTRIBUTING.md
    # carried without a source. Measured with a paired probe (two skills, one
    # 358-char description each, unique trigger token at char 329 vs char 32):
    # both triggered every time on Claude Code 2.1.220 and 2.1.235. Nothing is
    # truncated at 250, so the rule was firing on five of eight skills for no
    # reason — and a gate that cries wolf on most of the corpus gets ignored
    # wholesale, taking its real findings with it. If a hard cap is ever wanted,
    # it should be the documented frontmatter limit, verified first.
    for key in AGENT_SPECIFIC_KEYS:
        if key in d.frontmatter:
            d.warn(
                "agent-specific-frontmatter",
                f"`{key}` is Claude-Code-specific and other harnesses ignore it. "
                "CONTRIBUTING.md asks that the dependency be noted in the description.",
            )


def check_length(d: SkillDoc) -> None:
    """Three caps on SKILL.md: lines, bytes, words. All three are resident-context
    budgets — a line cap alone is passed by writing paragraphs."""
    measures = (
        ("lines", len(d.lines), MAX_SKILL_LINES),
        ("bytes", len(d.text.encode("utf-8")), MAX_SKILL_BYTES),
        ("words", len(d.text.split()), MAX_SKILL_WORDS),
    )
    for unit, n, cap in measures:
        if n > cap:
            d.err(
                "skill-length",
                f"SKILL.md is {n:,} {unit} (>{cap:,}). Move procedure that only some "
                "runs exercise into a trigger-loaded references/ file and point at it.",
            )
        elif n > cap * 0.9:
            d.warn("skill-length", f"SKILL.md is {n:,} {unit} — approaching the {cap:,} cap.")


def check_model_pins(d: SkillDoc) -> None:
    """Sub-agent specs name a role, never a model tier.

    Pinned tiers silently downgrade as newer tiers ship above them, and a
    consumer may not have access to the tier at all.
    """
    spans = code_spans(d.text)
    for m in re.finditer(r"^.*\bmodel\b.*$", d.text, re.M | re.I):
        line = m.group(0)
        if not re.search(MODEL_NAMES, line, re.I):
            continue
        # A prose sentence about inheriting the session model is the fix, not the bug.
        if re.search(r"inherit|never pin|no model pin|do not pin|omit", line, re.I):
            continue
        if in_span(m.start(), spans) and not re.search(r"model\s*[:=]", line, re.I):
            continue
        d.err(
            "model-pin",
            f"Names a model tier next to `model`: {line.strip()[:120]!r}. "
            "Specify subagent_type (the role) and let the agent inherit the session model.",
            line_of(d.text, m.start()),
        )


def check_elastic_permissions(d: SkillDoc) -> None:
    """Affirmative permission gated on a judgment call gets over-invoked.

    Confirmed by the grill-me / grill-with-docs bundling removal: the clause
    "you may bundle ... when they're parameters of the same choice" fired far
    more often than intended, because almost any situation can be framed to
    satisfy it.
    """
    patterns = [
        (r"\bmay\b[^.\n]{0,90}?\bwhen\b", "permission gated on a condition", False),
        (r"\bcan\b[^.\n]{0,60}?\bif (?:it|they|the)\b[^.\n]{0,60}?\b(seem|feel|look|are related|are coupled)",
         "permission gated on a subjective judgement", False),
        # "rarely" only matters when it is hedging a permission the model could
        # take up; "an interface which rarely changes" is description, not a rule.
        (r"\brarely\b(?=[^\n]*\b(?:may|can|could)\b)|\b(?:may|can|could)\b[^\n]{0,60}?\brarely\b",
         "frequency hedge next to an actionable permission", False),
        (r"err on the side of", "soft steer that loses to a concrete nearby permission", False),
        # A permission is granted to an action, and skill prose names actions as
        # gerunds ("bundling ... is fine"). Requiring one in the same line keeps
        # this off descriptive prose like "fail when behavior is fine".
        (r"\bis fine\b", "informal carve-out", True),
        (r"\bwhen in doubt\b[^.\n]{0,40}\b(may|can)\b", "doubt-gated permission", False),
    ]
    spans = code_spans(d.text)
    for pat, why, needs_gerund in patterns:
        for m in re.finditer(pat, d.text, re.I):
            if in_span(m.start(), spans):
                continue
            line_no = line_of(d.text, m.start())
            line = d.lines[line_no - 1]
            if needs_gerund and not re.search(r"\b\w{4,}ing\b", line, re.I):
                continue
            snippet = re.sub(r"\s+", " ", d.text[m.start() : m.start() + 110]).strip()
            d.warn(
                "elastic-permission",
                f"{why}: …{snippet}… — prefer a strict rule with a narrow, "
                "explicitly-named exception that says why the excepted case is safe.",
                line_no,
            )


def check_restated_rules(d: SkillDoc) -> None:
    """A rule and its loophole stated in two places: fixing one leaves the other.

    For each NEVER/ALWAYS bullet, look elsewhere in the document for a sentence
    that shares the bullet's salient vocabulary and also carries a permission
    word. That combination is what the bundling regression looked like.
    """
    bullets = []
    for m in re.finditer(r"^[-*]\s*\**(NEVER|ALWAYS)\**\s*(.*)$", d.text, re.M):
        bullets.append((m.start(), m.group(1), m.group(2)))
    if not bullets:
        return

    sents = sentences(d.text)

    # Document-frequency filter. Words like "agent" or "phase" saturate a long
    # skill file, so a 3-word overlap on them means nothing. Only tokens that
    # are rare in this document carry evidence that two sites discuss one rule.
    df: dict[str, int] = {}
    for _, sent in sents:
        for tok in salient(sent):
            df[tok] = df.get(tok, 0) + 1
    rare = {t for t, n in df.items() if n <= max(3, len(sents) // 40)}

    for pos, kind, rest in bullets:
        keys = salient(rest)
        if len(keys) < 3:
            continue
        bullet_line = line_of(d.text, pos)
        for spos, sent in sents:
            if abs(spos - pos) < 200:
                continue  # the bullet itself, or its immediate neighbours
            if not re.search(PERMISSION_WORDS, sent, re.I):
                continue
            # A sentence that also prohibits is the tightened rule, not a loophole.
            if re.search(r"\b(never|not|no longer|refuse|forbidden|must not|cannot|can't)\b", sent, re.I):
                continue
            overlap = keys & salient(sent)
            if len(overlap) < 3 or not (overlap & rare):
                continue
            d.warn(
                "restated-rule",
                f"`{kind} {rest.strip()[:60]}` (line {bullet_line}) overlaps a "
                f"permissive sentence on line {line_of(d.text, spos)} "
                f"(shared: {', '.join(sorted(overlap)[:4])}). If you tighten one "
                "site, tighten the other — a surviving carve-out wins most of the time.",
                bullet_line,
            )
            break


def check_repo_state_assumptions(d: SkillDoc) -> None:
    """Skills install into repos the author does not control.

    A hardcoded scratch path assumes a .gitignore entry that may not exist —
    that is how run-plan's commit fast path once leaked scratch files into
    review diffs.
    """
    spans = code_spans(d.text)
    for m in re.finditer(r"\.(?:agents|claude)/scratch", d.text):
        line_no = line_of(d.text, m.start())
        line = d.lines[line_no - 1]
        if re.search(r"NEVER hardcode|e\.g\.|for example|in this repo|resolved value|sibling", line, re.I):
            continue
        if in_span(m.start(), spans) and re.search(r"scratch_dir|<scratch", line):
            continue
        d.warn(
            "repo-state-assumption",
            f"Literal scratch path in {line.strip()[:100]!r}. Resolve it at "
            "runtime and self-ignore via .git/info/exclude instead of assuming "
            "the consuming repo's .gitignore.",
            line_no,
        )

    for m in re.finditer(r"^(?![^\n]*(?:info/exclude|never|not|instead of|rather than))[^\n]*\.gitignore[^\n]*$",
                         d.text, re.M | re.I):
        d.warn(
            "repo-state-assumption",
            f"Mentions .gitignore without the info/exclude escape hatch: "
            f"{m.group(0).strip()[:100]!r}",
            line_of(d.text, m.start()),
        )


def check_reference_links(d: SkillDoc) -> None:
    for m in re.finditer(r"\[[^\]]+\]\((references/[^)#]+)\)", d.text):
        target = d.root / m.group(1)
        if not target.is_file():
            d.err(
                "dead-reference",
                f"Links to `{m.group(1)}` which does not exist.",
                line_of(d.text, m.start()),
            )
    for ref in sorted((d.root / "references").glob("*.md")) if (d.root / "references").is_dir() else []:
        rel = f"references/{ref.name}"
        if rel not in d.text:
            d.warn(
                "orphan-reference",
                f"`{rel}` exists but SKILL.md never links to it — progressive "
                "disclosure only works if the entry point points at it.",
            )


def check_registration(d: SkillDoc) -> None:
    """`register-skill.sh` is idempotent, so drift here is always stale state."""
    expected = {p.name for p in d.root.iterdir() if not p.name.startswith(".")}
    for agent_dir in AGENT_DIRS:
        linked = REPO / agent_dir / d.name
        if not linked.is_dir():
            d.err(
                "registration",
                f"Not registered in {agent_dir}/ — the skills CLI will not find it. "
                f"Run ./scripts/register-skill.sh {d.name}",
            )
            continue
        present = {p.name for p in linked.iterdir() if not p.name.startswith(".")}
        for missing in sorted(expected - present):
            d.err(
                "registration",
                f"{agent_dir}/{d.name}/ is missing `{missing}`. "
                f"Run ./scripts/register-skill.sh {d.name}",
            )
        for extra in sorted(present - expected):
            d.err(
                "registration",
                f"{agent_dir}/{d.name}/{extra} is dangling (no source). "
                f"Run ./scripts/register-skill.sh {d.name}",
            )
        for entry in sorted(present & expected):
            link = linked / entry
            if link.is_symlink() and not link.resolve().exists():
                d.err("registration", f"{agent_dir}/{d.name}/{entry} is a broken symlink.")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def skill_scoped_text(doc: str, name: str) -> str:
    """The parts of a user-facing doc that are actually about this skill.

    Two shapes appear in this repo: a heading whose text slugifies to the skill
    name (`## Run Plan` → `run-plan`), and a one-row-per-skill table in the
    README. Anything else is another skill's prose, and matching flags against
    the whole file just reports every skill's flags against every skill.
    """
    chunks: list[str] = []
    parts = re.split(r"^(#{1,6})\s+(.*)$", doc, flags=re.M)
    # parts = [preamble, hashes, heading, body, hashes, heading, body, ...]
    for i in range(1, len(parts) - 2, 3):
        heading, body = parts[i + 1], parts[i + 2]
        if name in slug(heading):
            chunks.append(body)
    for line in doc.splitlines():
        if line.lstrip().startswith("|") and name in line:
            chunks.append(line)
    return "\n".join(chunks)


def check_flag_docs(d: SkillDoc) -> None:
    """A flag the skill accepts but no user-facing doc mentions is undiscoverable.

    The reverse — a doc promising a flag the skill dropped — is worse.
    """
    # Backticks may wrap the flag plus its argument: `--base <branch>`.
    declared = set(re.findall(r"^\s*-\s*`(--[a-z][a-z0-9-]*)[^`]*`", d.body, re.M))
    if not declared:
        return

    scoped: dict[str, str] = {}
    for rel in USER_DOCS:
        p = REPO / rel
        if p.is_file():
            scoped[rel] = skill_scoped_text(p.read_text(encoding="utf-8"), d.name)

    mentioned: set[str] = set()
    for text in scoped.values():
        mentioned |= set(re.findall(r"(--[a-z][a-z0-9-]*)", text))

    for flag in sorted(declared - mentioned):
        d.warn(
            "flag-undocumented",
            f"`{flag}` is accepted but no {d.name} passage in "
            f"{', '.join(USER_DOCS)} mentions it.",
        )

    body_all = set(re.findall(r"`(--[a-z][a-z0-9-]*)[^`]*`", d.body))
    for rel, text in scoped.items():
        for flag in sorted(set(re.findall(r"(--[a-z][a-z0-9-]*)", text)) - body_all):
            d.warn(
                "flag-phantom",
                f"{rel} promises `{flag}` in its {d.name} section but the skill "
                "does not declare it.",
            )


RULES = (
    check_frontmatter,
    check_length,
    check_model_pins,
    check_elastic_permissions,
    check_restated_rules,
    check_repo_state_assumptions,
    check_reference_links,
    check_registration,
    check_flag_docs,
)


# --------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("skills", nargs="*", help="skill names (default: all)")
    ap.add_argument("--strict", action="store_true", help="warnings fail the run too")
    ap.add_argument("--only", help="run a single rule, by name (e.g. model-pin)")
    ap.add_argument(
        "--file",
        help="check one SKILL.md outside the corpus (skips registration and "
        "cross-doc rules). Use for a pre-commit hook or to check an old revision.",
    )
    args = ap.parse_args()

    if args.file:
        p = Path(args.file).resolve()
        if not p.is_file():
            print(f"No such file: {p}", file=sys.stderr)
            return 1
        docs = [load(p, p.parent.name, "file")]
        rules = tuple(r for r in RULES if r not in (check_registration, check_flag_docs))
    else:
        docs = discover(args.skills or None)
        rules = RULES

    if not docs:
        print("No skills found.", file=sys.stderr)
        return 1

    errors = warns = 0
    for d in docs:
        for rule in rules:
            rule(d)
        if args.only:
            d.findings = [f for f in d.findings if f.rule == args.only]

        e = sum(1 for f in d.findings if f.level == "error")
        w = len(d.findings) - e
        errors += e
        warns += w

        status = "clean" if not d.findings else f"{e} error(s), {w} warning(s)"
        print(f"{d.domain}/{d.name}: {status}")
        for f in sorted(d.findings, key=lambda f: (f.level != "error", f.rule)):
            print(f.render())

    print(f"\n{len(docs)} skill(s) — {errors} error(s), {warns} warning(s)")
    if errors:
        return 1
    if warns and args.strict:
        print("--strict: warnings are fatal.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
