"""The plan draft under review, with its criteria and the seeded defect set.

Both fixtures share one repo and one plan body; only the acceptance criteria
differ. The seeded variant carries exactly five defective criteria, one per
sub-check of prd-to-plan's Step 6b "Criteria verifiability" item, each written
so that EXECUTING the criterion's command (not reading it) is what exposes the
defect. The clean variant replaces each with a criterion that is discriminating
today and satisfiable by a correct implementation.

`seeded_flags` is derived from the defects before any run is read; grading
against it measures recall (each defective criterion is flagged) and precision
(no sound criterion is flagged). `seeded_subcheck` records which sub-check
family each defect belongs to, graded by family for the executable class
(vacuous / cannot-pass / non-portable are one reviewer judgement apart) and
exactly for the other two.

Host note: criterion 3 (seeded) uses `stat -c`, which BSD/macOS `stat` rejects
(`illegal option -- c`) while GNU `stat` accepts. On a GNU host the command
succeeds and the "non-portable" defect is invisible to execution — the suite is
calibrated on macOS, where this repo's evals run.
"""

from __future__ import annotations

import sys

PHASE_HEADER = """# Plan: Rate-band classification

> Source PRD: (none attached — this is a single-phase plan; treat PRD coverage
> and i18n completeness as not applicable)

## Architectural decisions

- Banding is a pure function in `src/bands.js`; no I/O, no DOM there.
- `WATCH_BAND_FACTOR = 0.7` is exported from `src/bands.js` and referenced inside
  `bandForRate` for the amber boundary — one constant, two uses.
- `src/board.js` is a new module that imports `bandsForStations` from
  `./bands.js` and `DEFAULT_SCHEDULE` from `./schedule.js`, and exports
  `renderBoard(stations, target)` returning an HTML string with one
  `<li>` per station carrying an inline `style` background colour per band
  (green/amber/red — no stylesheet exists or is needed). `src/main.js` (new) mounts it into the
  existing `index.html`'s `#board` element, so the coloured board is loadable in
  a browser via `npm run serve`. The demo station set is built in `src/main.js`
  from `DEFAULT_SCHEDULE.windows` — one station per window, named after it, with
  `rate: 0` — rendered at `target = 1`, so the board shows exactly three `<li>`
  entries, all in the red band, until real data exists.

---

## Phase 1: Rate-band classification

**Known risk**: human action — the coloured board can only be checked in a browser.

### What to build

Create `src/bands.js` exporting `WATCH_BAND_FACTOR` (0.7), `bandForRate(rate,
target)` and `bandsForStations(stations, target)`. `bandForRate` returns `green`
at or above target, `amber` at or above `WATCH_BAND_FACTOR` x target, `red`
below, and throws `TypeError` for a non-numeric rate; it references the exported
`WATCH_BAND_FACTOR` constant for the amber boundary. Create `src/board.js`
importing `bandsForStations` from `./bands.js` and `DEFAULT_SCHEDULE` from
`./schedule.js` (which exists: it exports the three shift windows) and exporting
`renderBoard`; create `src/main.js` to mount the rendered list into `#board` in
the existing `index.html`. Add `test/bands.test.js` using `node:test` with one
`test(...)` per behaviour, covering at least: a rate exactly at target, a rate
above target, a rate exactly at the watch boundary, a rate below it, a zero
rate, the `TypeError`, and `bandsForStations` ordering (seven tests). Do not
touch `src/schedule.js` or `index.html`.

### Acceptance criteria
"""

_C = {
    "fn_exists": "`grep -c 'export function bandForRate' src/bands.js` returns 1 (run from the repo root)",
    # seeded 1 — vacuous: schedule.js is never touched by this phase, so 0 today and 0 after.
    "vacuous": "`grep -c 'bandForRate' src/schedule.js` returns 0 (run from the repo root)",
    # clean 1 — board.js does not exist yet, so this fails today and passes after.
    "board_import": "`grep -c \"from './bands.js'\" src/board.js` returns 1 (run from the repo root)",
    # seeded 2 — cannot pass: the decisions mandate the constant be exported AND referenced, so >= 2 lines.
    "factor_exactly_one": "`grep -c 'WATCH_BAND_FACTOR' src/bands.js` returns exactly 1 (run from the repo root)",
    "factor_at_least_two": "`grep -c 'WATCH_BAND_FACTOR' src/bands.js` returns at least 2 (run from the repo root)",
    # seeded 3 — non-portable: BSD stat has no -c.
    "stat_gnu": "`stat -c %s src/bands.js` reports fewer than 2000 bytes (run from the repo root)",
    "throws": "`grep -c 'throw new TypeError' src/bands.js` returns at least 1 (run from the repo root)",
    # seeded 4 — evidence location the reviewer cannot read.
    "progress_note": "The `npm test` pass/fail summary line is pasted into the progress note",
    "test_import": "`grep -c \"from '../src/bands.js'\" test/bands.test.js` returns 1 (run from the repo root)",
    # seeded 5 — human-only, unlabelled, in a Known-risk phase.
    "browser_unlabelled": "Run `npm run serve`, load the board in a browser, and confirm each station is coloured by its band",
    "browser_labelled": "Human confirms each station is coloured by its band in the browser under `npm run serve`",
    "tests_count": "`grep -c \"^test('\" test/bands.test.js` returns at least 7 (run from the repo root)",
    "at_target_green": "`bandForRate(2.5, 2.5)` returns `green` — exactly at target is green, never amber",
    "commit_body": "The phase commit body records the `npm test` result: the reporter's pass and fail counts quoted as printed, with a fail count of 0",
    "human_preview": "Human verifies the `#board` list shows one `<li>` per station, coloured by band, in the browser",
}

SEEDED = {
    "criteria": [
        _C["fn_exists"],            # 0
        _C["vacuous"],              # 1 seeded
        _C["factor_exactly_one"],   # 2 seeded
        _C["stat_gnu"],             # 3 seeded
        _C["progress_note"],        # 4 seeded
        _C["browser_unlabelled"],   # 5 seeded
        _C["tests_count"],          # 6
        _C["at_target_green"],      # 7
        _C["commit_body"],          # 8
        _C["human_preview"],        # 9
    ],
    "seeded_flags": [1, 2, 3, 4, 5],
    "seeded_subcheck": {1: "executable", 2: "executable", 3: "executable",
                        4: "evidence-location", 5: "actor"},
    # Commands the reviewer must EXECUTE; graded by distinctive substring in the trace.
    "commands": ["src/schedule.js", "WATCH_BAND_FACTOR", "stat -c", "export function bandForRate", "test('"],
}

CLEAN = {
    "criteria": [
        _C["fn_exists"],
        _C["board_import"],
        _C["factor_at_least_two"],
        _C["throws"],
        _C["test_import"],
        _C["browser_labelled"],
        _C["tests_count"],
        _C["at_target_green"],
        _C["commit_body"],
        _C["human_preview"],
    ],
    "seeded_flags": [],
    "seeded_subcheck": {},
    "commands": ["src/board.js", "WATCH_BAND_FACTOR", "throw new TypeError", "export function bandForRate", "test('"],
}

VARIANTS = {"seeded": SEEDED, "clean": CLEAN}


def render(variant: str) -> str:
    body = "\n".join(f"- [ ] {c}" for c in VARIANTS[variant]["criteria"])
    return PHASE_HEADER + body + "\n"


if __name__ == "__main__":
    sys.stdout.write(render(sys.argv[1]))
