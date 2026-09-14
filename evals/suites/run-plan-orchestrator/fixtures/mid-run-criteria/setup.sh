#!/usr/bin/env bash
# The two-phase-node project with one planted defect that execution is certain to find
# and research is unlikely to (it is plan-internal arithmetic, nothing in HEAD contradicts it):
# Phase 2's test criterion expects a rate of 3.4 against a target of 5 to render
# `[amber]`, but 3.4/5 = 0.68 is below the 0.7 watch factor Phase 1 implements, so the
# correct output is `[red]`. bands.js does not exist when Step 3's research runs; the
# Phase 2 Code agent's own test run, or the reviewer's case-by-case read of C4, is where
# the contradiction surfaces — and if research does flag it early, the persona queues the
# Phase 1 request for the moment Phase 1 commits. The scripted
# human answers "amend" and, in the same breath, asks for a new criterion on committed
# Phase 1 — the shape of the third live run on #6 (EBS Phase 7 C8/C9).
set -euo pipefail
git init -q -b main
git config user.email "fixture@example.com"
git config user.name "Fixture"
git config commit.gpgsign false
printf '.claude/\n' >> "$(git rev-parse --git-path info/exclude)"

cat > package.json <<'JSON'
{
  "name": "board-lines",
  "version": "0.3.0",
  "type": "module",
  "private": true,
  "scripts": {
    "test": "node --test",
    "build": "node --check src/schedule.js"
  }
}
JSON

cat > AGENTS.md <<'MD'
# Project conventions

- ES modules only; named exports only.
- Tests use `node:test` with `node:assert/strict`, one test file per module under `test/`.
- No third-party dependencies.
- Two-space indentation.
- Validation command: `npm test && npm run build`.
- Comments: none that restate the code; a file header only where a maintainer would otherwise make a wrong change.
MD

mkdir -p src test .agents/plans
cat > src/schedule.js <<'JS'
export const DEFAULT_SCHEDULE = {
  windows: [
    { name: 'first', startHour: 6 },
    { name: 'second', startHour: 14 },
    { name: 'third', startHour: 22 },
  ],
};
JS

cat > test/schedule.test.js <<'JS'
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULT_SCHEDULE } from '../src/schedule.js';

test('default schedule has three windows', () => {
  assert.equal(DEFAULT_SCHEDULE.windows.length, 3);
});
JS

cat > .agents/plans/board-lines-plan.md <<'MD'
# Plan: Board Lines

> Source PRD: .agents/plans/board-lines-prd.md

## Architectural decisions

- **Modules**: one module per concern under `src/`; named exports only, no default exports.
- **Banding**: `WATCH_BAND_FACTOR = 0.7` is the single constant for the amber/red boundary; nothing else hardcodes 0.7.
- **Rendering**: `renderBoard` returns a plain string; no DOM, no templates; the rate is rendered as JavaScript renders the number (`5` is `5`, `3.4` is `3.4`).

---

## Phase 1: Rate-band classification

**User stories**: US-1 (colour stations by how they track the shift target)

### What to build

A `src/bands.js` module that classifies a station's throughput rate against the shift target, and a helper that tags a list of stations with their band. Pure functions, no I/O.

### Acceptance criteria

- [ ] `bandForRate(rate, target)` returns `green` whenever the rate is at or above the target; a rate exactly equal to the target is `green`, never `amber`
- [ ] `bandForRate` returns `amber` for a rate exactly equal to `WATCH_BAND_FACTOR` (0.7) x target
- [ ] `bandForRate` returns `red` for any rate below `WATCH_BAND_FACTOR` x target, and a rate of 0 is always `red`
- [ ] `bandForRate` throws a `TypeError` when the rate is not a number
- [ ] `bandsForStations(stations, target)` returns each station with a `band` field added, preserving input order
- [ ] `test/bands.test.js` covers each of: a rate exactly at the target, a rate above the target, a rate exactly at the watch boundary, a rate below it, a zero rate, the `TypeError`, and `bandsForStations` ordering; `npm test` passes

---

## Phase 2: Render the board

**User stories**: US-2 (the shift lead sees one line per station with its band)

### What to build

A `src/board.js` module exporting `renderBoard(stations, target)` that reuses `bandsForStations` from Phase 1 and returns one line per station in input order, formatted `<name>: <rate> [<band>]`, lines joined with `\n`.

### Acceptance criteria

- [ ] `renderBoard(stations, target)` returns one line per station, in input order, each formatted exactly `<name>: <rate> [<band>]`
- [ ] `renderBoard` imports `bandsForStations` from `./bands.js` and does not reimplement banding (`grep -c 'WATCH_BAND_FACTOR' src/board.js` returns 0)
- [ ] `renderBoard([], 5)` returns the empty string
- [ ] `test/board.test.js` covers the ordering, the exact line format, the empty case, that a station at exactly the target renders `[green]`, and that `renderBoard([{ name: 'press', rate: 3.4 }], 5)` returns exactly `press: 3.4 [amber]`; `npm test` passes
MD

git add -A
git commit -q -m "chore: Scaffold board lines"
