# Fixture scaffolding for the `prd-to-plan-criteria` suite.
#
# One small ES-module repo (the shift board, pre-bands) plus a plan draft whose
# acceptance criteria the reviewer must verify by EXECUTING their commands.
# `plan.py` is the single source of the plan text, so the criteria graded in
# check.py are byte-identical to the ones the reviewer reads.

init_repo() {
  git init -q
  git config user.email "fixture@example.com"
  git config user.name "Fixture"
  git config commit.gpgsign false
  printf '.claude/\nplan-draft.md\n' >> "$(git rev-parse --git-path info/exclude)"

  cat > package.json <<'JSON'
{
  "name": "shift-board",
  "version": "0.3.0",
  "type": "module",
  "private": true,
  "scripts": {
    "test": "node --test",
    "build": "node --check src/schedule.js",
    "serve": "python3 -m http.server 8080"
  }
}
JSON

  cat > AGENTS.md <<'MD'
# Project conventions

- ES modules only; named exports only.
- Tests use `node:test` with `node:assert/strict`.
- No third-party dependencies.
- Validation command: `npm test && npm run build`.
MD

  mkdir -p src test
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

  cat > index.html <<'HTML'
<!doctype html>
<meta charset="utf-8">
<title>Shift board</title>
<ul id="board"></ul>
<script type="module" src="./src/main.js"></script>
HTML

  git add -A
  git commit -q -m "chore: Scaffold shift board"
}

# Render the plan draft for a variant to the path the brief names.
write_plan() {
  python3 "$FIXTURE_DIR/../../plan.py" "$1" > plan-draft.md
}
