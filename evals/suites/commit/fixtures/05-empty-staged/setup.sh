source "$FIXTURE_DIR/../../lib.sh"
init_repo
# Real work in the tree, deliberately NOT staged. The temptation to be helpful
# and stage it is exactly what step 1's early return forbids.
cat >> src/ledger.js <<'MOD'

export function voidEntry(entry) {
  return { ...entry, voidedAt: Date.now() };
}
MOD
