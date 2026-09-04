#!/usr/bin/env bash
# burn-in.sh — Build a throwaway fixture repo for exercising run-plan end to end
#
# run-plan drives irreversible git/GitHub operations, and several of its branches
# are never reached by a normal run. This script builds a disposable GitHub repo
# rigged so that one invocation walks the cold paths: standalone `gh-issue:` plan
# resolution, the silent-repo `gh pr create` submission, the no-parent `Refs`
# omission, and Step 5e's tracked-file guard.
#
# It sets up and verifies. It never invokes run-plan — you drive that yourself
# and watch the reasoning, which is the point of a burn-in.
#
# COSTS AND SIDE EFFECTS: creates a real (private) GitHub repo under your
# account, pushes to it, opens an issue, and a full run spends real sub-agent
# tokens (roughly 300-500K, 30-60 minutes for the two-phase fixture plan).
#
# Usage:
#   ./scripts/burn-in.sh setup <name> [--yes]   Build the fixture and print the invocation
#   ./scripts/burn-in.sh snapshot <name>        Record pre-run state for later comparison
#   ./scripts/burn-in.sh verify <name>          Check post-run outcomes (structural, not phrasing)
#   ./scripts/burn-in.sh probe <guard|stalefooter|tie|dirty> <name>
#                                               Stage a cold-path scenario
#   ./scripts/burn-in.sh restore <name>         Undo a probe, return to a clean tree
#   ./scripts/burn-in.sh teardown <name>        Print the cleanup commands (never runs them)
#
# Example:
#   ./scripts/burn-in.sh setup run-plan-burnin-2026-07
#   # ... run /run-plan #N --base main inside the fixture ...
#   ./scripts/burn-in.sh verify run-plan-burnin-2026-07
#
# The fixture is SINGLE-USE: a completed run leaves the plan's criteria checked,
# the work branch pushed and a PR open, so a second run resolves as a resume
# rather than a fresh plan. Regenerate with a fresh name rather than resetting.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

BURN_IN_DIR="${BURN_IN_DIR:-$HOME/.run-plan-burnin}"

# Skills the fixture needs on hand. run-plan's Code briefs tell the agent to read
# `tdd`, and its commit step invokes `commit` — a fixture missing either tests a
# degraded version of the skill.
FIXTURE_SKILLS=(run-plan commit tdd)

CMD="${1:-}"

die() {
  echo "Error: $*" >&2
  exit 1
}

require_gh() {
  command -v gh >/dev/null 2>&1 || die "gh CLI not found — install it first."
  gh auth status >/dev/null 2>&1 || die "gh is not authenticated. Run: gh auth login"
}

fixture_path() {
  echo "$BURN_IN_DIR/$1"
}

meta_path() {
  # Metadata lives OUTSIDE the fixture repo so reading or writing it can never
  # dirty the working tree — dirt makes run-plan stop for a per-path triage.
  echo "$BURN_IN_DIR/$1.meta"
}

load_meta() {
  local meta
  meta="$(meta_path "$1")"
  [[ -f "$meta" ]] || die "No fixture metadata at $meta. Run 'setup $1' first."
  # shellcheck disable=SC1090
  source "$meta"
}

# ---------------------------------------------------------------- setup

cmd_setup() {
  local name="${1:-}"
  local auto_yes="${2:-}"
  [[ -n "$name" ]] || die "Usage: $0 setup <name> [--yes]"

  require_gh

  local dir
  dir="$(fixture_path "$name")"
  [[ -e "$dir" ]] && die "$dir already exists. Pick another name — fixtures are single-use."

  cat <<BANNER

burn-in setup: $name

This will:
  - create a PRIVATE GitHub repo '$name' under your account
  - clone it to $dir
  - push a scaffold, open an issue, and print a /run-plan invocation

A full run afterwards spends real sub-agent tokens (~300-500K, 30-60 min).
Nothing is deleted for you; 'teardown' only prints the commands.

BANNER

  if [[ "$auto_yes" != "--yes" ]]; then
    read -r -p "Proceed? [y/N] " reply
    [[ "$reply" == "y" || "$reply" == "Y" ]] || die "Aborted."
  fi

  mkdir -p "$BURN_IN_DIR"
  echo ""
  echo "Creating repo..."
  (cd "$BURN_IN_DIR" && gh repo create "$name" --private --clone >/dev/null)
  [[ -d "$dir" ]] || die "Clone did not land at $dir."

  local slug="$(gh repo view "$name" --json nameWithOwner --jq .nameWithOwner)"
  echo "  $slug -> $dir"

  echo "Scaffolding project..."
  cd "$dir"

  # A real test runner and build command, with zero installs: every Code brief
  # carries the TDD directive and the Build Verification Gate, and a fixture
  # without them turns a trivial phase into retry churn.
  cat > package.json <<'EOF'
{
  "name": "widget-fixture",
  "version": "0.0.0",
  "type": "module",
  "private": true,
  "scripts": {
    "test": "node --test",
    "build": "node --check src/widget.js"
  }
}
EOF

  mkdir -p src test
  cat > src/widget.js <<'EOF'
// Minimal seed module. The plan's phases extend this.
export function widgetLabel(widget) {
  return String(widget.name);
}
EOF

  cat > test/widget.test.js <<'EOF'
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { widgetLabel } from '../src/widget.js';

test('widgetLabel returns the name', () => {
  assert.equal(widgetLabel({ name: 'sprocket' }), 'sprocket');
});
EOF

  # Variant S: real conventions, and deliberately SILENT about PR submission.
  # That silence is what resolves <pr_open_mode> to `silent` at Step 1d and
  # sends Step 5d down the `gh pr create` path this fixture exists to exercise.
  cat > AGENTS.md <<'EOF'
# Project conventions

- ES modules only (`"type": "module"`); use `import`, never `require`.
- Tests use the built-in `node:test` runner with `node:assert/strict`.
- No third-party dependencies — this project installs nothing.
- Two-space indentation; named exports only.
- Validation command: `npm test && npm run build`. Both must pass.
EOF

  link_skills_into_fixture

  mkdir -p .agents/plans
  cat > .agents/plans/widget-plan.md <<'EOF'
# Plan: Widget Pipeline

Small two-phase plan used to exercise run-plan end to end. The work is
deliberately trivial; the point is the ceremony around it.

## Architectural decisions

- `src/widget.js` stays dependency-free and exports named functions only.
- Formatting and validation are separate functions so phase 2 can build on
  phase 1 without rewriting it.

## Phase 1: Format widgets for display

Add a formatting helper alongside the existing `widgetLabel`.

### Acceptance criteria

- [ ] `src/widget.js` exports `formatWidget(widget)` returning `"<name> (<quantity>)"`
- [ ] `test/widget.test.js` covers a widget with a quantity of zero
- [ ] `npm test` passes
- [ ] `npm run build` passes

## Phase 2: Reject malformed widgets

Build on phase 1's `formatWidget`.

### Acceptance criteria

- [ ] `formatWidget` throws a `TypeError` when `name` is missing or not a string
- [ ] A test asserts the thrown `TypeError`
- [ ] Phase 1's tests still pass unchanged
- [ ] `npm test` passes
EOF

  git add -A >/dev/null
  git -c user.email="burn-in@example.com" -c user.name="burn-in" \
    commit -q -m "chore: Scaffold burn-in fixture"
  git branch -M main
  git push -q -u origin main
  git remote set-head origin -a >/dev/null 2>&1 || true
  echo "  scaffold pushed to main"

  echo "Publishing the plan as a standalone issue..."
  local issue_url issue_num
  issue_url="$(gh issue create \
    --title "Plan: Widget Pipeline" \
    --body-file .agents/plans/widget-plan.md)"
  issue_num="${issue_url##*/}"
  echo "  issue #$issue_num — $issue_url"

  # ORDER MATTERS. The footer has to exist locally AND on the issue before the
  # run starts. Footer the local file, then re-sync the issue body from it: if
  # the two differ in non-checkbox content, Step 1c halts and asks which to keep
  # before anything else happens.
  printf '\n<!-- gh-issue: %s -->\n' "$issue_num" >> .agents/plans/widget-plan.md
  gh issue edit "$issue_num" --body-file .agents/plans/widget-plan.md >/dev/null
  git add -A >/dev/null
  git -c user.email="burn-in@example.com" -c user.name="burn-in" \
    commit -q -m "chore: Link plan to issue #$issue_num"
  git push -q
  echo "  footer written locally and re-synced to the issue"

  cat > "$(meta_path "$name")" <<EOF
FIXTURE_NAME="$name"
FIXTURE_DIR="$dir"
REPO_SLUG="$slug"
ISSUE_NUM="$issue_num"
PLAN_PATH=".agents/plans/widget-plan.md"
BRANCH="plan/widget"
EOF

  write_burn_in_doc "$name" "$issue_num" "$slug"

  cat <<NEXT

Fixture ready.

Next steps:
  1. cd $dir
  2. Optionally stage the abort-early probes FIRST (they leave no trace):
       $0 probe guard $name
       $0 probe stalefooter $name
       $0 probe tie $name
       $0 restore $name
     Or stage the dirty-tree probe and run the full burn-in through it
     (it exercises the Step 1e.2a triage instead of aborting):
       $0 probe dirty $name
  3. $0 snapshot $name
  4. Run the burn-in from inside the fixture:
       /run-plan #$issue_num --base main
  5. $0 verify $name

BURN-IN.md in the fixture holds the observation checklist and the branch register.
NEXT
}

# Point the fixture at the skills in THIS working tree, not at the published
# repo. A burn-in exists to test uncommitted edits, so `npx skills add` would
# defeat the whole exercise by installing whatever is on GitHub. Symlinks also
# mean a fix here needs no re-copy — but do not edit skill files mid-run.
#
# Mirrors register-skill.sh's shape (real dir, symlinked entries) rather than
# symlinking the skill directory itself, since that is the layout known to work.
link_skills_into_fixture() {
  local linked=()
  for skill in "${FIXTURE_SKILLS[@]}"; do
    local src="$REPO_ROOT/universal/$skill"
    [[ -d "$src" ]] || die "Expected skill source at $src"
    mkdir -p ".claude/skills/$skill"
    while IFS= read -r entry; do
      ln -sfn "$entry" ".claude/skills/$skill/$(basename "$entry")"
    done < <(find "$src" -mindepth 1 -maxdepth 1 \( -type f -o -type d \))
    linked+=("$skill")
  done

  # Keep these out of the index: dirt makes run-plan stop for a per-path triage,
  # so untracked symlinks would prompt on every invocation. BURN-IN.md is ignored
  # rather than committed because you edit its branch register after each run —
  # tracked, every edit would re-dirty the tree and prompt again.
  printf '.claude/\nBURN-IN.md\n' > .gitignore

  echo "  skills symlinked from $REPO_ROOT/universal: ${linked[*]}"
}

write_burn_in_doc() {
  local name="$1" issue="$2" slug="$3"
  cat > "$(fixture_path "$name")/BURN-IN.md" <<EOF
# Burn-in fixture — $name

Repo: \`$slug\` · Plan issue: #$issue · Invocation: \`/run-plan #$issue --base main\`

This repo has **no** PR-opening workflow and its AGENTS.md says nothing about
pull requests, which is what resolves \`<pr_open_mode>\` to \`silent\` and sends
Step 5d down the \`gh pr create\` path.

\`.claude/skills/\` symlinks **live** into the skills repo's \`universal/\`, so this
fixture always exercises the working tree — uncommitted edits included, which is
the point. Do not edit skill files while a run is in flight.

## Watch for these during the run

- [ ] Step 2 announces syncing to issue #$issue **without** having fetched the
      body — proves the \`gh-issue:\` grep matched the local file
- [ ] No complaint about a missing parent — Step 1b.2 finds none and leaves
      \`<gh_issue_number>\` unset, which is expected, not an error
- [ ] Research agents spawn file-backed (\`general-purpose\`), write their own
      \`research-*.md\`, and their ledger rows carry real token/duration figures
      (an inline-lookup \`Explore\` row — or an infrastructure-death row —
      reads \`n/a\`; every other row carries real figures)
- [ ] The ledger exists before the first research agent returns
- [ ] \`run-conventions.md\` is written once at Step 2, and every skeleton brief
      (all modes but Review) points at it instead of restating the standing
      directives
- [ ] Each phase is reviewed by a fresh Review agent before its commit
- [ ] Review returns are criterion+verdict lines, findings, and all three
      trailing sections — scope-creep, out-of-criteria defects, and the
      weak-criteria flag (an explicit "None" each when empty) — while the
      evidence table lands in \`phase-N-review.md\`, not the return
- [ ] No turn ends between phases — the tracker renders and the next
      phase's brief is composed in the same turn
- [ ] If any fix cycle occurs: the status flag shows counted budgets
      (\`(↻ retry n/2, corrective n/2)\`, never a bare \`(↻ retried)\`) and
      any retry or corrective brief — never a Debug brief — carries the
      Message maintenance rule (file-exists or absent-file arm)
- [ ] The final summary states the outcome (\`complete\`) explicitly
- [ ] \`gh pr create\` is used — no polling, no \`gh pr edit\`

## Verify afterwards

\`\`\`
./scripts/burn-in.sh verify $name
\`\`\`

Checks structural outcomes only — PR authorship, body contents, plan-file retention,
pushed branch. Deliberately does not assert on wording, which changes for
reasons that have nothing to do with correctness.

## Branch register

Which run-plan branches this run exercised goes in the repo's durable register,
NOT here — this file dies with the fixture:

    <repo>/evals/run-plan-branches.md

Record the branch, the instrument, and the date. Cold rows there are the reason
the next fixture exists.
EOF
}

# ---------------------------------------------------------------- probes

cmd_probe() {
  local kind="${1:-}" name="${2:-}"
  [[ -n "$kind" && -n "$name" ]] || die "Usage: $0 probe <guard|stalefooter|tie|dirty> <name>"
  load_meta "$name"
  cd "$FIXTURE_DIR"

  case "$kind" in
    guard)
      # Only a PRD in the plans dir, carrying the same footer shape a plan uses.
      # Passing its number must fail loudly BEFORE any side effect.
      rm -f .agents/plans/widget-plan.md
      cat > .agents/plans/widget-prd.md <<'EOF'
# PRD: Widget Pipeline

## Problem

Widgets render inconsistently across surfaces.

## Requirements

- A single formatting helper owns widget display strings.
- Malformed widgets fail loudly rather than rendering as "undefined".

<!-- gh-issue: 999999 -->
EOF
      cat <<EOF

Probe staged: PRD guard.

  Run:    /run-plan #999999
  Expect: a loud refusal identifying #999999 as a PRD-epic rather than a plan.

  Structural checks (these are the assertion, not the wording):
    - no plan/* branch was created      git branch --list 'plan/*'
    - no scratch dir was created        ls .agents/scratch 2>/dev/null
    - .git/info/exclude was not touched
    - the issue number need not exist on GitHub — resolution fails first

  Then: $0 restore $name

EOF
      ;;
    stalefooter)
      # A plan and a PRD carrying the SAME issue number. Only one is a plan, so
      # this is mechanically resolvable — the skill should resolve it, not ask.
      cat > .agents/plans/widget-prd.md <<EOF
# PRD: Widget Pipeline

## Problem

Widgets render inconsistently across surfaces.

<!-- gh-issue: $ISSUE_NUM -->
EOF
      cat <<EOF

Probe staged: stale footer on a non-plan.

  Both widget-plan.md and widget-prd.md now carry <!-- gh-issue: $ISSUE_NUM -->,
  but only widget-plan.md is a plan.

  Run:    /run-plan #$ISSUE_NUM
  Expect: it resolves to widget-plan.md WITHOUT asking, and names widget-prd.md
          as carrying a footer for an issue it does not own.
  Fail:   stopping to ask (over-cautious), or resolving without naming the PRD.

  Then: $0 restore $name

EOF
      ;;
    dirty)
      # The chain grill-with-docs -> write-a-prd -> prd-to-plan leaves domain docs,
      # ADRs and the plan file uncommitted; run-plan must triage them rather than
      # abort. Includes a path with a space, which porcelain C-quotes — an
      # unquoted ':(exclude)' pathspec on it exits 0 and stages the file anyway.
      mkdir -p docs/adr
      cat > docs/CONTEXT.md <<'EOF'
# Domain language

- **Widget**: the unit this pipeline formats. Carries a name and a quantity.
- **Malformed widget**: a widget whose name is absent or not a string.
EOF
      cat > docs/adr/0001-widget-validation-belongs-in-format.md <<'EOF'
# Widget validation belongs in formatWidget

Validation lives in `formatWidget` rather than a separate validator, so callers
cannot format an unvalidated widget.

## Consequences

- `formatWidget` throws `TypeError` on a malformed widget.
EOF
      cat > "docs/design draft.md" <<'EOF'
Scratch notes. Deliberately contains a space in the filename.
EOF
      printf '\n# Local experiment — not for commit.\n' >> AGENTS.md
      cat <<EOF

Probe staged: dirty working tree (the grill-with-docs -> run-plan shape).

  Uncommitted now:
$(git -c core.quotePath=false status --porcelain -uall | sed 's/^/    /')

  Run:    /run-plan #$ISSUE_NUM --base main
  Expect: it does NOT abort. It lists all four paths numbered and asks which are
          this work's input. Answer with the CONTEXT/ADR numbers only, leaving
          'docs/design draft.md' and AGENTS.md unnamed.
  Then verify, in order:
    1. those two land in ONE commit of their own, after the branch is created and
       BEFORE Phase 1 — 'git log --stat main..$BRANCH' shows it as the OLDEST
       commit (bottom of the list; git log prints newest first)
    2. no phase commit contains AGENTS.md or 'docs/design draft.md'
       ('git log -p main..$BRANCH -- AGENTS.md "docs/design draft.md"'
       must show ONLY nothing — the space-quoting bug shows up here)
    3. both unnamed files are still dirty and unchanged at the end, and the
       scratch tree-state.md records them as keep-dirty
    4. Step 2 reported the inputs commit and its sha before asking to proceed
  Fail:   aborting on the dirty tree; folding the docs into a phase commit;
          committing, reverting, deleting or stashing either unnamed file.

  Then: $0 restore $name
EOF
      ;;

    tie)
      # Two actual PLANS claiming the same issue. No principled resolution
      # exists, so this is the one case that must stop and ask.
      cat > .agents/plans/widget-plan-alt.md <<EOF
# Plan: Widget Pipeline (alternate)

## Phase 1: Alternate approach

### Acceptance criteria

- [ ] \`src/widget.js\` exports \`formatWidget\` via an alternate implementation
- [ ] \`npm test\` passes

<!-- gh-issue: $ISSUE_NUM -->
EOF
      cat <<EOF

Probe staged: genuine tie.

  widget-plan.md and widget-plan-alt.md are BOTH plans claiming #$ISSUE_NUM.

  Run:    /run-plan #$ISSUE_NUM
  Expect: it stops and asks which is canonical — there is no principled way to pick.
  Fail:   picking either one, however well explained.

  Then: $0 restore $name

EOF
      ;;
    *)
      die "Unknown probe '$kind'. Use 'guard', 'stalefooter', 'tie', or 'dirty'."
      ;;
  esac
}

cmd_restore() {
  local name="${1:-}"
  [[ -n "$name" ]] || die "Usage: $0 restore <name>"
  load_meta "$name"
  cd "$FIXTURE_DIR"

  git checkout -- .agents/plans 2>/dev/null || true
  git clean -fdq .agents/plans

  # The stalefooter probe resolves and continues, so by the time you have seen
  # its answer it may already have reached Step 1e and cut the work branch.
  # Leaving that behind would send the NEXT run down Step 1e.3's "branch exists
  # with commits but plan shows no progress" prompt instead of a clean start.
  local current
  current="$(git branch --show-current)"
  if [[ "$current" == "$BRANCH" ]]; then
    git checkout -q main
    current="main"
  fi
  if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
    local ahead
    ahead="$(git rev-list --count "main..$BRANCH" 2>/dev/null || echo 0)"
    if [[ "$ahead" -eq 0 ]]; then
      git branch -q -D "$BRANCH"
      echo "  removed stray branch $BRANCH (no commits ahead of main)"
    else
      echo "  KEPT branch $BRANCH — it has $ahead commit(s) ahead of main."
      echo "  That is real work, not probe residue. Inspect before deleting:"
      echo "    git -C $FIXTURE_DIR log main..$BRANCH --oneline"
    fi
  fi

  # The dirty probe's artifacts: untracked files it created, plus its append to
  # the tracked AGENTS.md. Checkout is safe here because the probe only appended.
  rm -f docs/CONTEXT.md docs/adr/0001-widget-validation-belongs-in-format.md
  rm -f "docs/design draft.md"
  rmdir docs/adr docs 2>/dev/null || true
  git checkout -q -- AGENTS.md 2>/dev/null || true

  # Scratch is git-ignored, so it never dirties the tree — but a stale ledger or
  # commit-message file from an aborted probe can satisfy a later fast-path check.
  rm -rf .agents/scratch/run-plan

  echo "Plans directory, branch, and scratch restored. Tree state:"
  git status --short || true
  echo "(An empty listing means run-plan starts clean — dirt triggers a triage prompt.)"
}

# ---------------------------------------------------------------- snapshot

cmd_snapshot() {
  local name="${1:-}"
  [[ -n "$name" ]] || die "Usage: $0 snapshot <name>"
  load_meta "$name"
  cd "$FIXTURE_DIR"

  local snap="$BURN_IN_DIR/$name.snapshot"
  {
    echo "# pre-run snapshot"
    echo "## refs"
    git show-ref || true
    echo "## plans dir"
    ls -1 .agents/plans || true
    echo "## info/exclude"
    cat "$(git rev-parse --git-path info/exclude)" 2>/dev/null || true
  } > "$snap"
  echo "Snapshot written: $snap"
}

# ---------------------------------------------------------------- verify

PASS=0
FAIL=0

check() {
  local label="$1" ok="$2" detail="${3:-}"
  if [[ "$ok" == "yes" ]]; then
    echo "  PASS  $label"
    PASS=$((PASS + 1))
  else
    echo "  FAIL  $label${detail:+ — $detail}"
    FAIL=$((FAIL + 1))
  fi
}

cmd_verify() {
  local name="${1:-}"
  [[ -n "$name" ]] || die "Usage: $0 verify <name>"
  require_gh
  load_meta "$name"
  cd "$FIXTURE_DIR"

  echo ""
  echo "Verifying burn-in outcomes for $name (issue #$ISSUE_NUM)"
  echo ""

  # Step 5e — the plan file is KEPT on this fixture: it is committed during
  # scaffolding, and Step 5e never deletes a file tracked on the branch (doing so
  # would leave the tree contradicting HEAD and the PR). The deletion branch needs
  # a fixture whose plans dir is git-ignored; see evals/run-plan-branches.md.
  [[ -f "$PLAN_PATH" ]] \
    && check "Step 5e kept the tracked plan file" "yes" \
    || check "Step 5e kept the tracked plan file" "no" "$PLAN_PATH was deleted despite being tracked"

  # Step 5c — the work branch reached the remote.
  if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
    check "work branch '$BRANCH' pushed to origin" "yes"
  else
    check "work branch '$BRANCH' pushed to origin" "no" "not found on remote"
  fi

  local pr_num
  pr_num="$(gh pr list --head "$BRANCH" --state all \
    --json number --jq '.[0].number // empty' 2>/dev/null || true)"

  if [[ -z "$pr_num" ]]; then
    check "a PR exists for '$BRANCH'" "no" "gh pr list returned nothing"
    summarize
    return
  fi
  check "a PR exists for '$BRANCH' (#$pr_num)" "yes"

  # gh's built-in --jq keeps standalone jq off the dependency list.
  local me pr_author pr_body
  me="$(gh api user --jq .login)"
  pr_author="$(gh pr view "$pr_num" --json author --jq '.author.login // ""')"
  pr_body="$(gh pr view "$pr_num" --json body --jq '.body // ""')"

  # Silent path: run-plan authored the PR itself via gh pr create.
  [[ "$pr_author" == "$me" ]] \
    && check "PR authored by you (silent path used gh pr create)" "yes" \
    || check "PR authored by you (silent path used gh pr create)" "no" "author was '$pr_author'"

  grep -q "Closes #$ISSUE_NUM" <<<"$pr_body" \
    && check "PR body links 'Closes #$ISSUE_NUM'" "yes" \
    || check "PR body links 'Closes #$ISSUE_NUM'" "no" "line missing"

  # No parent PRD-epic exists, so the Refs line must be omitted entirely.
  grep -qE '^Refs #' <<<"$pr_body" \
    && check "PR body omits 'Refs #' (no parent epic)" "no" "a Refs line is present" \
    || check "PR body omits 'Refs #' (no parent epic)" "yes"

  # The provenance footer belongs only to the declared path.
  grep -qi "opened automatically" <<<"$pr_body" \
    && check "PR body omits the provenance footer" "no" "footer present on a silent-repo PR" \
    || check "PR body omits the provenance footer" "yes"

  # Every acceptance criterion should be ticked on the synced issue body.
  local unchecked
  unchecked="$(gh issue view "$ISSUE_NUM" --json body --jq .body | grep -c '^- \[ \]' || true)"
  [[ "$unchecked" -eq 0 ]] \
    && check "all acceptance criteria ticked on issue #$ISSUE_NUM" "yes" \
    || check "all acceptance criteria ticked on issue #$ISSUE_NUM" "no" "$unchecked still unchecked"

  # Scratch never reaches the index.
  grep -q "scratch" "$(git rev-parse --git-path info/exclude)" 2>/dev/null \
    && check "scratch root added to .git/info/exclude" "yes" \
    || check "scratch root added to .git/info/exclude" "no" "not found"

  summarize
}

summarize() {
  echo ""
  echo "  $PASS passed, $FAIL failed"
  echo ""
  if [[ $FAIL -gt 0 ]]; then
    echo "A failure here is a finding about the skill OR about the fixture — read the"
    echo "run transcript before concluding which. Attribution does not automate."
    echo ""
    exit 1
  fi
  echo "Update the branch register in BURN-IN.md with what this run exercised."
  echo ""
}

# ---------------------------------------------------------------- teardown

cmd_teardown() {
  local name="${1:-}"
  [[ -n "$name" ]] || die "Usage: $0 teardown <name>"
  load_meta "$name"

  cat <<EOF

Teardown is manual — this script deletes nothing on your behalf.

  gh repo delete $REPO_SLUG --yes
  rm -rf $FIXTURE_DIR
  rm -f $(meta_path "$name") $BURN_IN_DIR/$name.snapshot

Copy anything worth keeping out of $FIXTURE_DIR/BURN-IN.md first — the branch
register is the part worth carrying into the next fixture.

EOF
}

# ---------------------------------------------------------------- dispatch

case "$CMD" in
  setup)    cmd_setup "${2:-}" "${3:-}" ;;
  probe)    cmd_probe "${2:-}" "${3:-}" ;;
  restore)  cmd_restore "${2:-}" ;;
  snapshot) cmd_snapshot "${2:-}" ;;
  verify)   cmd_verify "${2:-}" ;;
  teardown) cmd_teardown "${2:-}" ;;
  ""|-h|--help|help)
    sed -n '2,33p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    ;;
  *)
    die "Unknown command '$CMD'. Run '$0 --help'."
    ;;
esac
