#!/usr/bin/env bash
# An interrupted Phase 1 of two-phase-node's plan: the run recorded its ticks
# (Step 4 item 6) and the partial module exists, but the commit never landed.
# The work branch exists with nothing ahead of main. No scratch dir, so no
# tree-state.md: only the checked criteria can route this run to the full path.
set -euo pipefail
bash "$FIXTURE_DIR/../two-phase-node/setup.sh"
git checkout -q -b plan/shift-board
awk '/^## Phase 1:/{p=1} /^## Phase 2:/{p=0} { if (p) sub(/^- \[ \] /, "- [x] "); print }' \
  .agents/plans/shift-board-plan.md > plan.tmp && mv plan.tmp .agents/plans/shift-board-plan.md
cat > src/bands.js <<'JS'
export const WATCH_BAND_FACTOR = 0.7;
// partial: bandForRate not finished
JS
