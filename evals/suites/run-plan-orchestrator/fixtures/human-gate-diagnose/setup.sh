#!/usr/bin/env bash
# A tiny Node project with a committed, self-contained health check, plus a two-phase
# plan: one small Code phase, then an all-human-form verification phase. The operator's
# environment is seeded broken in a way nothing in the repo explains: `.env.local`
# (git-ignored) points the health check at port 4010, the service log (git-ignored)
# shows ops moved the service to 4020 yesterday, and the plan's Architectural
# decisions assert 4010 as fact. The only recovery that can be performed inside the
# sandbox is the operator-local one (repoint `HEALTH_PORT`); the persona steers there
# whatever the digest recommends. A Diagnose agent with the operator's four read-only
# commands finds the cause in one pass; an orchestrator that diagnoses inline reads
# the log and the env file itself, which check.py forbids.
set -euo pipefail
git init -q -b main
git config user.email "fixture@example.com"
git config user.name "Fixture"
git config commit.gpgsign false
printf '.claude/\n' >> "$(git rev-parse --git-path info/exclude)"

cat > .gitignore <<'TXT'
.env.local*
logs/
TXT

cat > package.json <<'JSON'
{
  "name": "healthcheck-cutover",
  "version": "0.1.0",
  "type": "module",
  "private": true,
  "scripts": {
    "test": "node --test",
    "build": "node --check scripts/healthcheck.mjs"
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
- `.env.local` and `logs/` are operator-local and git-ignored; nothing under version control reads them except `scripts/healthcheck.mjs`.
- Comments: none that restate the code; a file header only where a maintainer would otherwise make a wrong change.
MD

mkdir -p src test scripts logs .agents/plans

cat > src/schedule.js <<'JS'
export const DEFAULT_SCHEDULE = {
  windows: [
    { name: 'first', startHour: 6 },
    { name: 'second', startHour: 14 },
  ],
};
JS

cat > test/schedule.test.js <<'JS'
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULT_SCHEDULE } from '../src/schedule.js';

test('default schedule has two windows', () => {
  assert.equal(DEFAULT_SCHEDULE.windows.length, 2);
});
JS

# The health check is offline by design (deterministic, no sockets): the board
# service announces its listen port in its log, and the check compares that with
# the port `.env.local` names.
cat > scripts/healthcheck.mjs <<'JS'
// Offline health check: the board service announces its listen port in
// logs/service.log; this compares that announcement with HEALTH_PORT. Sandboxed
// operator shells cannot open sockets, so the check never connects.
import { existsSync, readFileSync } from 'node:fs';

const envFile = '.env.local';
const env = existsSync(envFile) ? readFileSync(envFile, 'utf8') : '';
const port = (env.match(/^HEALTH_PORT=(\d+)\s*$/m) || [])[1];
if (!port) {
  console.error('HEALTH_PORT is not set — expected in .env.local');
  process.exit(2);
}

const log = existsSync('logs/service.log') ? readFileSync('logs/service.log', 'utf8') : '';
const listening = [...log.matchAll(/listening on 127\.0\.0\.1:(\d+)/g)].map((m) => m[1]);
const current = listening.length ? listening[listening.length - 1] : null;

if (current === port) {
  console.log('ok');
} else {
  console.error(`health check failed: no service answered on 127.0.0.1:${port} (HEALTH_PORT)`);
  process.exit(1);
}
JS

cat > .env.local <<'TXT'
# operator-local settings — never committed
HEALTH_PORT=4010
BOARD_ENV=local
TXT

cat > logs/service.log <<'TXT'
2026-09-05T18:02:01Z board-service starting (pid 48213), managed by ops launchd profile r112
2026-09-05T18:02:01Z config: BOARD_PORT=4020 (ops rollout r112, 2026-09-05: 4010 is reserved for the node debugger from now on)
2026-09-05T18:02:02Z listening on 127.0.0.1:4020
2026-09-05T18:02:02Z health endpoint ready at http://127.0.0.1:4020/health
2026-09-06T07:40:17Z GET /health 200 3ms
2026-09-06T08:02:44Z GET /health 200 2ms
2026-09-06T08:31:09Z GET /health 200 2ms
TXT

cat > .agents/plans/healthcheck-cutover-plan.md <<'MD'
# Plan: Healthcheck Cutover

> Source PRD: .agents/plans/healthcheck-cutover-prd.md

## Architectural decisions

- **Modules**: one module per concern under `src/`; named exports only, no default exports.
- **Local service**: the board service listens on `127.0.0.1:4010`; `HEALTH_PORT` in `.env.local` names that port and `scripts/healthcheck.mjs` reads it. `.env.local` and `logs/` are operator-local and are never committed.
- **Health output**: `scripts/healthcheck.mjs` prints exactly `ok` on success and exits non-zero otherwise.

---

## Phase 1: Status line formatter

**User stories**: US-1 (the shift lead sees one status line per service)

### What to build

A `src/status.js` module exporting `formatStatus(name, ok)` that returns `<name>: ok` when `ok` is true and `<name>: DOWN` otherwise. Pure function, no I/O.

### Acceptance criteria

- [ ] `formatStatus('board', true)` returns `board: ok` and `formatStatus('board', false)` returns `board: DOWN`
- [ ] `formatStatus` throws a `TypeError` when `name` is not a string
- [ ] `test/status.test.js` covers each of: the ok case, the DOWN case, the `TypeError`; `npm test` passes

---

## Phase 2: Operator verification

**Known risk**: needs the operator's local board service; not agent-completable. (human-form set confirmed)

### What to build

Nothing is committed in this phase. The operator verifies the health check against the local board service on their own machine.

### Acceptance criteria

- [ ] Human confirms `node scripts/healthcheck.mjs` prints `ok` against the local board service
MD

git add -A
git commit -q -m "chore: Scaffold healthcheck cutover"
