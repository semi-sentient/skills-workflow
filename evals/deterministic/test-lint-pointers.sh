#!/usr/bin/env bash
# Deterministic test for evals/lint.py's section-pointer rule: a throwaway skill whose
# `<file>.md → <Section>` pointers resolve, then one each of the shapes issue #25 found
# broken (a bold paragraph lead, a pointer that names no heading, a file not in references/).
#
#   ./evals/deterministic/test-lint-pointers.sh      # exit 0 = all passed
set -u

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/lint-test.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
pass=0; fail=0
check() { # name, condition-exit-code, evidence
  if [ "$2" -eq 0 ]; then pass=$((pass + 1)); printf '  ok   %s\n' "$1"; else fail=$((fail + 1)); printf '  FAIL %s\n       %s\n' "$1" "$3"; fi
}
lint() { "$REPO/evals/lint.py" --file "$WORK/s/SKILL.md" --only section-pointer 2>&1; }

mkdir -p "$WORK/s/references"
cat > "$WORK/s/references/ops.md" <<'REF'
# Ops

## Budgets

**Retry limit.** A bold lead, not a heading.

### Corrective-pass budget

## Scoped Re-review Exceptions (Step 4 item 5)

```md
## Fenced heading
```
REF
good='---
name: s
description: "Test skill."
---

See ops.md → Corrective-pass budget, then **read ops.md → Scoped Re-review Exceptions** and
[ops.md → Budgets](ops.md#budgets). A slug example is not a pointer: `a-plan.md` → `a`.'
printf '%s\n' "$good" > "$WORK/s/SKILL.md"
out="$(lint)"; rc=$?
check "pointers to ##/### headings (by name before ' (') pass" $([ $rc -eq 0 ] && echo 0 || echo 1) "$out"

for bad in 'ops.md → Retry limit' 'ops.md → Fenced heading' 'ops.md → Plan drift first' 'missing.md → Budgets'; do
  printf '%s\n\n%s.\n' "$good" "$bad" > "$WORK/s/SKILL.md"
  out="$(lint)"; rc=$?
  check "'$bad' fails" $([ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'section-pointer' && echo 0 || echo 1) "$out"
done

printf '%s\n' "$good" > "$WORK/s/SKILL.md"
printf '\nSee ops.md → Retry limit.\n' >> "$WORK/s/references/ops.md"
out="$(lint)"; rc=$?
check "a broken pointer inside a reference file fails too" $([ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'ops.md:' && echo 0 || echo 1) "$out"

printf '\n%d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
