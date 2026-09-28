#!/usr/bin/env bash
# two-phase-node's repo and plan, plus the shape every skill-testing run has: the
# operator's own uncommitted edits. One tracked file modified, one untracked file
# whose name porcelain C-quotes (the space). No scratch dir, no ticks: a first run.
set -euo pipefail
bash "$FIXTURE_DIR/../two-phase-node/setup.sh"
printf -- '- Local note: prefer small commits.\n' >> AGENTS.md
mkdir -p notes
printf 'Draft: board colours, not for this run.\n' > "notes/design draft.md"
