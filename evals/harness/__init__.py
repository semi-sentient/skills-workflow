"""Tier 1 behavioural-fixture harness for the skill corpus.

The unit under test is a skill *version*. An arm materialises one version into
a throwaway fixture repo, runs it headless, and grades deterministic assertions
against the artifacts it produced and the trajectory it took to get there.

Two arms over the same fixtures is the whole point: confounds (model version,
harness build, machine) cancel, so a difference in pass rates is attributable
to the skill diff.
"""

from .expect import Expect, Result
from .trace import Trace
from .runner import Arm, Fixture, RunOutcome, Runner, discover_fixtures
from .report import Report, compare

__all__ = [
    "Arm",
    "Expect",
    "Fixture",
    "Report",
    "Result",
    "RunOutcome",
    "Runner",
    "Trace",
    "compare",
    "discover_fixtures",
]
