# Shared fixture scaffolding for the `commit` suite.
# Sourced by each fixture's setup.sh, which runs with cwd = a fresh empty dir.

init_repo() {
  git init -q
  git config user.email "fixture@example.com"
  git config user.name "Fixture"
  git config commit.gpgsign false

  # The harness materialises the skill under test into .claude/ AFTER setup.
  # Excluding it locally keeps it out of every `git diff`/`git status` the skill
  # inspects, so the eval apparatus can never leak into what is being graded.
  # info/exclude rather than .gitignore: nothing about the fixture's tracked
  # files should differ between arms.
  printf '.claude/\n' >> "$(git rev-parse --git-path info/exclude)"

  mkdir -p src test
  cat > README.md <<'EOF'
# Ledger service

Internal service for recording and reconciling account entries.
EOF
  cat > src/ledger.js <<'EOF'
export function recordEntry(entry) {
  return { ...entry, recordedAt: entry.at };
}
EOF
  git add -A
  git commit -q -m "chore: Initial commit"
}

# A multi-part change, so a good message has something to make bullets out of.
stage_feature() {
  mkdir -p src/reconcile test
  cat > src/reconcile/matcher.js <<'EOF'
const TOLERANCE_CENTS = 5;

export function matchEntries(bankRows, ledgerRows) {
  const matched = [];
  const unmatched = [];
  for (const row of bankRows) {
    const hit = ledgerRows.find(
      (l) => l.reference === row.reference && Math.abs(l.amount - row.amount) <= TOLERANCE_CENTS,
    );
    if (hit) matched.push({ bank: row, ledger: hit });
    else unmatched.push(row);
  }
  return { matched, unmatched };
}

export function summarise({ matched, unmatched }) {
  return { matchedCount: matched.length, unmatchedCount: unmatched.length };
}
EOF
  cat > src/reconcile/report.js <<'EOF'
import { summarise } from './matcher.js';

export function renderReport(result) {
  const { matchedCount, unmatchedCount } = summarise(result);
  return `matched ${matchedCount}, unmatched ${unmatchedCount}`;
}
EOF
  cat > test/matcher.test.js <<'EOF'
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { matchEntries } from '../src/reconcile/matcher.js';

test('matches within the cent tolerance', () => {
  const out = matchEntries(
    [{ reference: 'A1', amount: 1000 }],
    [{ reference: 'A1', amount: 1003 }],
  );
  assert.equal(out.matched.length, 1);
});

test('reports unmatched bank rows', () => {
  const out = matchEntries([{ reference: 'ZZ', amount: 10 }], []);
  assert.equal(out.unmatched.length, 1);
});
EOF
  cat >> src/ledger.js <<'EOF'

export function isReconciled(entry) {
  return Boolean(entry.reconciledAt);
}
EOF
  git add -A
}
