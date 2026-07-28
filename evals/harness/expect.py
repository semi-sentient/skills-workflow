"""Assertion collector handed to each fixture's `check.py`.

Assertions are deterministic by design: a regex, a file state, a tool-call
ordering. Nothing here asks a model to judge anything, so a failure is a fact
about the run rather than a second opinion that itself needs replicating.

Every assertion carries `evidence` — the actual observed value. When a fixture
flips between arms, the evidence string is what tells you why without reopening
the transcript.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Result:
    name: str
    passed: bool
    evidence: str = ""
    graded: bool = True  # False → recorded for context, never gates

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "evidence": self.evidence,
            "graded": self.graded,
        }


@dataclass
class Expect:
    results: list[Result] = field(default_factory=list)

    # ---------------------------------------------------------------- core

    def that(self, name: str, ok: bool, evidence: str = "") -> bool:
        self.results.append(Result(name, bool(ok), _trim(evidence)))
        return bool(ok)

    def info(self, name: str, value: object) -> None:
        """Record an observation without grading it.

        Use for numbers you want in the report but have no defensible
        threshold for yet — token counts, turn counts, message length.
        """
        self.results.append(Result(name, True, _trim(str(value)), graded=False))

    # ------------------------------------------------------------- strings

    def match(self, name: str, pattern: str, text: str, flags: int = 0) -> bool:
        m = re.search(pattern, text or "", flags)
        return self.that(
            name,
            m is not None,
            f"matched {m.group(0)!r}" if m else f"no match for {pattern!r} in {_trim(text, 200)!r}",
        )

    def absent(self, name: str, pattern: str, text: str, flags: int = 0) -> bool:
        m = re.search(pattern, text or "", flags)
        return self.that(
            name,
            m is None,
            f"unexpectedly found {m.group(0)!r}" if m else "absent, as required",
        )

    def contains(self, name: str, needle: str, text: str) -> bool:
        return self.that(
            name,
            needle in (text or ""),
            f"found {needle!r}" if needle in (text or "") else f"missing {needle!r}",
        )

    def equals(self, name: str, actual: object, expected: object) -> bool:
        return self.that(name, actual == expected, f"actual={actual!r} expected={expected!r}")

    # -------------------------------------------------------------- counts

    def at_most(self, name: str, actual: float, limit: float) -> bool:
        return self.that(name, actual <= limit, f"{actual} (limit {limit})")

    def at_least(self, name: str, actual: float, floor: float) -> bool:
        return self.that(name, actual >= floor, f"{actual} (floor {floor})")

    # ------------------------------------------------------------ summary

    @property
    def graded_results(self) -> list[Result]:
        return [r for r in self.results if r.graded]

    @property
    def ok(self) -> bool:
        return all(r.passed for r in self.graded_results)


def _trim(text: str, limit: int = 400) -> str:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"
