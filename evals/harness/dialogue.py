"""Drive a multi-turn skill against a simulated user.

An interview skill cannot be graded from one `claude -p` call: its whole
contract is about what it does with the *answers*. So the skill under test runs
as a resumable session, and a second, tool-less `claude -p` session plays the
user from a fixture-supplied `persona.md` — a hidden ground truth with planted
defects (a contradiction with the code, a term used two ways, a "figure it out
later" dodge, a decision with a known flaw). The simulator is scripted, not
judging: it answers what it is asked and reports *events* from a vocabulary the
persona fixes ("dodge_pressed:webhooks", "challenged:store"), and `check.py`
grades those events plus the final wrap-up plus the trajectory.

Every interviewer turn is one `claude -p --resume`, so the interviewer's
transcript is a single session JSONL and `Trace` works on it unchanged.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

SIM_SYSTEM = """You are role-playing a software developer being interviewed about a plan. Stay in character throughout. The persona below is your hidden ground truth: what you know, what you have decided, and how you react. Follow its reaction rules exactly, including the ones that tell you to be evasive or to hold a flawed position until a specific kind of pushback.

Rules:
- Answer only what the interviewer actually asked. Do not volunteer hidden facts, do not answer questions that were not asked, do not summarise your persona.
- If the interviewer asks several numbered questions, answer each by number, briefly.
- If asked for a fact the persona marks as "in the repo", say you don't remember and that it's in the codebase; do not make one up.
- Keep replies short and conversational. No headings.
- When the interviewer presents a final summary / wrap-up, or asks you to confirm shared understanding, and asks nothing new: confirm briefly and set "done": true.
- Never ask for or accept follow-on work: no implementation, no documents, no artifacts, no "write it up". If offered, decline in one clause and confirm.

Reply with a single JSON object and nothing else:
{"reply": "<what you say to the interviewer>", "events": ["<event>", ...], "done": false}

"events" is bookkeeping for the evaluator and is as important as the reply. Before writing the reply, scan the interviewer's turn against EVERY event in the persona's vocabulary and list each one whose trigger occurs in THIS turn. Use only the exact event strings defined there. Empty list when none apply. An "asked:<topic>" event fires the first time the interviewer raises that decision, whether as a question, a numbered item, or a recommendation you are asked to accept.
"""


def _vocabulary(persona: str) -> str:
    """The persona's '# Event vocabulary' section, re-sent every turn.

    Without the reminder the simulator's event reporting decays over a long
    session: in the first smoke run it emitted events on turn 1 and on almost
    nothing after, while the interviewer visibly hit five planted triggers.
    """
    m = re.search(r"(?ms)^#+\s*Event vocabulary.*", persona)
    return m.group(0).strip() if m else ""


@dataclass
class Turn:
    role: str  # "interviewer" | "user"
    text: str
    events: list[str] = field(default_factory=list)
    cost_usd: float = 0.0
    done: bool = False  # user turn that confirmed the wrap-up


@dataclass
class Dialogue:
    turns: list[Turn] = field(default_factory=list)
    payload: dict = field(default_factory=dict)  # aggregate, shaped like a single-run payload
    sim_cost_usd: float = 0.0
    stop_reason: str = ""

    @property
    def interviewer_turns(self) -> list[str]:
        return [t.text for t in self.turns if t.role == "interviewer"]

    @property
    def events(self) -> list[str]:
        return [e for t in self.turns if t.role == "user" for e in t.events]

    def has_event(self, name: str) -> bool:
        return name in self.events

    @property
    def final(self) -> str:
        it = self.interviewer_turns
        return it[-1] if it else ""

    @property
    def wrapup(self) -> str:
        """The interviewer turn the user confirmed — the wrap-up itself, not
        whatever pleasantries followed the confirmation. Falls back to the
        final turn when the session never closed."""
        for i, t in enumerate(self.turns):
            if t.role == "user" and t.done and i > 0:
                return self.turns[i - 1].text
        return self.final

    def to_dict(self) -> dict:
        return {
            "stop_reason": self.stop_reason,
            "sim_cost_usd": round(self.sim_cost_usd, 4),
            "turns": [
                {"role": t.role, "text": t.text, "events": t.events, "cost_usd": round(t.cost_usd, 4), "done": t.done}
                for t in self.turns
            ],
        }


def _first_json(text: str) -> dict | None:
    decoder = json.JSONDecoder()
    for m in re.finditer(r"\{", text):
        try:
            value, _ = decoder.raw_decode(text, m.start())
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "reply" in value:
            return value
    return None


class Simulator:
    """A tool-less `claude -p` session playing the user."""

    def __init__(self, persona: str, home: Path, model: str | None, timeout_s: int):
        self.persona = persona
        self.home = home
        self.model = model
        self.timeout_s = timeout_s
        self.session_id: str | None = None
        self.cost_usd = 0.0
        home.mkdir(parents=True, exist_ok=True)
        # Nothing project-level may leak into the simulator's context.
        (home / ".claude").mkdir(exist_ok=True)
        (home / ".claude" / "settings.json").write_text(json.dumps({"permissions": {"deny": ["*"]}}), "utf-8")

    def respond(self, interviewer_text: str) -> tuple[str, list[str], bool, str]:
        prompt = f"The interviewer says:\n\n{interviewer_text}"
        vocab = _vocabulary(self.persona)
        if vocab:
            prompt += f"\n\n---\nReminder — check this turn against every event:\n\n{vocab}"
        cmd = [
            "claude", "-p", prompt,
            "--output-format", "json",
            "--setting-sources", "project",
            "--tools", "",
            "--system-prompt", SIM_SYSTEM + "\n\n--- PERSONA ---\n\n" + self.persona,
        ]
        if self.session_id:
            cmd += ["--resume", self.session_id]
        if self.model:
            cmd += ["--model", self.model]
        try:
            proc = subprocess.run(cmd, cwd=self.home, capture_output=True, text=True, timeout=self.timeout_s)
        except subprocess.TimeoutExpired:
            return "", [], False, f"simulator timeout after {self.timeout_s}s"
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return "", [], False, f"simulator unparseable: {proc.stdout.strip()[:200] or proc.stderr.strip()[:200]}"
        self.session_id = payload.get("session_id") or self.session_id
        self.cost_usd += float(payload.get("total_cost_usd") or 0.0)
        if payload.get("is_error"):
            return "", [], False, f"simulator error: {str(payload.get('result'))[:200]}"
        raw = str(payload.get("result", ""))
        obj = _first_json(raw)
        if obj is None:
            # Treat the whole text as the reply rather than abort the interview
            # over a formatting slip; the slip is visible in dialogue.json.
            return raw.strip(), [], False, ""
        events = [str(e) for e in obj.get("events") or [] if isinstance(e, (str, int))]
        done = bool(obj.get("done"))
        # A turn that still carries a numbered/marked question is not a wrap-up,
        # whatever the simulator says: in the v1 baseline it confirmed on "Q17"
        # rounds, which then graded as the closing summary.
        if done and re.search(r"❓|\*\*Q\d+\b|Question \d+", interviewer_text):
            done = False
        return str(obj.get("reply", "")).strip(), events, done, ""


def run_dialogue(runner, fixture, repo: Path, opening: str) -> tuple[Dialogue | None, str]:
    persona_path = fixture.root / "persona.md"
    if not persona_path.is_file():
        return None, "dialogue fixture has no persona.md"
    persona = persona_path.read_text("utf-8")

    per_call = int(fixture.meta.get("call_timeout_s", 420))
    sim = Simulator(
        persona,
        home=repo / ".claude" / "simulator",
        model=fixture.meta.get("sim_model") or os.environ.get("SKILLS_EVAL_SIM_MODEL") or None,
        timeout_s=per_call,
    )
    dlg = Dialogue()
    agg: dict = {"total_cost_usd": 0.0, "usage": {}, "duration_ms": 0, "num_turns": 0, "modelUsage": {}}
    session_id: str | None = None
    err = ""

    def call_interviewer(text: str) -> dict | None:
        nonlocal session_id, err
        payload, e = runner.invoke(text, repo, per_call, resume=session_id)
        if e:
            err = e
            return None
        session_id = payload.get("session_id") or session_id
        agg["total_cost_usd"] += float(payload.get("total_cost_usd") or 0.0)
        for k, v in (payload.get("usage") or {}).items():
            if isinstance(v, (int, float)):
                agg["usage"][k] = agg["usage"].get(k, 0) + v
        agg["duration_ms"] += int(payload.get("duration_ms") or 0)
        agg["num_turns"] += int(payload.get("num_turns") or 0)
        for k in (payload.get("modelUsage") or {}):
            agg["modelUsage"][k] = True
        if payload.get("is_error"):
            err = f"session error: {str(payload.get('result'))[:300]}"
            return None
        dlg.turns.append(Turn("interviewer", str(payload.get("result", "")), cost_usd=float(payload.get("total_cost_usd") or 0.0)))
        return payload

    def persist() -> None:
        dlg.sim_cost_usd = sim.cost_usd
        (repo / ".claude" / "dialogue.json").write_text(json.dumps(dlg.to_dict(), indent=2), "utf-8")

    if call_interviewer(opening) is None:
        dlg.stop_reason = err
        persist()
        return dlg, err

    for _ in range(fixture.max_turns):
        reply, events, done, sim_err = sim.respond(dlg.final)
        if sim_err:
            dlg.stop_reason = sim_err
            persist()
            return dlg, sim_err
        dlg.turns.append(Turn("user", reply, events, done=done))
        persist()  # after every exchange, so a hung or capped run can be read mid-flight
        if call_interviewer(reply) is None:
            dlg.stop_reason = err
            persist()
            return dlg, err
        if done:
            dlg.stop_reason = "user confirmed"
            break
    else:
        dlg.stop_reason = f"turn cap ({fixture.max_turns}) reached"
        err = dlg.stop_reason

    agg["session_id"] = session_id
    agg["result"] = dlg.final
    agg["num_interviewer_turns"] = len(dlg.interviewer_turns)
    dlg.payload = agg
    persist()
    return dlg, err
