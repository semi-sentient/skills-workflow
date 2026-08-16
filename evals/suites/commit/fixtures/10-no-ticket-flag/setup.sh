source "$FIXTURE_DIR/../../lib.sh"
init_repo
# The branch carries an inferable issue number, but the `--no-ticket` argument
# is a deliberate omission — SKILL.md step 2.1 says inference never overrides
# it. This is run-plan's local-only invocation path.
git checkout -q -b 123-reconcile-report
stage_feature
