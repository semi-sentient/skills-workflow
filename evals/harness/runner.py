"""Materialise a skill version, run it headless against a fixture, grade it.

An *arm* is a skill version: `worktree` (whatever is on disk now) or any git
ref (`HEAD`, `HEAD~1`, a tag, a SHA). Arms run the same fixtures on the same
machine in the same session, so everything except the skill text is held
constant and a pass-rate difference is attributable to the diff.

Fixture repos are built under a workdir outside this repository — a fixture is
a throwaway git repo the skill is allowed to mutate freely, and it must never
be the repo you are developing in.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .expect import Expect, Result
from .trace import Trace, find_transcript

REPO = Path(__file__).resolve().parent.parent.parent
SUITES = REPO / "evals" / "suites"
DEFAULT_WORKDIR = Path.home() / ".skills-evals"


# --------------------------------------------------------------- fixtures


@dataclass
class Fixture:
    suite: str
    name: str
    root: Path
    meta: dict

    @property
    def skill(self) -> str:
        return self.meta.get("skill", self.suite)

    @property
    def args(self) -> str:
        return self.meta.get("args", "")

    @property
    def timeout_s(self) -> int:
        return int(self.meta.get("timeout_s", 600))

    @property
    def description(self) -> str:
        return self.meta.get("description", "")

    @property
    def expects_no_commit(self) -> bool:
        return bool(self.meta.get("expects_no_commit"))

    @property
    def mode(self) -> str:
        """`single` (one `claude -p`, the default) or `dialogue` (multi-turn
        against a simulated user; see harness/dialogue.py)."""
        return str(self.meta.get("mode", "single"))

    @property
    def companions(self) -> list[str]:
        """Other skills the skill under test may delegate to. Materialised from
        the same arm when that arm has them, skipped silently when it does not —
        so an arm whose skill is a dispatcher ("call the grilling skill") can
        resolve its target, and an arm whose skill is self-contained is not
        penalised for lacking a file it never references."""
        return list(self.meta.get("companions", []))

    @property
    def max_turns(self) -> int:
        return int(self.meta.get("max_turns", 30))

    def module(self, filename: str):
        path = self.root / filename
        if not path.is_file():
            return None
        mod_name = f"fixture_{self.suite}_{self.name}_{Path(filename).stem}".replace("-", "_")
        spec = importlib.util.spec_from_file_location(mod_name, path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod


def discover_fixtures(suite: str | None = None, only: list[str] | None = None) -> list[Fixture]:
    out: list[Fixture] = []
    if not SUITES.is_dir():
        return out
    for suite_dir in sorted(SUITES.iterdir()):
        if not suite_dir.is_dir() or (suite and suite_dir.name != suite):
            continue
        fixtures_dir = suite_dir / "fixtures"
        if not fixtures_dir.is_dir():
            continue
        for fx in sorted(fixtures_dir.iterdir()):
            meta_path = fx / "meta.json"
            if not meta_path.is_file():
                continue
            if only and fx.name not in only:
                continue
            out.append(
                Fixture(suite_dir.name, fx.name, fx, json.loads(meta_path.read_text("utf-8")))
            )
    return out


# ------------------------------------------------------------------- arms


@dataclass
class Arm:
    """A skill version to test. `ref` is 'worktree', any git ref, or
    `path:<dir>` — a directory tree outside this repo (an upstream clone, say)
    searched for `**/<skill>/SKILL.md`. That is how a fork gets benchmarked
    against the skill it forked from without importing it.

    `ablations` deletes spans from the materialised skill before the run:
    a list of (path-relative-to-skill-dir, regex). This answers the question a
    git ref cannot — "is this clause pulling its weight?" — by running the same
    fixtures with one sentence removed. A pattern that matches nothing raises,
    because a no-op ablation would silently produce two identical arms and a
    confident "no difference".
    """

    ref: str
    ablations: list[tuple[str, str]] = field(default_factory=list)

    @property
    def is_path(self) -> bool:
        return self.ref.startswith("path:")

    @property
    def path(self) -> Path:
        return Path(self.ref[len("path:"):]).expanduser().resolve()

    @property
    def label(self) -> str:
        base = f"path:{self.path.name}" if self.is_path else self.ref
        return base if not self.ablations else f"{base}-ablated"

    def resolve(self) -> str:
        base = self._resolve_ref()
        if not self.ablations:
            return base
        return base + " minus " + "; ".join(f"{p}:/{pat[:40]}/" for p, pat in self.ablations)

    def _resolve_ref(self) -> str:
        if self.is_path:
            if not self.path.is_dir():
                raise FileNotFoundError(f"{self.path} is not a directory")
            sha = subprocess.run(
                ["git", "-C", str(self.path), "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True,
            )
            return f"{self.path}" + (f" @ {sha.stdout.strip()}" if sha.returncode == 0 else "")
        if self.ref == "worktree":
            dirty = subprocess.run(
                ["git", "-C", str(REPO), "status", "--porcelain"],
                capture_output=True, text=True,
            ).stdout.strip()
            return "worktree" + (" (dirty)" if dirty else " (clean)")
        sha = subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "--short", self.ref],
            capture_output=True, text=True,
        )
        return f"{self.ref} @ {sha.stdout.strip()}" if sha.returncode == 0 else self.ref

    def has(self, skill: str) -> bool:
        """Whether this arm carries `skill` at all (used for companions)."""
        try:
            if self.is_path:
                self._path_source(skill)
            elif self.ref == "worktree":
                self._worktree_path(skill)
            else:
                self._ref_path(skill)
        except FileNotFoundError:
            return False
        return True

    def materialise(self, skill: str, dest: Path) -> None:
        """Copy this version of `skill` to `dest` (a .../skills/<name>/ dir)."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            shutil.rmtree(dest)

        if self.is_path:
            shutil.copytree(self._path_source(skill), dest, symlinks=False)
        elif self.ref == "worktree":
            src = self._worktree_path(skill)
            # symlinks=False: .agents/skills/ entries are symlinks into universal/,
            # and the fixture must hold real files so the arm cannot drift.
            shutil.copytree(src, dest, symlinks=False)
        else:
            rel = self._ref_path(skill)
            with tempfile.TemporaryDirectory() as tmp:
                archive = Path(tmp) / "skill.tar"
                with archive.open("wb") as fh:
                    proc = subprocess.run(
                        ["git", "-C", str(REPO), "archive", self.ref, "--", rel],
                        stdout=fh, stderr=subprocess.PIPE,
                    )
                if proc.returncode != 0:
                    raise RuntimeError(
                        f"git archive {self.ref} -- {rel} failed: {proc.stderr.decode().strip()}"
                    )
                with tarfile.open(archive) as tar:
                    tar.extractall(tmp, filter="data")
                shutil.copytree(Path(tmp) / rel, dest)

        self._apply_ablations(dest)

    def _apply_ablations(self, dest: Path) -> None:
        for rel, pattern in self.ablations:
            target = dest / rel
            if not target.is_file():
                raise RuntimeError(f"ablation target {rel} not found in this skill version")
            before = target.read_text("utf-8")
            after, n = re.subn(pattern, "", before, flags=re.S)
            if n == 0:
                raise RuntimeError(
                    f"ablation /{pattern}/ matched nothing in {rel} — the arm would be "
                    "identical to the baseline, which would read as 'no difference'"
                )
            target.write_text(after, "utf-8")

    def _path_source(self, skill: str) -> Path:
        """`<skill>/SKILL.md` anywhere under the arm's directory, `.git` and
        hidden dirs excluded. Shortest match wins so `skills/x/grill-me` beats a
        nested copy in a docs or test tree."""
        hits = [
            p.parent for p in self.path.rglob(f"{skill}/SKILL.md")
            if not any(part.startswith(".") for part in p.relative_to(self.path).parts)
        ]
        if not hits:
            raise FileNotFoundError(f"No skill '{skill}' under {self.path}")
        hits.sort(key=lambda p: len(p.parts))
        return hits[0]

    def _worktree_path(self, skill: str) -> Path:
        for domain in sorted(p for p in REPO.iterdir() if p.is_dir() and not p.name.startswith(".")):
            cand = domain / skill
            if (cand / "SKILL.md").is_file():
                return cand
        raise FileNotFoundError(f"No skill '{skill}' in the working tree.")

    def _ref_path(self, skill: str) -> str:
        """Locate the canonical source dir for `skill` at this ref.

        Agent discovery dirs (.agents/skills/, .claude/skills/) hold symlinks
        into the domain folders. `git archive` exports those as symlinks, which
        dangle once extracted in isolation — so the canonical domain copy is the
        only correct source. Hidden dirs are skipped for exactly that reason.
        """
        listing = subprocess.run(
            ["git", "-C", str(REPO), "ls-tree", "-r", "--name-only", self.ref],
            capture_output=True, text=True,
        )
        candidates = [
            line[: -len("/SKILL.md")]
            for line in listing.stdout.splitlines()
            if line.endswith(f"/{skill}/SKILL.md") and not line.startswith(".")
        ]
        if not candidates:
            raise FileNotFoundError(
                f"No non-symlinked skill '{skill}' at ref {self.ref} "
                "(only agent discovery dirs matched, which hold symlinks)."
            )
        candidates.sort(key=lambda p: (not p.startswith("universal/"), len(p)))
        return candidates[0]


# ---------------------------------------------------------------- outcomes


@dataclass
class RunOutcome:
    fixture: Fixture
    arm: str
    rep: int
    repo: Path
    results: list[Result] = field(default_factory=list)
    cost_usd: float = 0.0
    tokens: int = 0
    duration_ms: int = 0
    turns: int = 0
    model: str = ""
    session_id: str = ""
    error: str = ""

    @property
    def graded(self) -> list[Result]:
        return [r for r in self.results if r.graded]

    @property
    def passed(self) -> bool:
        return not self.error and all(r.passed for r in self.graded)

    def to_dict(self) -> dict:
        return {
            "suite": self.fixture.suite,
            "fixture": self.fixture.name,
            "arm": self.arm,
            "rep": self.rep,
            "repo": str(self.repo),
            "cost_usd": self.cost_usd,
            "tokens": self.tokens,
            "duration_ms": self.duration_ms,
            "turns": self.turns,
            "model": self.model,
            "session_id": self.session_id,
            "error": self.error,
            "results": [r.to_dict() for r in self.results],
        }


# ------------------------------------------------------------------ runner


def _outstanding_closers(text: str) -> str:
    """The bracket/quote sequence needed to terminate a truncated JSON value.

    Scans with string and escape awareness, so braces inside evidence strings
    are not mistaken for structure.
    """
    stack: list[str] = []
    in_string = escaped = False
    for ch in text:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if stack and stack[-1] == ch:
                stack.pop()
            else:
                return ""  # unbalanced in a way repair cannot reason about
    return ('"' if in_string else "") + "".join(reversed(stack))


class Context:
    """What a fixture's `check.py` gets to inspect."""

    def __init__(self, fixture: Fixture, repo: Path, payload: dict, trace: Trace, dialogue=None):
        self.fixture = fixture
        self.repo = repo
        self.json = payload
        self.trace = trace
        self.dialogue = dialogue  # harness.dialogue.Dialogue for mode=dialogue, else None
        self.repaired_json = False

    @property
    def result(self) -> str:
        return str(self.json.get("result", ""))

    @property
    def args(self) -> str:
        return self.fixture.args

    def sh(self, command: str) -> str:
        proc = subprocess.run(
            command, shell=True, cwd=self.repo, capture_output=True, text=True
        )
        return proc.stdout.strip()

    def read(self, relpath: str) -> str:
        p = self.repo / relpath
        return p.read_text("utf-8") if p.is_file() else ""

    def exists(self, relpath: str) -> bool:
        return (self.repo / relpath).exists()

    def json_from_result(self, require_key: str | None = None) -> dict | None:
        """Extract the first JSON object in the final message.

        Uses an incremental decoder rather than brace counting: evidence strings
        routinely contain braces (`{ stations: tagged }`), and a naive scan reads
        those as structure and fails on perfectly good output. Models also wrap
        the object in a fence or a sentence of preamble often enough that a
        strict parse would grade the harness instead of the skill.
        """
        text = self.result.strip()
        decoder = json.JSONDecoder()
        for m in re.finditer(r"\{", text):
            try:
                value, _ = decoder.raw_decode(text, m.start())
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict) and (require_key is None or require_key in value):
                return value

        # Last resort: a long single-line object sometimes ends without its
        # closing brackets. Synthesise exactly the closers the scanner says are
        # outstanding and try once more. `self.repaired_json` records that this
        # happened so a format lapse stays visible instead of being papered over
        # — a malformed reply must not silently destroy a recall measurement.
        start = text.find("{")
        if start == -1:
            return None
        closer = _outstanding_closers(text[start:])
        if not closer:
            return None
        try:
            value, _ = decoder.raw_decode(text[start:] + closer)
        except json.JSONDecodeError:
            return None
        if isinstance(value, dict) and (require_key is None or require_key in value):
            self.repaired_json = True
            return value
        return None

    def result_is_bare_json(self) -> bool:
        """Whether the final message is the JSON object alone, with no prose."""
        text = self.result.strip()
        if not text.startswith("{"):
            return False
        try:
            _, end = json.JSONDecoder().raw_decode(text, 0)
        except json.JSONDecodeError:
            return False
        return not text[end:].strip()


class Runner:
    def __init__(
        self,
        workdir: Path = DEFAULT_WORKDIR,
        run_id: str = "run",
        model: str | None = None,
        verbose: bool = False,
    ):
        self.workdir = Path(workdir).expanduser()
        self.run_id = run_id
        self.model = model or os.environ.get("SKILLS_EVAL_MODEL") or None
        self.verbose = verbose
        if REPO in self.workdir.parents or self.workdir == REPO:
            raise ValueError(
                f"workdir {self.workdir} is inside {REPO}. Fixtures are mutated "
                "freely by the skill under test; keep them out of the repo."
            )

    # ------------------------------------------------------------- plumbing

    def run_dir(self, fixture: Fixture, arm: str, rep: int) -> Path:
        safe_arm = arm.replace("/", "-").replace("~", "-")
        return self.workdir / self.run_id / safe_arm / fixture.suite / fixture.name / f"rep{rep}"

    def prepare(self, fixture: Fixture, arm: Arm, rep: int) -> Path:
        repo = self.run_dir(fixture, arm.label, rep)
        if repo.exists():
            shutil.rmtree(repo)
        repo.mkdir(parents=True)

        setup = fixture.root / "setup.sh"
        if setup.is_file():
            proc = subprocess.run(
                ["bash", "-euo", "pipefail", str(setup)],
                cwd=repo, capture_output=True, text=True,
                env={**os.environ, "FIXTURE_DIR": str(fixture.root)},
            )
            if proc.returncode != 0:
                raise RuntimeError(f"setup.sh failed: {proc.stderr.strip()[:600]}")

        arm.materialise(fixture.skill, repo / ".claude" / "skills" / fixture.skill)
        for companion in fixture.companions:
            if arm.has(companion):
                arm.materialise(companion, repo / ".claude" / "skills" / companion)

        settings = repo / ".claude" / "settings.json"
        if not settings.is_file():
            settings.write_text(json.dumps({"permissions": {"deny": ["WebFetch", "WebSearch"]}}), "utf-8")
        return repo

    def prompt_for(self, fixture: Fixture, repo: Path, arm: Arm | None = None) -> str:
        mod = fixture.module("prompt.py")
        if not (mod and hasattr(mod, "prompt")):
            head = f"/{fixture.skill} {fixture.args}".strip()
            plan = fixture.root / "plan.md"
            # A dialogue fixture's opening message is the plan being grilled.
            return f"{head}\n\n{plan.read_text('utf-8').strip()}" if plan.is_file() else head
        # A prompt composed from the skill text is normally strict about finding
        # every block it needs. Under an ablation those blocks are missing on
        # purpose, so tell the composer that omission is the experiment.
        prev = os.environ.get("SKILLS_EVAL_ABLATED")
        if arm is not None and arm.ablations:
            os.environ["SKILLS_EVAL_ABLATED"] = "1"
        else:
            os.environ.pop("SKILLS_EVAL_ABLATED", None)
        try:
            return mod.prompt(repo / ".claude" / "skills" / fixture.skill, repo)
        finally:
            if prev is None:
                os.environ.pop("SKILLS_EVAL_ABLATED", None)
            else:
                os.environ["SKILLS_EVAL_ABLATED"] = prev

    def invoke(
        self, prompt: str, repo: Path, timeout_s: int, resume: str | None = None
    ) -> tuple[dict, str]:
        cmd = [
            "claude", "-p", prompt,
            "--output-format", "json",
            "--setting-sources", "project",
            "--permission-mode", "bypassPermissions",
            # Artifact publishes are an outward side effect; an eval must not produce one.
            "--disallowedTools", "WebSearch", "WebFetch", "Artifact",
        ]
        if resume:
            cmd += ["--resume", resume]
        if self.model:
            cmd += ["--model", self.model]
        try:
            proc = subprocess.run(
                cmd, cwd=repo, capture_output=True, text=True, timeout=timeout_s
            )
        except subprocess.TimeoutExpired:
            return {}, f"timeout after {timeout_s}s"
        if proc.returncode != 0 and not proc.stdout.strip():
            return {}, f"claude exited {proc.returncode}: {proc.stderr.strip()[:400]}"
        try:
            return json.loads(proc.stdout), ""
        except json.JSONDecodeError:
            return {}, f"unparseable output: {proc.stdout.strip()[:300]}"

    # ----------------------------------------------------------------- main

    def run_one(self, fixture: Fixture, arm: Arm, rep: int) -> RunOutcome:
        outcome = RunOutcome(fixture, arm.label, rep, repo=Path("."))
        try:
            repo = self.prepare(fixture, arm, rep)
        except Exception as exc:  # setup is infrastructure, not a skill finding
            outcome.error = f"setup: {exc}"
            return outcome
        outcome.repo = repo

        try:
            prompt = self.prompt_for(fixture, repo, arm)
        except Exception as exc:
            outcome.error = f"prompt: {exc}"
            return outcome
        (repo / ".claude" / "eval-prompt.txt").write_text(prompt, "utf-8")

        dialogue = None
        if fixture.mode == "dialogue":
            from .dialogue import run_dialogue

            dialogue, err = run_dialogue(self, fixture, repo, prompt)
            payload = dialogue.payload if dialogue else {}
        else:
            payload, err = self.invoke(prompt, repo, fixture.timeout_s)
        if err and not payload:
            outcome.error = err
            return outcome

        usage = payload.get("usage") or {}
        outcome.cost_usd = float(payload.get("total_cost_usd") or 0.0)
        outcome.tokens = int(
            (usage.get("input_tokens") or 0)
            + (usage.get("output_tokens") or 0)
            + (usage.get("cache_read_input_tokens") or 0)
            + (usage.get("cache_creation_input_tokens") or 0)
        )
        outcome.duration_ms = int(payload.get("duration_ms") or payload.get("duration_api_ms") or 0)
        outcome.turns = int(payload.get("num_turns") or 0)
        outcome.model = ",".join((payload.get("modelUsage") or {}).keys())
        outcome.session_id = str(payload.get("session_id") or "")

        if payload.get("is_error"):
            outcome.error = f"session error: {str(payload.get('result'))[:300]}"
        elif err:
            # A dialogue that hit its turn cap or lost the simulator still has a
            # gradeable transcript; the cause is recorded, not fatal.
            outcome.error = err

        # Persist the final message. Without it, diagnosing a grading failure
        # means reconstructing the reply from the transcript and hoping the
        # reconstruction matches what was actually graded.
        (repo / ".claude" / "final-message.txt").write_text(
            str(payload.get("result", "")), "utf-8"
        )

        transcript = find_transcript(outcome.session_id, repo) if outcome.session_id else None
        trace = Trace.load(transcript) if transcript else Trace.empty()
        if transcript:
            shutil.copy(transcript, repo / ".claude" / "transcript.jsonl")

        expect = Expect()
        mod = fixture.module("check.py")
        if mod and hasattr(mod, "check"):
            ctx = Context(fixture, repo, payload, trace, dialogue)
            try:
                mod.check(ctx, expect)
            except Exception as exc:
                expect.that("check.py ran", False, f"{type(exc).__name__}: {exc}")
        else:
            expect.that("check.py present", False, "fixture has no check.py")

        expect.info("cost_usd", round(outcome.cost_usd, 4))
        expect.info("turns", outcome.turns)
        if not transcript and outcome.session_id:
            expect.info("transcript", "not found — trajectory assertions were skipped")

        outcome.results = expect.results
        (repo / ".claude" / "outcome.json").write_text(
            json.dumps(outcome.to_dict(), indent=2), "utf-8"
        )
        if self.verbose:
            mark = "pass" if outcome.passed else "FAIL"
            print(f"    [{mark}] {fixture.name} {arm.label} rep{rep} "
                  f"${outcome.cost_usd:.3f}", file=sys.stderr)
        return outcome
