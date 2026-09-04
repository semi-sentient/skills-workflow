#!/usr/bin/env bash
# Deterministic tests for run-plan's rp.sh helper. No model, no network: a throwaway
# git repo, a synthetic plan covering the shapes real plans have taken (Phase 6A, a
# `Part N` heading, wrapped criteria, checked criteria, Known-risk lines, backticked
# `Human verifies`, a GH footer), keep-dirty paths with spaces and a rename, and a
# stubbed `gh` for the sync/drift paths.
#
#   ./evals/deterministic/test-rp-sh.sh          # exit 0 = all passed
set -u

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
SKILL="$REPO/universal/run-plan"
RP="$SKILL/references/rp.sh"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/rp-test.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
pass=0; fail=0
ok()   { pass=$((pass + 1)); printf '  ok   %s\n' "$1"; }
bad()  { fail=$((fail + 1)); printf '  FAIL %s\n       %s\n' "$1" "${2:-}"; }
check() { # name, condition-exit-code, evidence
  if [ "$2" -eq 0 ]; then ok "$1"; else bad "$1" "$3"; fi
}
eq() { # name expected actual
  if [ "$2" = "$3" ]; then ok "$1"; else bad "$1" "expected: $(printf '%s' "$2" | head -c 300) | actual: $(printf '%s' "$3" | head -c 300)"; fi
}

# ------------------------------------------------------------------ fixture repo
cd "$WORK"
git init -q repo && cd repo
git config user.email t@example.com; git config user.name t; git config commit.gpgsign false
mkdir -p .agents/plans src docs
cat > .agents/plans/demo-plan.md <<'PLAN'
# Plan: Demo Feature

> Source PRD: #7 — https://github.com/o/r/issues/7 ("Demo")

## Architectural decisions

- **Routes**: keep `/api/v1`
- **Schema**: no migrations

---

## Phase 1: Bootstrap

**User stories**: US-1

### What to build

Set up the module.

- [ ] this checkbox is prose, not a criterion

### Acceptance criteria

- [x] (already done) `src/a.js` exists
- [ ] `bandForRate` returns green at target; a rate equal to the target is green,
      never amber
- [ ] Tests cover the boundary

---

## Phase 2: Wire it

### What to build

Wire the module into the board.

### Acceptance criteria

- [ ] `renderBoard` includes the strip
- [ ] `Human verifies` the strip is visible in the browser
- [ ] Human confirms the deploy succeeded

## Phase 6A: Alarm on failure

**Known risk**: requires a human apply. (human-form set confirmed)

### What to build

Add the alarm.

### Acceptance criteria

- [ ] `grep -c alarm infra.tf` returns 1
- [ ] **Human applied** the change

## Part 7 — Cleanup

- [ ] Remove the flag
- [ ] Update the README

## Not a phase

- [ ] stray checkbox after the phases

<!-- gh-sub-issue: 42 -->
PLAN
echo 'a' > src/a.js; echo 'b' > src/b.js; echo 'x' > "docs/design draft.md"; echo 'old' > docs/old.md
git add -A && git commit -qm init
echo '.agents/scratch/' >> "$(git rev-parse --git-path info/exclude)"
SCRATCH="$(pwd -P)/.agents/scratch/run-plan/demo"

echo "rp.sh syntax"
bash -n "$RP"; check "bash -n passes" $? ""

echo "init"
out="$(bash "$RP" init "$SKILL" "$SCRATCH" .agents/plans/demo-plan.md 42 2>"$WORK/err.txt")"; rc=$?
check "init exits 0" $rc "$(cat "$WORK/err.txt")"
check "init copied rp.sh" $([ -f "$SCRATCH/rp.sh" ] && echo 0 || echo 1) ""
check "init copied templates" $([ -f "$SCRATCH/briefs/brief-code.md" ] && [ -f "$SCRATCH/briefs/run-conventions.md" ] && echo 0 || echo 1) ""
check "init wrote ledger header" $(grep -q '^| Phase | Mode' "$SCRATCH/ledger.md" && echo 0 || echo 1) ""
check "init summary names phases" $(printf '%s' "$out" | grep -q '^### Phase 6A' && echo 0 || echo 1) "$out"
check "init warned about the prose checkbox" $(grep -q 'warning: phase 1 has a checkbox line outside' "$WORK/err.txt" && echo 0 || echo 1) "$(cat "$WORK/err.txt")"
check "init did NOT warn about the post-phase stray checkbox" $(grep -q 'stray' "$WORK/err.txt" && echo 1 || echo 0) "$(cat "$WORK/err.txt")"
RPS="$SCRATCH/rp.sh"

echo "extract"
eq "phases" $'1\n2\n6A\n7' "$(bash "$RPS" phases)"
eq "phase 1 criteria labelled, wrapped line kept" $'- [x] (C1) (already done) `src/a.js` exists\n- [ ] (C2) `bandForRate` returns green at target; a rate equal to the target is green,\n      never amber\n- [ ] (C3) Tests cover the boundary' "$(bash "$RPS" criteria 1)"
eq "Part heading without AC heading uses all checkboxes" $'- [ ] (C1) Remove the flag\n- [ ] (C2) Update the README' "$(bash "$RPS" criteria 7)"
check "spec 6A exists" $([ -f "$SCRATCH/phase-6A-spec.md" ] && echo 0 || echo 1) ""
check "spec 7 excludes the footer and the non-phase section" $(grep -q 'gh-sub-issue\|Not a phase\|stray' "$SCRATCH/phase-7-spec.md" && echo 1 || echo 0) "$(cat "$SCRATCH/phase-7-spec.md")"
check "spec 1 excludes phase 2 text" $(grep -q 'Wire the module' "$SCRATCH/phase-1-spec.md" && echo 1 || echo 0) ""
check "spec 1 keeps What to build prose" $(grep -q 'Set up the module' "$SCRATCH/phase-1-spec.md" && echo 0 || echo 1) ""
check "spec 1 keeps the prose checkbox unlabelled" $(grep -q '^- \[ \] this checkbox is prose' "$SCRATCH/phase-1-spec.md" && echo 0 || echo 1) "$(cat "$SCRATCH/phase-1-spec.md")"
check "spec has no trailing separator" $([ "$(tail -1 "$SCRATCH/phase-1-spec.md")" != "---" ] && echo 0 || echo 1) ""
idx="$SCRATCH/plan-index.md"
check "index has H1" $(head -1 "$idx" | grep -q '^# Plan: Demo Feature' && echo 0 || echo 1) "$(head -3 "$idx")"
check "index has source line" $(grep -q '^> Source PRD: #7' "$idx" && echo 0 || echo 1) ""
check "index counts" $(grep -q 'Phases: 4 · Criteria: 10 (1 checked)' "$idx" && echo 0 || echo 1) "$(grep '^Plan file' "$idx")"
check "index has decisions, not What-to-build prose" $(grep -q 'keep `/api/v1`' "$idx" && ! grep -q 'Set up the module' "$idx" && echo 0 || echo 1) ""
check "index flags human-form incl. backticked and bold" $(grep -q '^Human-form criteria: C2 C3$' "$idx" && grep -q '^Human-form criteria: C2$' "$idx" && echo 0 || echo 1) "$(grep 'Human-form' "$idx")"
check "index reports confirmed literal on 6A" $(grep -q '^Human-gate literal: confirmed' "$idx" && echo 0 || echo 1) "$(grep 'literal' "$idx")"
check "index shows Known risk line" $(grep -q '^\*\*Known risk\*\*: requires a human apply' "$idx" && echo 0 || echo 1) ""
check "index has per-phase headings with counts" $(grep -q '^### Phase 2: Wire it — 3 criteria (0 checked) — spec: phase-2-spec.md' "$idx" && echo 0 || echo 1) "$(grep '^###' "$idx")"

echo "tick / untick"
bash "$RPS" tick 1 2 3 >/dev/null 2>&1; rc=$?
check "tick exits 0" $rc ""
eq "tick changed exactly the named criteria" "3" "$(grep -c '^- \[x\]' .agents/plans/demo-plan.md)"
check "tick left the prose checkbox alone" $(grep -q '^- \[ \] this checkbox is prose' .agents/plans/demo-plan.md && echo 0 || echo 1) ""
check "tick re-extracted the index" $(grep -q 'Criteria: 10 (3 checked)' "$idx" && echo 0 || echo 1) ""
bash "$RPS" untick 1 3 >/dev/null 2>&1
eq "untick reverted one" "2" "$(grep -c '^- \[x\]' .agents/plans/demo-plan.md)"
bash "$RPS" tick 1 9 >/dev/null 2>"$WORK/err.txt"; rc=$?
check "tick of a missing criterion fails" $([ $rc -ne 0 ] && echo 0 || echo 1) ""
check "…and names it" $(grep -q 'no criterion C9' "$WORK/err.txt" && echo 0 || echo 1) "$(cat "$WORK/err.txt")"
eq "…and leaves the plan unchanged" "2" "$(grep -c '^- \[x\]' .agents/plans/demo-plan.md)"
bash "$RPS" tick 6A 1 >/dev/null 2>&1
check "tick works on an alphanumeric phase id" $(grep -q '^- \[x\] `grep -c alarm' .agents/plans/demo-plan.md && echo 0 || echo 1) ""
check "footer survives ticks" $(tail -1 .agents/plans/demo-plan.md | grep -q 'gh-sub-issue: 42' && echo 0 || echo 1) ""

echo "ledger / phase-cost"
bash "$RPS" ledger 1 Research 68217 41 113266 R1 "shared layer"
bash "$RPS" ledger 3 Research 59404 36 98112 R1 "api client"
bash "$RPS" ledger 1 Code 151579 84 3057245
bash "$RPS" ledger 1 Review 78097 32 350528 "" "all MET"
bash "$RPS" ledger 2 Code 353900 202 4323000
bash "$RPS" ledger 2 Code 113200 96 1361000 "" "retry 1/2"
bash "$RPS" ledger 2 Review 124600 44 1012000
bash "$RPS" ledger 2 Review 119300 38 860000 "" "re-review"
bash "$RPS" ledger 2 Debug n/a n/a n/a "" "death"
eq "ledger rows appended" "11" "$(wc -l < "$SCRATCH/ledger.md" | tr -d ' ')"
eq "phase-cost phase 1 (a one-member group gets no aside)" "| 68.2K | 151.6K | 78.1K | 297.9K | 0:58:41 |" "$(bash "$RPS" phase-cost 1)"
eq "phase-cost phase 2 (multi-value cells, n/a kept)" "| — | 354K·113K·n/a | 125K·119K | 711.0K | 2:05:56 |" "$(bash "$RPS" phase-cost 2)"
eq "phase-cost unknown phase" "| — | — | — | — | — |" "$(bash "$RPS" phase-cost 9)"
bash "$RPS" ledger 4 Research 1000 1 60000 R2 a; bash "$RPS" ledger 4 Research 1000 1 120000 R2 b; bash "$RPS" ledger 4 Code 2000 2 30000
eq "phase-cost parallel group counted at max" "| 1K·1K | 2.0K | — | 4.0K | 0:02:30 (Σ 0:03:30, 1 parallel group) |" "$(bash "$RPS" phase-cost 4)"

echo "stage / delta / baselines with keep-dirty paths"
printf 'keep-dirty: docs/design draft.md\nkeep-dirty: docs/old.md\nkeep-dirty: docs/new.md\n' > "$SCRATCH/tree-state.md"
echo 'edited' >> "docs/design draft.md"; git mv docs/old.md docs/new.md; echo 'phase work' >> src/a.js; echo 'new' > src/c.js
git add .agents/plans/demo-plan.md   # the plan's tick edits are already staged, as after item 5
eq "delta lists phase files only (no plan file, no keep-dirty paths)" $'src/a.js\nsrc/c.js' "$(bash "$RPS" delta | sort)"
out="$(bash "$RPS" baselines | sort)"
eq "baselines resolves index content and marks new files" $'src/a.js\tbaseline-src__a.js\nsrc/c.js\tnew' "$out"
eq "baseline holds verdict-time content" "a" "$(cat "$SCRATCH/baseline-src__a.js")"
git restore --staged docs/new.md docs/old.md 2>/dev/null || true
bash "$RPS" stage; rc=$?
check "stage exits 0" $rc ""
staged="$(git diff --cached --name-only | sort | tr '\n' ' ')"
eq "stage excluded keep-dirty paths (space in name, both rename halves) and the scratch dir" ".agents/plans/demo-plan.md src/a.js src/c.js " "$staged"
check "plan file with edits is staged too" $(bash "$RPS" tick 1 3 >/dev/null 2>&1 && bash "$RPS" stage && git diff --cached --name-only | grep -q demo-plan.md && echo 0 || echo 1) ""
( cd "$WORK" && git init -q other && cd other && mkdir -p sc && cp "$RPS" sc/rp.sh && printf "PLAN_FILE='%s'\nISSUE=''\nREPO_TOP='%s'\n" "$WORK/repo/.agents/plans/demo-plan.md" "$(pwd -P)" > sc/run.env && bash sc/rp.sh stage 2>"$WORK/other/err.txt" ); rc=$?
check "stage refuses an un-ignored in-repo scratch dir" $([ $rc -ne 0 ] && grep -q 'not git-ignored' "$WORK/other/err.txt" && echo 0 || echo 1) "$(cat "$WORK/other/err.txt" 2>/dev/null)"

echo "review findings (code review of 2026-09-03)"
# B1: a clean-tree run has no tree-state.md at all — stage/delta must still work.
mv "$SCRATCH/tree-state.md" "$WORK/ts.bak"
echo 'more' >> src/a.js
out="$(bash "$RPS" delta 2>"$WORK/err.txt")"; rc=$?
check "delta works with no tree-state.md (keep-dirty paths then count as delta)" $([ $rc -eq 0 ] && printf '%s\n' "$out" | grep -q '^src/a.js$' && printf '%s\n' "$out" | grep -q '^docs/design draft.md$' && echo 0 || echo 1) "rc=$rc out=$out err=$(cat "$WORK/err.txt")"
printf 'input: docs/x.md\n' > "$SCRATCH/tree-state.md"
bash "$RPS" stage 2>"$WORK/err.txt"; rc=$?
check "stage works with a tree-state.md that has no keep-dirty lines" $([ $rc -eq 0 ] && git diff --cached --name-only | grep -q '^src/a.js$' && echo 0 || echo 1) "rc=$rc $(cat "$WORK/err.txt")"
mv "$WORK/ts.bak" "$SCRATCH/tree-state.md"
# B7: glob characters in a keep-dirty path must not exclude siblings.
mkdir -p 'app/users/[id]' app/users/i && echo p > 'app/users/[id]/page.tsx' && echo q > app/users/i/page.tsx
printf 'keep-dirty: app/users/[id]/page.tsx\n' >> "$SCRATCH/tree-state.md"
bash "$RPS" stage
check "glob chars in a keep-dirty path exclude only that path" $(git diff --cached --name-only | grep -q '^app/users/i/page.tsx$' && ! git diff --cached --name-only | grep -q 'id' && echo 0 || echo 1) "$(git diff --cached --name-only)"
git reset -q; rm -rf app; sed -i.bak '/app\/users/d' "$SCRATCH/tree-state.md"; rm -f "$SCRATCH/tree-state.md.bak"
# B3/B4/B17: duplicate basenames, non-ASCII paths, deleted files in baselines.
mkdir -p src/x src/y && echo 1 > src/x/index.js && echo 2 > src/y/index.js && echo 'é' > 'src/café.js' && git add -A && git commit -qm more
echo 3 >> src/x/index.js; echo 4 >> src/y/index.js; echo 'ë' >> 'src/café.js'; rm src/b.js
out="$(bash "$RPS" baselines | sort)"
eq "baselines: distinct names per path, non-ASCII round-trips, deletion marked" $'src/b.js\tdeleted\nsrc/café.js\tbaseline-src__café.js\nsrc/x/index.js\tbaseline-src__x__index.js\nsrc/y/index.js\tbaseline-src__y__index.js' "$out"
eq "baselines hold each file's own index content" "1 2" "$(cat "$SCRATCH/baseline-src__x__index.js" "$SCRATCH/baseline-src__y__index.js" | tr '\n' ' ' | sed 's/ $//')"
git checkout -q -- src; bash "$RPS" cleanup 9
# B9: cwd elsewhere must not matter.
( cd "$WORK" && git init -q elsewhere && cd elsewhere && echo z > z && bash "$RPS" delta ); rc=$?
check "delta from a foreign cwd still targets the recorded repo" $([ $rc -eq 0 ] && echo 0 || echo 1) ""
( cd src && bash "$RPS" stage ); check "stage from a subdirectory exits 0" $? ""
# B2: TAB characters in plan text survive tick.
printf '\n## Phase 8: Tabs\n\n### What to build\n\n```go\nfmt.Println("tab\\tinside")\n\t- [ ] fenced box, not a criterion\n```\n\n### Acceptance criteria\n\n- [ ] first\tcriterion with tab\n- [ ] second\n' > "$WORK/tabs.md"
grep -v 'gh-sub-issue' .agents/plans/demo-plan.md > "$WORK/p2.md"; cat "$WORK/tabs.md" >> "$WORK/p2.md"; printf '\n<!-- gh-sub-issue: 42 -->\n' >> "$WORK/p2.md"; cp "$WORK/p2.md" .agents/plans/demo-plan.md
cp .agents/plans/demo-plan.md "$WORK/before.md"
bash "$RPS" tick 8 2 >/dev/null 2>&1
check "tick preserves tabs and fenced content" $(grep -q $'first\tcriterion with tab' .agents/plans/demo-plan.md && grep -q 'tab\\tinside' .agents/plans/demo-plan.md && [ "$(diff "$WORK/before.md" .agents/plans/demo-plan.md | grep -c '^[<>]')" = 2 ] && echo 0 || echo 1) "$(diff "$WORK/before.md" .agents/plans/demo-plan.md)"
eq "fenced checkbox is not a criterion; tabbed criterion is" $'- [ ] (C1) first\tcriterion with tab\n- [x] (C2) second' "$(bash "$RPS" criteria 8)"
# B8: a symlinked plan file is updated through the link.
mv .agents/plans/demo-plan.md .agents/plans/real-plan.md && ln -s real-plan.md .agents/plans/demo-plan.md
bash "$RPS" untick 8 2 >/dev/null 2>&1
check "tick writes through a symlinked plan file" $([ -L .agents/plans/demo-plan.md ] && grep -q '^- \[ \] second' .agents/plans/real-plan.md && echo 0 || echo 1) ""
rm .agents/plans/demo-plan.md && mv .agents/plans/real-plan.md .agents/plans/demo-plan.md
# B11: unknown ids fail loudly.
bash "$RPS" criteria 99 2>"$WORK/err.txt"; rc=$?
check "criteria on an unknown phase fails" $([ $rc -ne 0 ] && grep -q "no phase '99'" "$WORK/err.txt" && echo 0 || echo 1) "$(cat "$WORK/err.txt")"
bash "$RPS" tick 99 1 2>"$WORK/err.txt"; rc=$?
check "tick on an unknown phase fails" $([ $rc -ne 0 ] && echo 0 || echo 1) ""
# B10: an all-n/a phase reports n/a, not zero.
bash "$RPS" ledger 77 Code n/a n/a n/a "" death
eq "phase-cost with only n/a rows prints n/a totals" "| — | n/a | — | n/a | n/a |" "$(bash "$RPS" phase-cost 77)"
# A13/B13: nested checkbox warning, fenced checkbox silence.
printf '# Plan: N\n\n## Phase 1: X\n\n### Acceptance criteria\n\n- [ ] top\n  - [ ] nested\n' > "$WORK/nested.md"
bash "$RP" init "$SKILL" "$WORK/scn" "$WORK/nested.md" 2>"$WORK/err.txt" >/dev/null
check "nested checkbox under a criterion warns" $(grep -q 'nested checkbox' "$WORK/err.txt" && echo 0 || echo 1) "$(cat "$WORK/err.txt")"
check "…and a plan without Architectural decisions warns" $(grep -q "no '## Architectural decisions' heading" "$WORK/err.txt" && echo 0 || echo 1) "$(cat "$WORK/err.txt")"
bash "$RP" init "$SKILL" "$WORK/scd" .agents/plans/demo-plan.md 42 2>"$WORK/err.txt" >/dev/null
check "a plan with Architectural decisions does not warn about them" $(grep -q 'Architectural decisions' "$WORK/err.txt" && echo 1 || echo 0) "$(cat "$WORK/err.txt")"
# A5/B12: brief values may contain {{TOKENS}}; @@ is a literal at-sign.
bash "$RPS" brief run-conventions.md rc2.md SCRATCH_DIR="$SCRATCH" PROJECT_CONVENTIONS='mentions {{SPEC_PATH}} and {{KEEP_DIRTY_NOTE}}' KEEP_DIRTY_NOTE='@@scope/pkg is fine' TICKET_DIRECTIVE='t' >/dev/null 2>"$WORK/err.txt"; rc=$?
check "brief accepts values containing placeholders and @@ literals" $([ $rc -eq 0 ] && grep -q 'mentions {{SPEC_PATH}} and {{KEEP_DIRTY_NOTE}}' "$SCRATCH/rc2.md" && grep -q '^\*\*Uncommitted user edits.\*\* @scope/pkg is fine' "$SCRATCH/rc2.md" && echo 0 || echo 1) "$(cat "$WORK/err.txt"; grep -n 'mentions\|scope' "$SCRATCH/rc2.md")"
bash "$RPS" brief brief-code.md nope.md PHASE_HEADING=h PLAN_FILE=/nonexistent/plan.md CONVENTIONS_PATH="$SCRATCH/run-conventions.md" CONTEXT_POINTERS=n DELTAS=n MANIFEST_MODIFY=n MANIFEST_REFERENCE=n SPEC_PATH="$SCRATCH/phase-1-spec.md" HUMAN_FORM=n FIX_CYCLE=n COMMIT_MSG_PATH=x HANDOFF_PATH=y 2>"$WORK/err.txt"; rc=$?
check "brief refuses an input path that does not exist" $([ $rc -ne 0 ] && grep -q 'PLAN_FILE names /nonexistent/plan.md' "$WORK/err.txt" && echo 0 || echo 1) "$(cat "$WORK/err.txt")"
# A2: evidence check.
printf '| C1 | MET | a.js:1 |\n| C2 | NOT MET | gap |\n\nFindings\n\nF1 — behaviour — gap at a.js:3\nF2 — documentation — stale comment\n' > "$SCRATCH/phase-9-review.md"
check "evidence passes with enough findings" $(bash "$RPS" evidence "$SCRATCH/phase-9-review.md" 2 >/dev/null && echo 0 || echo 1) ""
bash "$RPS" evidence "$SCRATCH/phase-9-review.md" 3 2>"$WORK/err.txt"; rc=$?
check "evidence fails when the file names fewer findings than the return" $([ $rc -ne 0 ] && grep -q 'names 2 distinct' "$WORK/err.txt" && echo 0 || echo 1) "$(cat "$WORK/err.txt")"
bash "$RPS" evidence "$SCRATCH/nope.md" 0 2>"$WORK/err.txt"; rc=$?
check "evidence fails on a missing file" $([ $rc -ne 0 ] && echo 0 || echo 1) ""
printf 'no rows here\n' > "$SCRATCH/phase-9-review-2.md"
bash "$RPS" evidence "$SCRATCH/phase-9-review-2.md" 0 2>"$WORK/err.txt"; rc=$?
check "evidence fails without a C<k> row" $([ $rc -ne 0 ] && grep -q 'no C<k>' "$WORK/err.txt" && echo 0 || echo 1) ""

echo "review-path / cleanup"
eq "first evidence path is unsuffixed" "$SCRATCH/phase-3-review.md" "$(bash "$RPS" review-path 3)"
touch "$SCRATCH/phase-3-review.md"
eq "second is -2" "$SCRATCH/phase-3-review-2.md" "$(bash "$RPS" review-path 3)"
touch "$SCRATCH/phase-3-review-2.md" "$SCRATCH/phase-3-review-4.md" "$SCRATCH/phase-3-brief-review.md"
eq "next is highest+1, ignoring the brief file" "$SCRATCH/phase-3-review-5.md" "$(bash "$RPS" review-path 3)"
touch "$SCRATCH/phase-3-review-5.md"; bash "$RPS" review-path 3 >/dev/null
check "review-path rm -f's the path it returns" $([ ! -e "$SCRATCH/phase-3-review-6.md" ] && echo 0 || echo 1) ""
touch "$SCRATCH/phase-2-commit-msg.md" "$SCRATCH/baseline-z.js" "$SCRATCH/phase-2-handoff.md"
bash "$RPS" cleanup 2
check "cleanup removed message file and baselines, kept handoff" $([ ! -e "$SCRATCH/phase-2-commit-msg.md" ] && [ ! -e "$SCRATCH/baseline-z.js" ] && [ ! -e "$SCRATCH/baseline-src__a.js" ] && [ -e "$SCRATCH/phase-2-handoff.md" ] && echo 0 || echo 1) "$(ls "$SCRATCH")"
bash "$RPS" cleanup 2; check "cleanup with nothing to delete exits 0" $? ""

echo "brief"
touch "$SCRATCH/run-conventions.md"
out="$(bash "$RPS" brief brief-code.md phase-1-brief-code.md PHASE_HEADING='Phase 1: Bootstrap' PLAN_FILE="$PWD/.agents/plans/demo-plan.md" CONVENTIONS_PATH="$SCRATCH/run-conventions.md" CONTEXT_POINTERS=$'- `research-a.md`\n- none' DELTAS='None' MANIFEST_MODIFY='- `src/a.js`' MANIFEST_REFERENCE='- `src/b.js` — "quoted" & <special> $chars' SPEC_PATH="$SCRATCH/phase-1-spec.md" HUMAN_FORM='None' FIX_CYCLE='None — first attempt.' COMMIT_MSG_PATH="$SCRATCH/phase-1-commit-msg.md" HANDOFF_PATH="$SCRATCH/phase-1-handoff.md" 2>"$WORK/err.txt")"; rc=$?
check "brief fills a template" $rc "$(cat "$WORK/err.txt")"
check "brief prints path and size" $(printf '%s' "$out" | grep -q 'phase-1-brief-code.md ([0-9]* bytes)' && echo 0 || echo 1) "$out"
check "multi-line and special-character values survive" $(grep -q '^- none$' "$SCRATCH/phase-1-brief-code.md" && grep -Fq '"quoted" & <special> $chars' "$SCRATCH/phase-1-brief-code.md" && echo 0 || echo 1) ""
check "no placeholder remains" $(grep -q '{{' "$SCRATCH/phase-1-brief-code.md" && echo 1 || echo 0) "$(grep '{{' "$SCRATCH/phase-1-brief-code.md")"
bash "$RPS" brief brief-code.md x.md PHASE_HEADING=h 2>"$WORK/err.txt"; rc=$?
check "brief refuses unfilled placeholders" $([ $rc -ne 0 ] && grep -q 'unfilled placeholders' "$WORK/err.txt" && grep -q 'SPEC_PATH' "$WORK/err.txt" && echo 0 || echo 1) "$(cat "$WORK/err.txt")"
check "…and writes nothing" $([ ! -e "$SCRATCH/x.md" ] && echo 0 || echo 1) ""
echo 'from a file' > "$WORK/val.txt"
bash "$RPS" brief run-conventions.md run-conventions.md SCRATCH_DIR="$SCRATCH" PROJECT_CONVENTIONS=@"$WORK/val.txt" KEEP_DIRTY_NOTE='None declared.' TICKET_DIRECTIVE='Use `#42` as the ticket identifier.' >/dev/null 2>"$WORK/err.txt"; rc=$?
check "brief accepts @file values" $([ $rc -eq 0 ] && grep -q '^from a file$' "$SCRATCH/run-conventions.md" && echo 0 || echo 1) "$(cat "$WORK/err.txt")"
for t in brief-research.md brief-review.md brief-rereview.md; do
  keys="$(grep -oE '\{\{[A-Z0-9_]+\}\}' "$SCRATCH/briefs/$t" | sort -u | tr -d '{}' | awk -v f="$SCRATCH/phase-1-spec.md" '/^(CONVENTIONS_PATH|SPEC_PATH|PLAN_FILE|PRIOR_EVIDENCE)$/ { print $0 "=" f; next } { print $0 "=v" }' | tr '\n' ' ')"
  # shellcheck disable=SC2086
  bash "$RPS" brief "$t" "out-$t" $keys >/dev/null 2>"$WORK/err.txt"; rc=$?
  check "template $t fills with all its placeholders" $rc "$(cat "$WORK/err.txt")"
done
bash "$RPS" brief nope.md y.md 2>"$WORK/err.txt"; rc=$?
check "brief names missing template" $([ $rc -ne 0 ] && grep -q 'no template' "$WORK/err.txt" && echo 0 || echo 1) ""

echo "sync / drift / pull (stubbed gh)"
mkdir -p "$WORK/bin"
cat > "$WORK/bin/gh" <<'GH'
#!/usr/bin/env bash
# stub: `gh issue view N --json body --jq .body` prints $GH_BODY_FILE; `gh issue edit N --body-file F` copies F there.
case "$1 $2" in
  "issue view") cat "$GH_BODY_FILE" ;;
  "issue edit") if [ -n "${GH_FAIL:-}" ]; then echo "boom" >&2; exit 1; fi; shift 3; cp "$2" "$GH_BODY_FILE" ;;
  *) exit 2 ;;
esac
GH
chmod +x "$WORK/bin/gh"
export PATH="$WORK/bin:$PATH" GH_BODY_FILE="$WORK/gh-body.txt"
grep -v 'gh-sub-issue' .agents/plans/demo-plan.md > "$GH_BODY_FILE"
eq "drift: identical modulo footer" "identical" "$(bash "$RPS" drift)"
sed 's/^- \[x\] \(.*already done\)/- [ ] \1/' "$GH_BODY_FILE" > "$WORK/t" && mv "$WORK/t" "$GH_BODY_FILE"
eq "drift: local ahead by ticks only" "local-ahead 1" "$(bash "$RPS" drift)"
sed 's/^- \[ \] `renderBoard`/- [x] `renderBoard`/; s/^- \[ \] Remove the flag/- [x] Remove the flag/' "$GH_BODY_FILE" > "$WORK/t" && mv "$WORK/t" "$GH_BODY_FILE"
eq "drift: gh ahead" "gh-ahead 1" "$(bash "$RPS" drift)"
bash "$RPS" pull
check "pull took the GH body and kept the footer" $(grep -q '^- \[x\] `renderBoard`' .agents/plans/demo-plan.md && tail -1 .agents/plans/demo-plan.md | grep -q 'gh-sub-issue: 42' && echo 0 || echo 1) "$(tail -3 .agents/plans/demo-plan.md)"
eq "pull leaves exactly one footer" "1" "$(grep -c 'gh-sub-issue' .agents/plans/demo-plan.md)"
eq "…and now drift is identical" "identical" "$(bash "$RPS" drift)"
echo 'extra prose' >> "$GH_BODY_FILE"
eq "drift: non-checkbox difference" "differ" "$(bash "$RPS" drift)"
out="$(bash "$RPS" sync)"; rc=$?
check "sync pushes the plan" $([ $rc -eq 0 ] && [ "$out" = "synced #42" ] && cmp -s .agents/plans/demo-plan.md "$GH_BODY_FILE" && echo 0 || echo 1) "$out"
GH_FAIL=1 bash "$RPS" sync 2>"$WORK/err.txt"; rc=$?
check "sync fails loudly after retries" $([ $rc -ne 0 ] && grep -q 'failed after 4 attempts: boom' "$WORK/err.txt" && echo 0 || echo 1) "$(cat "$WORK/err.txt")"
# A1/B5: CRLF bodies compare equal and pull never writes CR into the plan or the specs.
grep -v 'gh-sub-issue' .agents/plans/demo-plan.md | sed 's/$/\r/' > "$GH_BODY_FILE"
eq "drift: CRLF body vs LF local is identical" "identical" "$(bash "$RPS" drift)"
printf 'trailing\r\n' >> "$GH_BODY_FILE"
eq "drift: a real content difference under CRLF is differ" "differ" "$(bash "$RPS" drift)"
bash "$RPS" pull
check "pull strips CR from the plan and specs" $(! grep -q $'\r' .agents/plans/demo-plan.md && ! cat "$SCRATCH"/phase-*-spec.md | grep -q $'\r' && tail -1 .agents/plans/demo-plan.md | grep -q 'gh-sub-issue: 42' && echo 0 || echo 1) "$(tail -3 .agents/plans/demo-plan.md | cat -v)"
sed -i.bak "s/^ISSUE=.*/ISSUE=''/" "$SCRATCH/run.env"
eq "sync is a no-op local-only" "local-only run: nothing to sync" "$(bash "$RPS" sync)"

echo "errors"
( cd "$WORK" && mkdir -p e && cp "$RP" e/rp.sh && bash e/rp.sh phases 2>"$WORK/err.txt" ); rc=$?
check "commands without run.env fail with guidance" $([ $rc -ne 0 ] && grep -q 'run.env missing' "$WORK/err.txt" && echo 0 || echo 1) ""
printf '# Plan: X\n\nno phases here\n' > "$WORK/nophase.md"
bash "$RP" init "$SKILL" "$WORK/sc2" "$WORK/nophase.md" 2>"$WORK/err.txt"; rc=$?
check "init fails on a plan with no phases" $([ $rc -ne 0 ] && grep -q 'no phases found' "$WORK/err.txt" && echo 0 || echo 1) "$(cat "$WORK/err.txt")"
bash "$RP" init "$SKILL" "$WORK/sc3" "$WORK/nophase.md" abc 2>"$WORK/err.txt"; rc=$?
check "init rejects a non-numeric issue" $([ $rc -ne 0 ] && grep -q 'bare number' "$WORK/err.txt" && echo 0 || echo 1) ""
bash "$RPS" bogus 2>"$WORK/err.txt"; rc=$?
check "unknown command fails" $([ $rc -ne 0 ] && echo 0 || echo 1) ""
check "help prints the command list" $(bash "$RPS" help | grep -q 'review-path <n>' && bash "$RPS" help | grep -q 'evidence <path>' && echo 0 || echo 1) ""

printf '\n%d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
