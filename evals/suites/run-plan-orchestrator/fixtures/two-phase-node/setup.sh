#!/usr/bin/env bash
# A tiny ES-module Node project with one committed module, plus a two-phase plan
# in the shape prd-to-plan writes. Local-only (no remote), so run-plan takes the
# --no-github path: branch, two reviewed phase commits, final summary, no PR.
set -euo pipefail
git init -q -b main
git config user.email "fixture@example.com"
git config user.name "Fixture"
git config commit.gpgsign false
printf '.claude/\n' >> "$(git rev-parse --git-path info/exclude)"

cat > package.json <<'JSON'
{
  "name": "shift-board",
  "version": "0.3.0",
  "type": "module",
  "private": true,
  "scripts": {
    "test": "node --test",
    "build": "node --check src/schedule.js && node --check src/bands.js 2>/dev/null || node --check src/schedule.js"
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

cat > .agents/plans/shift-board-plan.md <<'MD'
# Plan: Shift Board Bands

> Source PRD: .agents/plans/shift-board-prd.md

## Architectural decisions

- **Modules**: one module per concern under `src/`; named exports only, no default exports.
- **Banding**: `WATCH_BAND_FACTOR = 0.7` is the single constant for the amber/red boundary; nothing else hardcodes 0.7.
- **Rendering**: `renderBoard` returns a plain string; no DOM, no templates.

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
- [ ] `test/board.test.js` covers the ordering, the exact line format, the empty case, and that a station at exactly the target renders `[green]`; `npm test` passes
MD

git add -A
git commit -q -m "chore: Scaffold shift board"
