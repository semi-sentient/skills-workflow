#!/usr/bin/env bash
# rp.sh — run-plan's per-run helper. `init` copies it verbatim into <scratch_dir>;
# every later call is `bash <scratch_dir>/rp.sh <command> …`. The orchestrator never
# edits this file: the copy under the skill's references/ is the source.
#
# Commands (paths are relative to the run's scratch directory unless stated):
#   init <skill_dir> <scratch_dir> <plan_file> [issue]
#                    copy this script and the brief templates into <scratch_dir>, write
#                    run.env, create the ledger header, extract plan-index.md and the
#                    phase-<n>-spec.md files, print the phase summary
#   extract          rewrite plan-index.md and phase-<n>-spec.md from the plan file
#   phases           one phase id per line (1, 2, 6A, …)
#   criteria <n>     the labelled criteria of phase <n>
#   tick <n> <k>…    check criteria C<k> of phase <n> in the plan file, then re-extract
#   untick <n> <k>…  uncheck criteria C<k> of phase <n>, then re-extract
#   ledger <phase> <mode> <tokens> <tool_uses> <duration_ms> [group] [note]
#                    append one usage row to ledger.md
#   phase-cost <n>   `| Research | Code | Review | Total | Active time |` cells for phase <n>;
#                    warns when the phase has more review evidence files than Review rows
#   stage            git add -A from the repo root, excluding every keep-dirty path in
#                    tree-state.md (each exclusion is its own literal pathspec)
#   delta            names-only unstaged + untracked delta since the last staging, minus
#                    the plan file and keep-dirty paths, one path per line
#   baselines        for each delta path, save its index content to baseline-<flattened
#                    path>; prints "<path><TAB>baseline-…", "<path><TAB>new", or
#                    "<path><TAB>deleted"; warns and saves nothing when there is no delta
#   review-path <n>  print the next evidence path for phase <n> (highest suffix + 1,
#                    rm -f'd first so a stale file can never satisfy the existence check)
#   evidence <path> <findings>
#                    exit 0 when the evidence file exists, holds at least one C<k> row,
#                    and names at least <findings> F<k> findings; exit 1 otherwise
#   sync             push the plan file to the GH issue body, 4 attempts with backoff;
#                    exit 1 on persistent failure; a no-op on a local-only run
#   drift            compare the GH body with the local plan (footer lines and CR ignored):
#                    identical | local-ahead <k> | gh-ahead <k> | differ; the fetched
#                    body is left in gh-body.md
#   pull             overwrite the local plan with gh-body.md, keeping the local footer
#   cleanup <n>      rm phase-<n>-commit-msg.md and every baseline-* file
#   brief <template> <out> KEY=VALUE|KEY=@file …
#                    fill briefs/<template> into <out>; every {{KEY}} the template names
#                    must be supplied (a value starting with a literal @ is written @@)
#   help             this text
#
# Plan shape: phases are `## Phase <id>` or `## Part <id>` H2 headings (id = digits plus
# an optional letter); criteria are the `- [ ]` / `- [x]` lines under a phase's
# `### Acceptance criteria` heading. Portability: bash 3.2+, BSD or GNU awk/sed/grep,
# git; gh for sync/drift.

set -eu

die() { printf 'rp.sh: %s\n' "$*" >&2; exit 1; }
warn() { printf 'rp.sh: warning: %s\n' "$*" >&2; }

SELF="$(cd "$(dirname "$0")" && pwd -P)/$(basename "$0")"
SCRATCH="$(dirname "$SELF")"
SEP="$(printf '\001')"   # field separator for the annotated stream — a TAB can occur in plan text

load_env() {
  [ -f "$SCRATCH/run.env" ] || die "run.env missing in $SCRATCH — run: bash <skill_dir>/references/rp.sh init …"
  # shellcheck disable=SC1090
  . "$SCRATCH/run.env"
  : "${PLAN_FILE:?run.env has no PLAN_FILE}"
  [ -f "$PLAN_FILE" ] || die "plan file not found: $PLAN_FILE"
}

sq() { printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"; }

# Write stdin over the plan file through its symlink, if it is one.
write_plan() { cat > "$PLAN_FILE.rp-tmp" && cat "$PLAN_FILE.rp-tmp" > "$PLAN_FILE" && rm -f "$PLAN_FILE.rp-tmp"; }

# ------------------------------------------------------------------ plan parsing

AWK_PHASE_LIB='
function is_phase(line) { return line ~ /^## (Phase|Part) [0-9]+[A-Za-z]?([^A-Za-z0-9]|$)/ }
function phase_id(line,   s) { s = line; sub(/^## (Phase|Part) /, "", s); sub(/[^A-Za-z0-9].*$/, "", s); return s }
function is_footer(line) { return line ~ /^<!-- gh-(sub-)?issue: [0-9]+ -->[[:space:]]*$/ }
function is_criterion(line) { return line ~ /^- \[[ xX]\] / }
function is_nested_box(line) { return line ~ /^[[:space:]]+- \[[ xX]\] / }
function is_continuation(line) { return line ~ /^[[:space:]]+[^[:space:]]/ && line !~ /^[[:space:]]+- \[/ }
function is_ac_heading(line) { return tolower(line) ~ /^### acceptance criteria/ }
function is_fence(line) { return line ~ /^[[:space:]]*(```|~~~)/ }
function crit_text(line,   s) { s = line; sub(/^- \[[ xX]\] /, "", s); return s }
function crit_mark(line) { return substr(line, 1, 5) }
function is_human(text,   s) { s = text; gsub(/^[*`_ ]+/, "", s); return tolower(s) ~ /^human / }
'

# Emits one record per plan line: "<phase-id>␁<kind>␁<k>␁<line>" (␁ = \001), kind in
# heading | ac-heading | crit | cont | body | footer; k = criterion number for
# crit/cont, else 0; phase-id "-" outside any phase. A trailing CR is dropped from
# every line. Two passes over the file: the first learns which phases carry an
# Acceptance-criteria heading. Lines inside a fenced code block are body.
annotate() {
  awk -v warn="${1:-0}" -v SEP="$SEP" "$AWK_PHASE_LIB"'
  { sub(/\r$/, "") }
  FNR == NR {
    if (is_fence($0)) { fence1 = !fence1; next }
    if (fence1) next
    if (is_phase($0)) p = phase_id($0)
    else if ($0 ~ /^## / || is_footer($0)) p = ""
    else if (p != "" && is_ac_heading($0)) hasac[p] = 1
    next
  }
  FNR == 1 { pid = "-"; k = 0; inac = 0; last = "body"; fence = 0 }
  {
    line = $0; kind = "body"
    if (is_fence(line)) { fence = !fence }
    else if (fence) kind = "body"
    else if (is_footer(line)) { pid = "-"; inac = 0; kind = "footer" }
    else if (is_phase(line)) { pid = phase_id(line); k = 0; inac = 0; kind = "heading" }
    else if (pid == "-") kind = "body"
    else if (line ~ /^## /) { pid = "-"; inac = 0 }
    else if (is_ac_heading(line)) { inac = 1; kind = "ac-heading" }
    else if (line ~ /^### /) inac = 0
    else if (is_criterion(line) && (inac || !hasac[pid])) { k++; kind = "crit" }
    else if (is_criterion(line) && warn) printf "rp.sh: warning: phase %s has a checkbox line outside its Acceptance criteria section; it is not a criterion: %s\n", pid, substr(line, 1, 60) > "/dev/stderr"
    else if (inac && is_nested_box(line) && warn) { printf "rp.sh: warning: phase %s has a nested checkbox under a criterion; it is not labelled and cannot be ticked: %s\n", pid, substr(line, 1, 60) > "/dev/stderr"; if (k > 0 && (last == "crit" || last == "cont")) kind = "cont" }
    else if (k > 0 && is_continuation(line) && (last == "crit" || last == "cont")) kind = "cont"
    print pid SEP kind SEP ((kind == "crit" || kind == "cont") ? k : 0) SEP line
    last = kind
  }' "$PLAN_FILE" "$PLAN_FILE"
}

# Drop trailing blank / `---` lines from stdin.
trim_tail() { awk '{ sub(/\r$/, ""); buf[++n] = $0 } END { while (n > 0 && (buf[n] == "" || buf[n] == "---")) n--; for (i = 1; i <= n; i++) print buf[i] }'; }

extract() {
  load_env
  local tsv="$SCRATCH/.annotated.tsv"
  annotate "${1:-0}" > "$tsv"
  local ids
  ids="$(awk -F"$SEP" '$2 == "heading" { print $1 }' "$tsv")"
  [ -n "$ids" ] || { rm -f "$tsv"; die "no phases found in $PLAN_FILE — phases must be H2 headings of the form '## Phase 3:', '## Phase 6A:', or '## Part 2 —' (digits plus an optional letter); rename the plan's phase headings, or ask the user to"; }
  if printf '%s\n' "$ids" | sort | uniq -d | grep -q .; then
    rm -f "$tsv"; die "duplicate phase ids in $PLAN_FILE: $(printf '%s\n' "$ids" | sort | uniq -d | tr '\n' ' ')"
  fi

  rm -f "$SCRATCH"/phase-*-spec.md
  local stamp id
  stamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  for id in $ids; do
    awk -F"$SEP" -v id="$id" -v plan="$PLAN_FILE" -v stamp="$stamp" "$AWK_PHASE_LIB"'
      $1 != id { next }
      $2 == "heading" {
        print "<!-- Extracted by run-plan (rp.sh) from " plan " at " stamp ". The (C<k>) labels on the criteria exist for the return contract; every other character is the plan'"'"'s own text. Cross-phase decisions: read `## Architectural decisions` in the plan file. -->"
        print ""; print $4; next
      }
      $2 == "crit" { print crit_mark($4) " (C" $3 ") " crit_text($4); next }
      { print $4 }
    ' "$tsv" | trim_tail > "$SCRATCH/phase-$id-spec.md"
  done

  {
    awk -F"$SEP" '
      $1 == "-" && $2 == "body" && $4 ~ /^# / && !h1 { print $4; h1 = 1; next }
      $1 == "-" && $2 == "body" && $4 ~ /^> Source PRD:/ { print $4 }
    ' "$tsv"
    awk -F"$SEP" -v plan="$PLAN_FILE" '
      $2 == "heading" { phases++ }
      $2 == "crit" { crit++; if ($4 ~ /^- \[[xX]\]/) done++ }
      END { printf "\nPlan file: %s · Phases: %d · Criteria: %d (%d checked)\n\n", plan, phases, crit, done }
    ' "$tsv"
    awk -F"$SEP" '
      $1 == "-" && $2 == "body" && $4 ~ /^## Architectural decisions/ { on = 1; print $4; next }
      on && $4 ~ /^## / { on = 0 }
      on && $2 == "body" && $4 != "---" { print $4 }
    ' "$tsv" | trim_tail
    printf '\n## Phases\n'
    awk -F"$SEP" "$AWK_PHASE_LIB"'
      function flush() {
        if (pid == "") return
        printf "\n### %s — %d criteria (%d checked) — spec: phase-%s-spec.md\n", heading, n, done, pid
        if (risk != "") print risk
        if (human != "") print "Human-form criteria: " human
        if (literal) print "Human-gate literal: " (confirmed ? "confirmed" : "UNRESOLVED — ask which non-Human criteria are human-form (SKILL.md Step 3 batch)")
        for (i = 1; i <= m; i++) print lines[i]
      }
      $2 == "heading" { flush(); pid = $1; heading = $4; sub(/^## /, "", heading); n = 0; done = 0; m = 0; risk = ""; human = ""; literal = 0; confirmed = 0; next }
      pid == "" || $1 != pid { next }
      {
        low = tolower($4)
        if (low ~ /known risk|human gate|not agent-completable/) literal = 1
        if (low ~ /\(human-form set confirmed\)/) confirmed = 1
      }
      $2 == "body" && $4 ~ /^\*\*Known risk\*\*/ { risk = $4 }
      $2 == "crit" {
        n++; if ($4 ~ /^- \[[xX]\]/) done++
        t = crit_text($4)
        if (is_human(t)) human = human (human == "" ? "" : " ") "C" $3
        lines[++m] = crit_mark($4) " (C" $3 ") " t; next
      }
      $2 == "cont" { lines[++m] = $4 }
      END { flush() }
    ' "$tsv"
  } > "$SCRATCH/plan-index.md"
  if [ "${1:-0}" = 1 ] && ! grep -q '^## Architectural decisions' "$SCRATCH/plan-index.md"; then
    warn "the plan has no '## Architectural decisions' heading; plan-index.md carries no cross-phase decisions — ask the user which section holds them, or whether there are none"
  fi
  rm -f "$tsv"
}

assert_phase() {
  local id="$1"
  annotate | awk -F"$SEP" -v id="$id" '$2 == "heading" && $1 == id { f = 1 } END { exit !f }' || die "no phase '$id' in $PLAN_FILE (have: $(annotate | awk -F"$SEP" '$2 == "heading" { printf "%s ", $1 }'))"
}

cmd_phases() { load_env; annotate | awk -F"$SEP" '$2 == "heading" { print $1 }'; }

cmd_criteria() {
  load_env
  local id="${1:?usage: rp.sh criteria <n>}"
  assert_phase "$id"
  annotate | awk -F"$SEP" -v id="$id" "$AWK_PHASE_LIB"'
    $1 == id && $2 == "crit" { print crit_mark($4) " (C" $3 ") " crit_text($4) }
    $1 == id && $2 == "cont" { print $4 }'
}

set_tick() {
  load_env
  local state="$1"; shift
  local id="${1:?usage: rp.sh tick|untick <n> <k>…}"; shift
  [ $# -gt 0 ] || die "tick/untick: name at least one criterion number"
  local k; for k in "$@"; do case "$k" in ''|*[!0-9]*) die "tick/untick: '$k' is not a criterion number (pass 3, not C3)" ;; esac; done
  assert_phase "$id"
  local want=" $* "
  annotate | awk -F"$SEP" -v id="$id" -v want="$want" -v state="$state" '
    {
      line = $4
      if ($1 == id && $2 == "crit" && index(want, " " $3 " ")) {
        hit[$3] = 1
        if (state == "x") sub(/^- \[ \]/, "- [x]", line); else sub(/^- \[[xX]\]/, "- [ ]", line)
      }
      print line
    }
    END {
      n = split(want, w, " ")
      for (i = 1; i <= n; i++) if (w[i] != "" && !hit[w[i]]) { printf "rp.sh: phase %s has no criterion C%s\n", id, w[i] > "/dev/stderr"; bad = 1 }
      exit bad
    }
  ' > "$PLAN_FILE.rp-tick" || { rm -f "$PLAN_FILE.rp-tick"; exit 1; }
  write_plan < "$PLAN_FILE.rp-tick"; rm -f "$PLAN_FILE.rp-tick"
  extract
}

# ---------------------------------------------------------------------- ledger

LEDGER_HEADER='| Phase | Mode | Tokens | Tool uses | duration_ms | Parallel group | Note |
| ----- | ---- | -----: | --------: | ----------: | -------------- | ---- |'

ensure_ledger() { [ -f "$SCRATCH/ledger.md" ] || printf '%s\n' "$LEDGER_HEADER" > "$SCRATCH/ledger.md"; }

cmd_ledger() {
  [ $# -ge 5 ] || die "usage: rp.sh ledger <phase> <mode> <tokens> <tool_uses> <duration_ms> [group] [note]"
  ensure_ledger
  printf '| %s | %s | %s | %s | %s | %s | %s |\n' "$1" "$2" "$3" "$4" "$5" "${6:-}" "${7:-}" >> "$SCRATCH/ledger.md"
}

# Per-agent figures stay per-agent (dot-separated in spawn order); only Total sums.
# Architect lands in the Research column, Debug and retries in Code. Active time sums
# duration_ms with rows sharing a Parallel group counted at the group's max. A column
# with nothing numeric to sum prints n/a, never a fabricated zero.
cmd_phase_cost() {
  local id="${1:?usage: rp.sh phase-cost <n>}"
  ensure_ledger
  # Every Review return owes a ledger row; the evidence files count the returns.
  local files=0 rows f
  for f in "$SCRATCH/phase-$id-review.md" "$SCRATCH/phase-$id-review-"*.md; do [ -e "$f" ] && files=$((files + 1)); done
  rows="$(awk -F'|' -v id="$id" 'function trim(s) { gsub(/^[[:space:]]+|[[:space:]]+$/, "", s); return s } NR > 2 && trim($2) == id && trim($3) == "Review" { n++ } END { print n + 0 }' "$SCRATCH/ledger.md")"
  [ "$files" -le "$rows" ] || warn "phase $id has $files review evidence file(s) but $rows Review ledger row(s) — a Review return went unrecorded; add it with: rp.sh ledger $id Review <tokens> <tool_uses> <duration_ms>"
  awk -F'|' -v id="$id" '
    function trim(s) { gsub(/^[[:space:]]+|[[:space:]]+$/, "", s); return s }
    function fmtk(v, multi) { if (v !~ /^[0-9]+$/) return "n/a"; return multi ? sprintf("%dK", (v + 500) / 1000) : sprintf("%.1fK", v / 1000) }
    function hms(ms,   s) { s = int(ms / 1000); return sprintf("%d:%02d:%02d", s / 3600, (s % 3600) / 60, s % 60) }
    function col(mode) { if (mode == "Research" || mode == "Architect") return "Research"; if (mode == "Review") return "Review"; return "Code" }
    NR <= 2 { next }
    trim($2) != id { next }
    {
      mode = trim($3); tok = trim($4); dur = trim($6); grp = trim($7)
      c = col(mode); n[c]++; v[c, n[c]] = tok
      if (tok ~ /^[0-9]+$/) { total += tok; anytok = 1 }
      if (dur ~ /^[0-9]+$/) {
        dur += 0; anydur = 1
        if (grp == "") solo += dur
        else { if (!(grp in gmax) || dur > gmax[grp]) gmax[grp] = dur; gsum[grp] += dur; gcount[grp]++ }
      }
      rows++
    }
    END {
      if (!rows) { print "| — | — | — | — | — |"; exit }
      split("Research Code Review", cols, " ")
      for (k = 1; k <= 3; k++) {
        c = cols[k]
        if (!n[c]) { cell[c] = "—"; continue }
        s = ""
        for (i = 1; i <= n[c]; i++) s = s (i > 1 ? "·" : "") fmtk(v[c, i], n[c] > 1)
        cell[c] = s
      }
      active = solo; sum = solo; groups = 0
      for (g in gmax) { active += gmax[g]; sum += gsum[g]; if (gcount[g] > 1) groups++ }
      t = !anydur ? "n/a" : (groups ? sprintf("%s (Σ %s, %d parallel group%s)", hms(active), hms(sum), groups, groups > 1 ? "s" : "") : hms(active))
      printf "| %s | %s | %s | %s | %s |\n", cell["Research"], cell["Code"], cell["Review"], anytok ? sprintf("%.1fK", total / 1000) : "n/a", t
    }
  ' "$SCRATCH/ledger.md"
}

# --------------------------------------------------------------------- git side

# The repository is the one `init` ran in, recorded in run.env — never the caller's
# cwd, which a persistent shell can leave anywhere.
repo_top() {
  [ -n "${REPO_TOP:-}" ] || die "run.env has no REPO_TOP — rp.sh init did not run inside a git repository"
  [ -d "$REPO_TOP/.git" ] || git -C "$REPO_TOP" rev-parse --git-dir >/dev/null 2>&1 || die "recorded repository $REPO_TOP is not a git repository"
  printf '%s\n' "$REPO_TOP"
}

# Every keep-dirty path the working-tree triage recorded, one per line, unquoted,
# relative to the repo root (porcelain paths, which is what the triage records).
keep_dirty_paths() {
  [ -f "$SCRATCH/tree-state.md" ] || return 0
  sed -n 's/^keep-dirty: //p' "$SCRATCH/tree-state.md"
}

# EXCL holds one ':(exclude,literal)<path>' argv word per keep-dirty path. Quoting
# inside the string would be wrong (':(exclude)"a b.md"' exits 0 and stages the file
# anyway), and without `literal` a path with [ ] * ? is a glob that excludes siblings.
EXCL=()
build_excl() {
  EXCL=()
  local p
  while IFS= read -r p; do
    if [ -n "$p" ]; then EXCL[${#EXCL[@]}]=":(exclude,literal)$p"; fi
  done <<EOF
$(keep_dirty_paths)
EOF
  return 0
}

assert_scratch_ignored() {
  local top="$1"
  case "$SCRATCH/" in
    "$top"/*) git -C "$top" check-ignore -q "$SCRATCH/probe" || die "$SCRATCH is inside the repo but not git-ignored — append its scratch root to \$(git rev-parse --git-path info/exclude) first" ;;
  esac
}

cmd_stage() {
  load_env
  local top; top="$(repo_top)"
  assert_scratch_ignored "$top"
  build_excl
  git -C "$top" add -A -- . ${EXCL[@]+"${EXCL[@]}"}
}

# Unquoted paths (core.quotePath=false) so non-ASCII names round-trip to `git show`.
cmd_delta() {
  load_env
  local top; top="$(repo_top)"
  build_excl
  local plan_phys plan_rel
  plan_phys="$(cd "$(dirname "$PLAN_FILE")" && pwd -P)/$(basename "$PLAN_FILE")"
  plan_rel="${plan_phys#"$top"/}"
  {
    git -C "$top" -c core.quotePath=false diff --name-only -- . ${EXCL[@]+"${EXCL[@]}"}
    git -C "$top" -c core.quotePath=false ls-files --others --exclude-standard -- . ${EXCL[@]+"${EXCL[@]}"}
  } | awk -v plan="$plan_rel" 'NF && $0 != plan && !seen[$0]++'
}

baseline_name() { printf 'baseline-%s\n' "$(printf '%s' "$1" | sed 's#/#__#g')"; }

cmd_baselines() {
  load_env
  local top; top="$(repo_top)"
  local p base delta
  delta="$(cmd_delta)"
  [ -n "$delta" ] || { warn "baselines: no delta since the last staging — run this after the fix agent returns and before rp.sh stage"; return 0; }
  printf '%s\n' "$delta" | while IFS= read -r p; do
    base="$(baseline_name "$p")"
    if [ ! -e "$top/$p" ]; then
      rm -f "$SCRATCH/$base"; printf '%s\tdeleted\n' "$p"
    elif git -C "$top" show ":$p" > "$SCRATCH/$base" 2>/dev/null; then
      printf '%s\t%s\n' "$p" "$base"
    else
      rm -f "$SCRATCH/$base"; printf '%s\tnew\n' "$p"
    fi
  done
}

cmd_review_path() {
  local id="${1:?usage: rp.sh review-path <n>}"
  local max=0 f n
  for f in "$SCRATCH/phase-$id-review.md" "$SCRATCH/phase-$id-review-"*.md; do
    [ -e "$f" ] || continue
    n="${f##*/phase-$id-review}"; n="${n%.md}"; n="${n#-}"
    [ -z "$n" ] && n=1
    case "$n" in *[!0-9]*) continue ;; esac
    [ "$n" -gt "$max" ] && max=$n
  done
  local path
  if [ "$max" -eq 0 ]; then path="$SCRATCH/phase-$id-review.md"; else path="$SCRATCH/phase-$id-review-$((max + 1)).md"; fi
  rm -f "$path"
  printf '%s\n' "$path"
}

# The findings the reviewer returned must also be in the evidence file, because the
# fix agent reads them there and the orchestrator never does.
cmd_evidence() {
  local path="${1:?usage: rp.sh evidence <path> <findings-count>}" want="${2:?evidence: missing <findings-count>}"
  case "$want" in ''|*[!0-9]*) die "evidence: '$want' is not a count" ;; esac
  [ -s "$path" ] || die "evidence: $path is missing or empty — incomplete review"
  local rows f
  rows="$(grep -cE '(^|[^A-Za-z0-9])C[0-9]+([^0-9]|$)' "$path" || true)"
  f="$(grep -oE '(^|[^A-Za-z0-9])F[0-9]+([^0-9]|$)' "$path" | grep -oE 'F[0-9]+' | sort -u | wc -l | tr -d ' ')"
  [ "$rows" -ge 1 ] || die "evidence: $path has no C<k> verdict row — incomplete review"
  [ "$f" -ge "$want" ] || die "evidence: $path names $f distinct F<k> finding(s), the return named $want — incomplete review"
  echo "evidence ok: $rows C<k> row line(s), $f finding(s)"
}

cmd_cleanup() {
  local id="${1:?usage: rp.sh cleanup <n>}"
  rm -f "$SCRATCH/phase-$id-commit-msg.md"
  find "$SCRATCH" -maxdepth 1 -name 'baseline-*' -delete
}

# ----------------------------------------------------------------------- GitHub

strip_footer() { tr -d '\r' < "$1" | grep -vE '^<!-- gh-(sub-)?issue: [0-9]+ -->[[:space:]]*$' | trim_tail; }
neutral() { strip_footer "$1" | sed 's/^- \[[xX]\] /- [ ] /'; }
ticks() { strip_footer "$1" | grep -cE '^- \[[xX]\] ' || true; }

cmd_sync() {
  load_env
  if [ -z "${ISSUE:-}" ]; then echo "local-only run: nothing to sync"; return 0; fi
  local delay err=""
  for delay in 0.25 1 3 0; do
    if err="$(gh issue edit "$ISSUE" --body-file "$PLAN_FILE" 2>&1)"; then echo "synced #$ISSUE"; return 0; fi
    [ "$delay" = 0 ] || sleep "$delay"
  done
  printf 'rp.sh: sync to #%s failed after 4 attempts: %s\n' "$ISSUE" "$err" >&2
  return 1
}

cmd_drift() {
  load_env
  [ -n "${ISSUE:-}" ] || die "drift: local-only run (no ISSUE in run.env)"
  gh issue view "$ISSUE" --json body --jq .body | tr -d '\r' > "$SCRATCH/gh-body.md" || die "drift: could not fetch #$ISSUE"
  if cmp -s <(strip_footer "$PLAN_FILE") <(strip_footer "$SCRATCH/gh-body.md"); then echo identical; return 0; fi
  if cmp -s <(neutral "$PLAN_FILE") <(neutral "$SCRATCH/gh-body.md"); then
    local lc gc; lc="$(ticks "$PLAN_FILE")"; gc="$(ticks "$SCRATCH/gh-body.md")"
    if [ "$lc" -gt "$gc" ]; then echo "local-ahead $((lc - gc))"; elif [ "$gc" -gt "$lc" ]; then echo "gh-ahead $((gc - lc))"; else echo differ; fi
    return 0
  fi
  echo differ
}

cmd_pull() {
  load_env
  [ -f "$SCRATCH/gh-body.md" ] || die "pull: run 'rp.sh drift' first"
  local footer; footer="$(grep -E '^<!-- gh-(sub-)?issue: [0-9]+ -->' "$PLAN_FILE" | tr -d '\r' || true)"
  { strip_footer "$SCRATCH/gh-body.md"; if [ -n "$footer" ]; then echo; printf '%s\n' "$footer"; fi; } | write_plan
  extract
}

# ----------------------------------------------------------------------- briefs

# Keys whose value must name an existing file: the agent will read it.
BRIEF_INPUT_KEYS=" CONVENTIONS_PATH SPEC_PATH PLAN_FILE PRIOR_EVIDENCE CODE_BRIEF_PATH "

cmd_brief() {
  local tpl="${1:?usage: rp.sh brief <template> <out> KEY=VALUE|KEY=@file …}" out="${2:?brief: missing <out>}"; shift 2
  local src="$SCRATCH/briefs/$tpl"
  [ -f "$src" ] || die "no template briefs/$tpl (have: $(ls "$SCRATCH/briefs" 2>/dev/null | tr '\n' ' '))"
  local keys="" kv key val
  for kv in "$@"; do
    case "$kv" in *=*) ;; *) die "brief: expected KEY=VALUE, got '$kv'" ;; esac
    key="${kv%%=*}"; val="${kv#*=}"
    case "$key" in ""|*[!A-Z0-9_]*) die "brief: key '$key' must be UPPER_SNAKE" ;; esac
    case "$val" in
      @@*) val="${val#@}" ;;
      @*) [ -f "${val#@}" ] || die "brief: no file ${val#@} for $key"; val="$(cat "${val#@}")" ;;
    esac
    case "$BRIEF_INPUT_KEYS" in *" $key "*) [ -f "$val" ] || die "brief: $key names $val, which does not exist — the agent would read a missing file" ;; esac
    export "RP_TPL_$key=$val"
    keys="$keys $key"
  done
  # Every placeholder the template names must be supplied; a value may contain {{…}}.
  local needed missing="" k
  needed="$(grep -oE '\{\{[A-Z0-9_]+\}\}' "$src" | tr -d '{}' | sort -u || true)"
  for k in $needed; do case "$keys" in *" $k"*) ;; *) missing="$missing $k" ;; esac; done
  [ -z "$missing" ] || die "brief: unfilled placeholders in $tpl:$missing"
  case "$out" in /*) ;; *) out="$SCRATCH/$out" ;; esac
  # One left-to-right pass per line: a substituted value is never rescanned.
  awk -v keys="$keys" '
    BEGIN { n = split(keys, k, " "); for (i = 1; i <= n; i++) if (k[i] != "") have[k[i]] = 1 }
    {
      line = $0; out = ""
      while ((p = index(line, "{{")) > 0) {
        rest = substr(line, p + 2)
        q = index(rest, "}}")
        if (q == 0) break
        key = substr(rest, 1, q - 1)
        if (key in have) { out = out substr(line, 1, p - 1) ENVIRON["RP_TPL_" key]; line = substr(rest, q + 2) }
        else { out = out substr(line, 1, p + 1); line = rest }
      }
      print out line
    }
  ' "$src" > "$out.rp-tmp"
  mv "$out.rp-tmp" "$out"
  printf '%s (%s bytes)\n' "$out" "$(wc -c < "$out" | tr -d ' ')"
}

# ------------------------------------------------------------------------- init

cmd_init() {
  local skill="${1:?usage: rp.sh init <skill_dir> <scratch_dir> <plan_file> [issue]}" scratch="${2:?init: missing <scratch_dir>}" plan="${3:?init: missing <plan_file>}" issue="${4:-}"
  [ -f "$skill/references/rp.sh" ] || die "init: $skill/references/rp.sh not found — pass the skill's base directory"
  [ -d "$skill/references/briefs" ] || die "init: $skill/references/briefs/ not found"
  [ -f "$plan" ] || die "init: plan file not found: $plan"
  case "$issue" in ''|*[!0-9]*) [ -z "$issue" ] || die "init: issue must be a bare number, got '$issue'" ;; esac
  local top; top="$(git rev-parse --show-toplevel 2>/dev/null || true)"
  mkdir -p "$scratch/briefs"
  scratch="$(cd "$scratch" && pwd -P)"
  skill="$(cd "$skill" && pwd -P)"
  plan="$(cd "$(dirname "$plan")" && pwd -P)/$(basename "$plan")"
  cp "$skill/references/rp.sh" "$scratch/rp.sh"
  rm -f "$scratch"/briefs/*.md
  cp "$skill"/references/briefs/*.md "$scratch/briefs/"
  {
    printf 'PLAN_FILE=%s\n' "$(sq "$plan")"
    printf 'ISSUE=%s\n' "$(sq "$issue")"
    printf 'SKILL_DIR=%s\n' "$(sq "$skill")"
    printf 'REPO_TOP=%s\n' "$(sq "$top")"
    printf 'RUN_START=%s\n' "$(date +%s)"
  } > "$scratch/run.env"
  [ -n "$top" ] || warn "init ran outside a git repository; stage/delta/baselines will refuse to run"
  [ -f "$scratch/ledger.md" ] || printf '%s\n' "$LEDGER_HEADER" > "$scratch/ledger.md"
  bash "$scratch/rp.sh" extract 1
  echo "run directory: $scratch"
  sed -n '1p;/^Plan file:/p' "$scratch/plan-index.md"
  grep -E '^### |^Human-form|^Human-gate' "$scratch/plan-index.md"
}

# ------------------------------------------------------------------------- main

cmd="${1:-help}"; [ $# -gt 0 ] && shift
case "$cmd" in
  init)        cmd_init "$@" ;;
  extract)     extract 1 ;;
  phases)      cmd_phases ;;
  criteria)    cmd_criteria "$@" ;;
  tick)        set_tick x "$@" ;;
  untick)      set_tick " " "$@" ;;
  ledger)      cmd_ledger "$@" ;;
  phase-cost)  cmd_phase_cost "$@" ;;
  stage)       cmd_stage ;;
  delta)       cmd_delta ;;
  baselines)   cmd_baselines ;;
  review-path) cmd_review_path "$@" ;;
  evidence)    cmd_evidence "$@" ;;
  sync)        cmd_sync ;;
  drift)       cmd_drift ;;
  pull)        cmd_pull ;;
  cleanup)     cmd_cleanup "$@" ;;
  brief)       cmd_brief "$@" ;;
  help|-h|--help) sed -n '2,/^# git; gh for/p' "$SELF" | sed 's/^# \{0,1\}//' ;;
  *) die "unknown command '$cmd' (try: rp.sh help)" ;;
esac
