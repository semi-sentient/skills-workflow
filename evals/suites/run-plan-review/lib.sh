# Fixture scaffolding for the `run-plan-review` suite.
#
# Each fixture builds the same base project and plan, then stages EITHER a
# correct implementation (`clean`) or one carrying a single deliberate defect
# (`seeded`). Pairing them is what makes the suite meaningful: the seeded arm
# measures recall, the clean arm measures false-positive rate, and a change that
# buys recall by making the reviewer paranoid shows up immediately as clean-arm
# noise.

init_repo() {
  git init -q
  git config user.email "fixture@example.com"
  git config user.name "Fixture"
  git config commit.gpgsign false
  printf '.claude/\n' >> "$(git rev-parse --git-path info/exclude)"

  cat > package.json <<'EOF'
{
  "name": "shift-board",
  "version": "0.3.0",
  "type": "module",
  "private": true,
  "scripts": {
    "test": "node --test",
    "build": "node --check src/schedule.js"
  }
}
EOF

  cat > AGENTS.md <<'EOF'
# Project conventions

- ES modules only; named exports only.
- Tests use `node:test` with `node:assert/strict`.
- No third-party dependencies.
- Two-space indentation.
- Validation command: `npm test && npm run build`.
EOF

  mkdir -p src test
  cat > src/schedule.js <<'EOF'
export const DEFAULT_SCHEDULE = {
  windows: [
    { name: 'first', startHour: 6 },
    { name: 'second', startHour: 14 },
    { name: 'third', startHour: 22 },
  ],
};
EOF

  cat > test/schedule.test.js <<'EOF'
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULT_SCHEDULE } from '../src/schedule.js';

test('default schedule has three windows', () => {
  assert.equal(DEFAULT_SCHEDULE.windows.length, 3);
});
EOF

  git add -A
  git commit -q -m "chore: Scaffold shift board"
}

# ---------------------------------------------------------------- phase 1

# Correct implementation of the rate-band phase.
stage_bands_clean() {
  cat > src/bands.js <<'EOF'
export const WATCH_BAND_FACTOR = 0.7;

/**
 * Classify a throughput rate against its target.
 * At exactly the target the operator is on plan, so the band is green.
 */
export function bandForRate(rate, target) {
  if (typeof rate !== 'number' || Number.isNaN(rate)) {
    throw new TypeError('rate must be a number');
  }
  if (rate >= target) return 'green';
  if (rate >= target * WATCH_BAND_FACTOR) return 'amber';
  return 'red';
}

export function bandsForStations(stations, target) {
  return stations.map((s) => ({ ...s, band: bandForRate(s.rate, target) }));
}
EOF

  cat > test/bands.test.js <<'EOF'
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { bandForRate, bandsForStations, WATCH_BAND_FACTOR } from '../src/bands.js';

test('exactly at target is green', () => {
  assert.equal(bandForRate(2.5, 2.5), 'green');
});

test('above target is green', () => {
  assert.equal(bandForRate(3, 2.5), 'green');
});

test('exactly at the watch boundary is amber', () => {
  assert.equal(bandForRate(2.5 * WATCH_BAND_FACTOR, 2.5), 'amber');
});

test('below the watch boundary is red', () => {
  assert.equal(bandForRate(1, 2.5), 'red');
});

test('a zero rate is red', () => {
  assert.equal(bandForRate(0, 2.5), 'red');
});

test('rejects a non-numeric rate', () => {
  assert.throws(() => bandForRate('fast', 2.5), TypeError);
});

test('bandsForStations tags every station', () => {
  const out = bandsForStations([{ id: 'a', rate: 3 }, { id: 'b', rate: 0 }], 2.5);
  assert.deepEqual(out.map((s) => s.band), ['green', 'red']);
});
EOF
  git add -A
}

# Seeded: strict `>` at the target boundary. Acceptance criterion 1 states
# explicitly that exactly-at-target is green, so this is NOT MET — and the test
# was written to match the buggy code, so `npm test` passes and the reviewer
# cannot lean on a red suite. Reading the criterion against the code is the only
# way to find it, which is precisely what the gate is for.
#
# The variant is written out in full rather than patched. A seeded fixture is
# only worth anything if the defect is exactly one known thing, and a regex that
# silently fails to apply leaves you grading a different bug than you think.
stage_bands_seeded() {
  stage_bands_clean
  cat > src/bands.js <<'EOF'
export const WATCH_BAND_FACTOR = 0.7;

/**
 * Classify a throughput rate against its target.
 */
export function bandForRate(rate, target) {
  if (typeof rate !== 'number' || Number.isNaN(rate)) {
    throw new TypeError('rate must be a number');
  }
  if (rate > target) return 'green';
  if (rate >= target * WATCH_BAND_FACTOR) return 'amber';
  return 'red';
}

export function bandsForStations(stations, target) {
  return stations.map((s) => ({ ...s, band: bandForRate(s.rate, target) }));
}
EOF

  cat > test/bands.test.js <<'EOF'
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { bandForRate, bandsForStations, WATCH_BAND_FACTOR } from '../src/bands.js';

test('exactly at target is amber', () => {
  assert.equal(bandForRate(2.5, 2.5), 'amber');
});

test('above target is green', () => {
  assert.equal(bandForRate(3, 2.5), 'green');
});

test('exactly at the watch boundary is amber', () => {
  assert.equal(bandForRate(2.5 * WATCH_BAND_FACTOR, 2.5), 'amber');
});

test('below the watch boundary is red', () => {
  assert.equal(bandForRate(1, 2.5), 'red');
});

test('a zero rate is red', () => {
  assert.equal(bandForRate(0, 2.5), 'red');
});

test('rejects a non-numeric rate', () => {
  assert.throws(() => bandForRate('fast', 2.5), TypeError);
});

test('bandsForStations tags every station', () => {
  const out = bandsForStations([{ id: 'a', rate: 3 }, { id: 'b', rate: 0 }], 2.5);
  assert.deepEqual(out.map((s) => s.band), ['green', 'red']);
});
EOF
  git add -A
}

# ---------------------------------------------------------------- phase 2

# Correct implementation of the unmapped-worker strip phase.
stage_wiring_clean() {
  cat > src/unmapped.js <<'EOF'
/** Workers with no station assignment, surfaced so drift is visible. */
export function collectUnmapped(workers, stations) {
  const assigned = new Set(stations.map((s) => s.workerName));
  return workers.filter((w) => !assigned.has(w.name));
}

export function renderUnmappedStrip(unmapped) {
  if (unmapped.length === 0) return '';
  return `unassigned: ${unmapped.map((w) => w.name).join(', ')}`;
}
EOF

  cat > src/board.js <<'EOF'
import { bandsForStations } from './bands.js';
import { collectUnmapped, renderUnmappedStrip } from './unmapped.js';

export function renderBoard({ workers, stations, target }) {
  const tagged = bandsForStations(stations, target);
  const unmapped = collectUnmapped(workers, stations);
  return {
    stations: tagged,
    unmappedStrip: renderUnmappedStrip(unmapped),
  };
}
EOF

  cat > test/unmapped.test.js <<'EOF'
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { collectUnmapped, renderUnmappedStrip } from '../src/unmapped.js';
import { renderBoard } from '../src/board.js';

test('collects workers with no station', () => {
  const out = collectUnmapped(
    [{ name: 'ana' }, { name: 'bo' }],
    [{ workerName: 'ana' }],
  );
  assert.deepEqual(out.map((w) => w.name), ['bo']);
});

test('renders nothing when everyone is assigned', () => {
  assert.equal(renderUnmappedStrip([]), '');
});

test('renders the unassigned names', () => {
  assert.equal(renderUnmappedStrip([{ name: 'bo' }]), 'unassigned: bo');
});

test('the board surfaces the unmapped strip', () => {
  const board = renderBoard({
    workers: [{ name: 'ana' }, { name: 'bo' }],
    stations: [{ id: 's1', workerName: 'ana', rate: 3 }],
    target: 2.5,
  });
  assert.equal(board.unmappedStrip, 'unassigned: bo');
});
EOF
  git add -A
}

# Seeded: the strip is built and unit-tested but the board never renders it —
# the exact shape of defect the July-2026 benchmark caught in production
# (a component fully tested in isolation, never mounted). Its own unit tests
# still pass, so only a criterion-by-criterion read finds it.
stage_wiring_seeded() {
  stage_wiring_clean
  cat > src/board.js <<'EOF'
import { bandsForStations } from './bands.js';

export function renderBoard({ workers, stations, target }) {
  const tagged = bandsForStations(stations, target);
  return {
    stations: tagged,
  };
}
EOF

  # The board-level test goes with it. That is the realistic shape of this bug:
  # the unit is covered in isolation and nothing exercises the integration, so
  # `npm test` is green and the phase reaches the review gate looking finished.
  # A seeded fixture whose test suite fails would never get that far, and would
  # be measuring the build gate rather than the reviewer.
  cat > test/unmapped.test.js <<'EOF'
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { collectUnmapped, renderUnmappedStrip } from '../src/unmapped.js';

test('collects workers with no station', () => {
  const out = collectUnmapped(
    [{ name: 'ana' }, { name: 'bo' }],
    [{ workerName: 'ana' }],
  );
  assert.deepEqual(out.map((w) => w.name), ['bo']);
});

test('renders nothing when everyone is assigned', () => {
  assert.equal(renderUnmappedStrip([]), '');
});

test('renders the unassigned names', () => {
  assert.equal(renderUnmappedStrip([{ name: 'bo' }]), 'unassigned: bo');
});
EOF
  git add -A
}

# The bands phase is a prerequisite for the wiring phase; commit it so the
# wiring fixture's staged diff contains only the phase under review.
commit_bands_as_prior_phase() {
  stage_bands_clean
  git commit -q -m "feat: Add rate-band classification"
}
