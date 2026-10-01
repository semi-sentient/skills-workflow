#!/usr/bin/env bash
# A one-phase Node plan whose commit a pre-commit hook rejects: every staged src/*.js
# must open with an SPDX line, and nothing the Code agent reads says so (AGENTS.md is
# silent, no existing file carries the line, and no criterion names a command, so Step 3
# has no reason to read the hook).
# The fast-path `git commit -F` fails, a hook-fix Debug agent adds the header — a code
# change after the message file was authored — and the commit must then go through the
# commit skill. C5 is a timing criterion no read-only reviewer can verify: NEEDS-RUNTIME,
# carried with rp.sh carry.
set -euo pipefail
git init -q -b main
git config user.email "fixture@example.com"
git config user.name "Fixture"
git config commit.gpgsign false
git config core.hooksPath .git/hooks  # a global hooksPath would bypass the hook below
printf '.claude/\n' >> "$(git rev-parse --git-path info/exclude)"

cat > package.json <<'JSON'
{
  "name": "shift-bands",
  "version": "0.3.0",
  "type": "module",
  "private": true,
  "scripts": {
    "test": "node --test"
  }
}
JSON

cat > AGENTS.md <<'MD'
# Project conventions

- ES modules only; named exports only.
- Tests use `node:test` with `node:assert/strict`, one test file per module under `test/`.
- No third-party dependencies.
- Two-space indentation.
- Validation command: `npm test`.
MD

mkdir -p src test .agents/plans
cat > src/schedule.js <<'JS'
export const DEFAULT_TARGET = 5;
JS

cat > test/schedule.test.js <<'JS'
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULT_TARGET } from '../src/schedule.js';

test('default target is five', () => {
  assert.equal(DEFAULT_TARGET, 5);
});
JS

cat > .agents/plans/shift-bands-plan.md <<'MD'
# Plan: Shift Bands

> Source PRD: .agents/plans/shift-bands-prd.md

## Architectural decisions

- **Modules**: one module per concern under `src/`; named exports only.
- **Banding**: `WATCH_BAND_FACTOR = 0.7` is the single constant for the amber/red boundary.

---

## Phase 1: Rate-band classification

**User stories**: US-1 (colour stations by how they track the shift target)

### What to build

A `src/bands.js` module that classifies a station's throughput rate against the shift target, and a helper that tags a list of stations with their band. Pure functions, no I/O.

### Acceptance criteria

- [ ] `bandForRate(rate, target)` returns `green` for a rate at or above the target, `amber` for a rate at or above `WATCH_BAND_FACTOR` (0.7) x target, and `red` below that
- [ ] `bandForRate` throws a `TypeError` when the rate is not a number
- [ ] `bandsForStations(stations, target)` returns each station with a `band` field added, preserving input order
- [ ] Tests cover the three bands, the exact watch boundary, the `TypeError`, and `bandsForStations` ordering
- [ ] On the production kiosk hardware, `bandsForStations` over 100,000 stations completes in under 50 ms
MD

git add -A
git commit -q -m "chore: Scaffold shift bands"

cat > .git/hooks/pre-commit <<'HOOK'
#!/bin/sh
status=0
for f in $(git diff --cached --name-only --diff-filter=ACMR -- 'src/*.js'); do
  if [ "$(head -n 1 "$f")" != "// SPDX-License-Identifier: MIT" ]; then
    echo "pre-commit: $f: the first line must be '// SPDX-License-Identifier: MIT'" >&2
    status=1
  fi
done
exit $status
HOOK
chmod +x .git/hooks/pre-commit
