#!/usr/bin/env python3
"""Tally what an orchestrator session's context is made of, from its JSONL transcript.

The yardstick behind issue #6. A run-plan orchestrator's resident context is
dominated by its own output — briefs, shell, prose — because every turn re-sends
the whole conversation. This script measures that directly, so a skill change
can be checked against the two runs that motivated it (typescript #71: 716K peak,
48 briefs at 9.2K chars; redshift #154: 532K before its first compaction).

    ./evals/harness/context_tally.py ~/.claude/projects/<slug>/<session>.jsonl
    ./evals/harness/context_tally.py <transcript> --json      # machine-readable

Reports, for the main agent only (sidechains are the sub-agents' own contexts):
  - characters by source: user text (skill injection, compaction summaries),
    assistant prose, each tool's call text and result text
  - sub-agent spawn prompts: count, mean/max chars (pointers after #6, so small)
  - authored briefs: the `rp.sh brief …` commands and `cat > …brief… <<` heredocs
    the orchestrator wrote — the bytes that actually cost context after #6
  - Bash call count, Monitor ticks, compactions
  - peak context per assistant turn: cache_read + cache_creation + input tokens
    at the turn with the largest sum, plus the last turn's figure

`peak_context_tokens` is the number the live-run target is written against
(under 400K on a 9-phase plan; zero compactions).
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

AGENT_TOOLS = {"Task", "Agent"}
RP_BRIEF = re.compile(r'rp\.sh["\']?\s+brief\b')
# A hand-written brief file: `cat > x-brief.md <<EOF`, `cat <<EOF > x-brief.md`, `tee`, `printf … >`.
HEREDOC_BRIEF = re.compile(r"(?:(?:cat|tee|printf|echo)\b[^\n|]*>{1,2}\s*['\"]?\S*brief\S*)|(?:<<-?\s*['\"]?\w+['\"]?\s*>{1,2}\s*['\"]?\S*brief\S*)")


def brief_kind(command: str) -> str | None:
    """'template' for an `rp.sh brief` fill, 'heredoc' for a brief file written by shell, else None.

    Sizes are the whole tool input (command plus description), the bytes the turn
    costs. A shell write to any path containing "brief" counts — an `@file` value
    named `…brief…` would be a false positive; name such files otherwise."""
    if RP_BRIEF.search(command):
        return "template"
    if HEREDOC_BRIEF.search(command):
        return "heredoc"
    return None


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        t = block.get("type")
        if t == "text":
            parts.append(block.get("text", ""))
        elif t == "tool_result":
            inner = block.get("content")
            parts.append(inner if isinstance(inner, str) else _text_of(inner))
    return "\n".join(parts)


def tally(path: Path) -> dict:
    chars: Counter = Counter()
    briefs: list[int] = []
    authored: list[tuple[str, int]] = []
    tool_calls: Counter = Counter()
    turn_context: list[int] = []
    compactions = 0
    assistant_turns = 0
    pending_tool: dict[str, str] = {}  # tool_use_id → tool name, to attribute results

    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("isSidechain"):
                continue
            kind = rec.get("type")
            msg = rec.get("message") or {}
            content = msg.get("content")

            if kind == "user":
                text = _text_of(content) if not isinstance(content, list) else ""
                if isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") == "tool_result":
                            name = pending_tool.pop(block.get("tool_use_id", ""), "unknown")
                            inner = block.get("content")
                            chars[f"tool_result:{name}"] += len(inner if isinstance(inner, str) else _text_of(inner))
                        elif block.get("type") == "text":
                            text += block.get("text", "")
                if "This session is being continued from a previous conversation" in text or rec.get("isCompactSummary"):
                    compactions += 1
                chars["user_text"] += len(text)
                continue

            if kind != "assistant":
                continue
            assistant_turns += 1
            usage = msg.get("usage") or {}
            ctx = int(usage.get("cache_read_input_tokens") or 0) + int(usage.get("cache_creation_input_tokens") or 0) + int(usage.get("input_tokens") or 0)
            if ctx:
                turn_context.append(ctx)
            if isinstance(content, str):
                chars["assistant_text"] += len(content)
                continue
            for block in content or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    chars["assistant_text"] += len(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    name = block.get("name", "")
                    inp = block.get("input") or {}
                    pending_tool[block.get("id", "")] = name
                    tool_calls[name] += 1
                    size = len(json.dumps(inp))
                    chars[f"tool_use:{name}"] += size
                    if name in AGENT_TOOLS:
                        briefs.append(len(str(inp.get("prompt", ""))))
                    elif name == "Bash":
                        kind = brief_kind(str(inp.get("command", "")))
                        if kind:
                            authored.append((kind, size))
                    elif name == "Write" and "brief" in str(inp.get("file_path", "")):
                        authored.append(("heredoc", size))

    total = sum(chars.values()) or 1
    by_source = sorted(chars.items(), key=lambda kv: -kv[1])
    return {
        "transcript": str(path),
        "assistant_turns": assistant_turns,
        "compactions": compactions,
        "tool_calls": dict(tool_calls.most_common()),
        "bash_calls": tool_calls.get("Bash", 0),
        "monitor_ticks": tool_calls.get("Monitor", 0),
        "briefs": {
            "count": len(briefs),
            "mean_chars": round(statistics.mean(briefs)) if briefs else 0,
            "max_chars": max(briefs) if briefs else 0,
            "total_chars": sum(briefs),
        },
        "authored_briefs": {
            "count": len(authored),
            "template": sum(1 for k, _ in authored if k == "template"),
            "heredoc": sum(1 for k, _ in authored if k == "heredoc"),
            "mean_chars": round(statistics.mean(n for _, n in authored)) if authored else 0,
            "max_chars": max((n for _, n in authored), default=0),
            "total_chars": sum(n for _, n in authored),
        },
        "chars_by_source": [{"source": k, "chars": v, "share": round(v / total, 3)} for k, v in by_source],
        "total_chars": total,
        "peak_context_tokens": max(turn_context) if turn_context else 0,
        "final_context_tokens": turn_context[-1] if turn_context else 0,
    }


def render(t: dict) -> str:
    out = [
        f"{t['transcript']}",
        f"turns {t['assistant_turns']}  bash {t['bash_calls']}  monitor {t['monitor_ticks']}  compactions {t['compactions']}",
        f"spawn prompts {t['briefs']['count']}  mean {t['briefs']['mean_chars']:,} chars  max {t['briefs']['max_chars']:,}  total {t['briefs']['total_chars']:,}",
        f"authored briefs {t['authored_briefs']['count']} ({t['authored_briefs']['template']} template, {t['authored_briefs']['heredoc']} heredoc)"
        f"  mean {t['authored_briefs']['mean_chars']:,} chars  max {t['authored_briefs']['max_chars']:,}  total {t['authored_briefs']['total_chars']:,}",
        f"peak context {t['peak_context_tokens']:,} tokens  (final turn {t['final_context_tokens']:,})",
        "",
        f"{'source':<28}{'chars':>12}{'share':>8}",
    ]
    for row in t["chars_by_source"][:14]:
        out.append(f"{row['source']:<28}{row['chars']:>12,}{row['share']:>8.1%}")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("transcript", type=Path)
    ap.add_argument("--json", action="store_true", help="emit the tally as JSON")
    args = ap.parse_args()
    if not args.transcript.is_file():
        print(f"no such file: {args.transcript}", file=sys.stderr)
        return 1
    t = tally(args.transcript)
    print(json.dumps(t, indent=2) if args.json else render(t))
    return 0


if __name__ == "__main__":
    sys.exit(main())
