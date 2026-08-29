#!/usr/bin/env bash
# List upstream commits not yet reviewed for a forked skill.
#
#   scripts/upstream-log.sh <skill> <path-to-mattpocock-skills-clone>
#
# Reads the pin ("Last reviewed upstream commit") and the upstream path(s) from
# docs/upstream/<skill>.md, then prints `git log <pin>..HEAD -- <paths>` in the
# clone. Paths that no longer exist at HEAD are still passed through: git log
# follows them into history, which is how a rename shows up.
set -euo pipefail

skill="${1:?usage: upstream-log.sh <skill> <clone-dir>}"
clone="${2:?usage: upstream-log.sh <skill> <clone-dir>}"
ledger="$(dirname "$0")/../docs/upstream/${skill}.md"

[[ -f "$ledger" ]] || { echo "no ledger at $ledger" >&2; exit 1; }
git -C "$clone" rev-parse --git-dir >/dev/null 2>&1 || { echo "$clone is not a git clone" >&2; exit 1; }

pin=$(grep -m1 -oE 'Last reviewed upstream commit:\*\* \[`[0-9a-f]+`' "$ledger" | grep -oE '[0-9a-f]{7,}')
paths=$(grep -m1 -E '^\*\*Upstream path\(s\):\*\*' "$ledger" | grep -oE '`[^`]+`' | tr -d '`')

[[ -n "$pin" ]] || { echo "no pin found in $ledger" >&2; exit 1; }
[[ -n "$paths" ]] || { echo "no upstream paths found in $ledger" >&2; exit 1; }

echo "# $skill: upstream commits since $pin on:" >&2
printf '#   %s\n' $paths >&2
# shellcheck disable=SC2086
git -C "$clone" log --date=short --pretty='%h %ad %s' "${pin}..HEAD" -- $paths
