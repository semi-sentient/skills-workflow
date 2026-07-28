"""Phase text, manifests, and the expected verdict set for each seeded variant.

Both members of a pair MUST receive an identical brief — the staged code is the
only thing allowed to differ, or the comparison measures the prompt instead of
the reviewer.

`seeded_not_met` is the set of criteria a seeded variant genuinely breaks,
derived from the defect before looking at any run output. Grading against it
measures two things at once: recall (each broken criterion is caught) and
precision (no intact criterion is failed). Writing this set down is also what
forces each criterion to be unambiguous — an earlier draft put the amber band's
upper boundary in a second criterion, so the boundary defect broke two criteria
and "correct" was not well defined.
"""

BANDS = {
    "phase": """## Phase 2: Rate-band classification

Classify each station's throughput rate against the shift target so the board
can colour stations by how they are tracking.""",
    "criteria": [
        # 0 — broken by the seeded strict `>`.
        "`bandForRate(rate, target)` returns `green` whenever the rate is at or above the target; a rate exactly equal to the target is `green`, never `amber`",
        # 1 — a fixed interior point of the watch band, unaffected by the target boundary.
        "`bandForRate` returns `amber` for a rate exactly equal to `WATCH_BAND_FACTOR` (0.7) x target",
        # 2
        "`bandForRate` returns `red` for any rate below `WATCH_BAND_FACTOR` x target, and a rate of 0 is always `red`",
        # 3
        "`bandForRate` throws a `TypeError` when the rate is not a number",
        # 4
        "`bandsForStations(stations, target)` returns each station with a `band` field added, preserving input order",
        # 5 — broken: the seeded test asserts amber at exactly-target.
        "Tests cover each of: a rate exactly at the target, a rate above the target, a rate exactly at the watch boundary, a rate below it, a zero rate, the `TypeError`, and `bandsForStations` ordering",
    ],
    "manifest": ["src/bands.js", "test/bands.test.js"],
    "pointers": [
        "`src/schedule.js` exports `DEFAULT_SCHEDULE` — window definitions only, not needed here.",
    ],
    "seeded_not_met": [0, 5],
}

WIRING = {
    "phase": """## Phase 3: Surface unmapped workers

Workers with no station assignment currently vanish from the board. Collect them
and render them as a strip beneath the station grid so assignment drift is
visible to the shift lead.""",
    "criteria": [
        # 0
        "`collectUnmapped(workers, stations)` returns the workers whose `name` matches no station's `workerName`",
        # 1
        "`renderUnmappedStrip(unmapped)` returns an empty string when nobody is unassigned, and a comma-joined `unassigned: ...` line otherwise",
        # 2 — broken: renderBoard never calls it.
        "`renderBoard` includes the rendered unmapped strip in the board it returns, so unmapped workers actually reach the rendered output",
        # 3 — broken: the board-level test was removed with it.
        "Tests cover collection, the empty case, the rendered case, and that `renderBoard` surfaces the strip",
    ],
    "manifest": ["src/unmapped.js", "src/board.js", "test/unmapped.test.js"],
    "pointers": [
        "`src/bands.js` (phase 2) exports `bandsForStations(stations, target)` — reuse it, do not reimplement banding.",
    ],
    "seeded_not_met": [2, 3],
}
